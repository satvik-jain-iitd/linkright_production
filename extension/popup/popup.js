// LinkRight Extension — popup (browser action)
// Shows connect/connected status. All auth work lives in the service worker.

const view = document.getElementById("view");

function send(msg) {
  return new Promise((resolve) => chrome.runtime.sendMessage(msg, resolve));
}

function renderNotConnected() {
  view.innerHTML = `
    <div class="card">
      <div class="muted" style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
        <span class="status-dot dot-grey"></span> Not connected
      </div>
      <p>Connect your LinkRight account so the extension can generate tailored apply-packs from your memory layer on every job page.</p>
    </div>
    <button class="btn btn-primary" id="connect">Connect account</button>
    <button class="btn btn-secondary" id="open">Open sync.linkright.in</button>
  `;
  document.getElementById("connect")?.addEventListener("click", async () => {
    await send({ type: "lr:connect" });
    window.close();
  });
  document.getElementById("open")?.addEventListener("click", () => {
    chrome.tabs.create({ url: "https://sync.linkright.in/dashboard" });
  });
}

function renderConnected(profile) {
  const streak = profile?.streak ?? 0;
  const atoms = profile?.atoms ?? 0;
  view.innerHTML = `
    <div class="card">
      <div class="muted" style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
        <span class="status-dot dot-green"></span> Connected
      </div>
      <div style="font-weight:600; margin-bottom:4px;">${profile?.name ?? profile?.email ?? "You"}</div>
      <div class="muted">${atoms} memory atoms · ${streak}-day streak</div>
    </div>
    <button class="btn btn-primary" id="today">Open today's jobs</button>
    <button class="btn btn-secondary" id="profile">Profile & token</button>
    <button class="btn btn-secondary" id="disconnect">Disconnect</button>
  `;
  document.getElementById("today")?.addEventListener("click", () => {
    chrome.tabs.create({ url: "https://sync.linkright.in/dashboard/today" });
  });
  document.getElementById("profile")?.addEventListener("click", () => {
    chrome.tabs.create({ url: "https://sync.linkright.in/dashboard/profile" });
  });
  document.getElementById("disconnect")?.addEventListener("click", async () => {
    await send({ type: "lr:disconnect" });
    renderNotConnected();
  });
}

(async () => {
  const status = await send({ type: "lr:get-status" });
  if (status?.connected) renderConnected(status.profile);
  else renderNotConnected();
})();
