// LinkRight Extension — Service Worker (background)
// Responsibilities:
//   1. Store + serve the 30-day extension JWT via chrome.storage.local
//   2. Route messages between popup, content scripts, and LinkRight API
//   3. Handle the "connect" flow initiated from popup
//
// Manifest V3 note: service workers sleep after inactivity. Keep this module
// stateless beyond chrome.storage — don't hold in-memory globals we need later.

const API_BASE = "https://sync.linkright.in";

/** chrome.storage.local helpers (promise-wrapped) */
const storage = {
  get: (keys) => new Promise((resolve) => chrome.storage.local.get(keys, resolve)),
  set: (items) => new Promise((resolve) => chrome.storage.local.set(items, resolve)),
  remove: (keys) => new Promise((resolve) => chrome.storage.local.remove(keys, resolve)),
};

async function getToken() {
  const { lr_token, lr_token_expires_at } = await storage.get(["lr_token", "lr_token_expires_at"]);
  if (!lr_token || !lr_token_expires_at) return null;
  if (Date.now() > Number(lr_token_expires_at)) return null;
  return lr_token;
}

async function setToken(token, ttlMs = 30 * 24 * 60 * 60 * 1000) {
  await storage.set({
    lr_token: token,
    lr_token_expires_at: Date.now() + ttlMs,
  });
}

async function clearToken() {
  await storage.remove(["lr_token", "lr_token_expires_at", "lr_profile"]);
}

/** Open the Connect flow in a new tab. The web page calls back via
 *  chrome.runtime.sendMessage({type: 'lr:connect-callback', token}) from
 *  /extension/connect (externally-connectable configured there). */
async function openConnect() {
  const ret = encodeURIComponent(chrome.runtime.getURL("popup/connected.html"));
  const url = `${API_BASE}/extension/connect?return=${ret}&ext_id=${chrome.runtime.id}`;
  await chrome.tabs.create({ url });
}

async function fetchMe() {
  const token = await getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE}/api/extension/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    const profile = await res.json();
    await storage.set({ lr_profile: profile });
    return profile;
  } catch (e) {
    console.warn("[lr] fetchMe failed:", e);
    return null;
  }
}

/** Message router — popup + content scripts talk to us here. */
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    try {
      switch (msg.type) {
        case "lr:get-status": {
          const token = await getToken();
          const { lr_profile } = await storage.get("lr_profile");
          sendResponse({ connected: !!token, profile: lr_profile ?? null });
          break;
        }
        case "lr:connect":
          await openConnect();
          sendResponse({ ok: true });
          break;
        case "lr:set-token":
          // Called from the connect-callback page after OAuth completes.
          if (!msg.token) { sendResponse({ ok: false, error: "no-token" }); break; }
          await setToken(msg.token, msg.ttl_ms ?? 30 * 24 * 60 * 60 * 1000);
          await fetchMe();
          sendResponse({ ok: true });
          break;
        case "lr:disconnect":
          await clearToken();
          sendResponse({ ok: true });
          break;
        case "lr:api":
          // Generic proxy so content scripts don't need their own auth handling.
          sendResponse(await proxyApi(msg.path, msg.init));
          break;
        default:
          sendResponse({ ok: false, error: `unknown:${msg.type}` });
      }
    } catch (e) {
      sendResponse({ ok: false, error: String(e?.message ?? e) });
    }
  })();
  // Return true to keep the message channel open for async sendResponse.
  return true;
});

async function proxyApi(path, init = {}) {
  const token = await getToken();
  if (!token) return { ok: false, status: 401, error: "not-connected" };
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });
  let body = null;
  try { body = await res.json(); } catch { body = null; }
  return { ok: res.ok, status: res.status, body };
}
