"""Chrome DevTools Protocol client for `linkright watch`.

Connects to a running Chrome instance at ``localhost:<port>`` (Chrome must be
started with ``--remote-debugging-port=<port>``), discovers all open page
targets, attaches to each, subscribes to ``Page.frameNavigated`` events, and
invokes the URL-pattern filter + JS extractor when a job page loads.

The implementation uses ``websockets`` for the CDP socket and ``httpx`` for
the discovery REST endpoint — both already in the linkright dependency tree
(``websockets`` added by this sprint, ``httpx`` already there for Pillar 2).

Design choices:
- Single browser-level WebSocket via ``Target.attachedToTarget`` flatMode
  (sessionId routing) so one connection sees ALL tabs/incognito/etc.
- Auto-reconnect with backoff if Chrome closes/restarts.
- Per-frame "settle delay" of 2 sec (mirrors the Tampermonkey userscript) so
  the JS extraction sees post-XHR DOM, not the early-paint version.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

DEFAULT_PORT = 9222
DEFAULT_HOST = "localhost"
SETTLE_DELAY_SEC = 2.0
RECONNECT_BASE_DELAY = 2.0
RECONNECT_MAX_DELAY = 60.0


class CDPError(RuntimeError):
    """Raised when CDP discovery or connection fails."""


async def discover_browser_ws(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = 5.0,
) -> str:
    """Return the browser-level WebSocket URL via Chrome's REST discovery.

    Hits ``http://<host>:<port>/json/version`` which returns
    ``webSocketDebuggerUrl`` for the browser endpoint (vs per-page endpoints
    at ``/json/list``).
    """
    url = f"http://{host}:{port}/json/version"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.RequestError as exc:
        raise CDPError(
            f"could not reach Chrome DevTools at {url} — is Chrome running with "
            f"`--remote-debugging-port={port}`? (run `linkright watch setup` to fix)"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise CDPError(f"Chrome DevTools at {url} returned {exc.response.status_code}") from exc

    ws_url = data.get("webSocketDebuggerUrl")
    if not ws_url:
        raise CDPError(f"missing webSocketDebuggerUrl in {data}")
    return ws_url


# ── CDP message tracking (request id → future) ──────────────────────────────
class _CdpSession:
    """Wraps one CDP WebSocket with id-based request/response correlation.

    CDP is a JSON-RPC over WebSocket: send {id, method, params} → eventually
    receive {id, result} or {id, error}. Events arrive without an id (just
    {method, params}) — we route those to the on_event callback.
    """

    def __init__(
        self,
        ws,
        on_event: Callable[[str, dict, Optional[str]], Awaitable[None]],
    ):
        self._ws = ws
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[dict]] = {}
        self._on_event = on_event
        self._reader_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._reader_task = asyncio.create_task(self._read_loop(), name="cdp-reader")

    async def stop(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, ConnectionClosed):
                pass

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg_id = msg.get("id")
                if msg_id is not None and msg_id in self._pending:
                    fut = self._pending.pop(msg_id)
                    if not fut.done():
                        if "error" in msg:
                            fut.set_exception(CDPError(f"CDP error: {msg['error']}"))
                        else:
                            fut.set_result(msg.get("result", {}))
                else:
                    method = msg.get("method")
                    params = msg.get("params", {})
                    session_id = msg.get("sessionId")
                    if method:
                        try:
                            await self._on_event(method, params, session_id)
                        except Exception as exc:
                            logger.warning("cdp on_event handler raised: %s", exc)
        except ConnectionClosed:
            logger.info("CDP connection closed")
        except Exception as exc:
            logger.exception("CDP reader unexpected error: %s", exc)

    async def call(
        self,
        method: str,
        params: Optional[dict] = None,
        session_id: Optional[str] = None,
        timeout: float = 10.0,
    ) -> dict:
        msg_id = self._next_id
        self._next_id += 1
        msg: dict = {"id": msg_id, "method": method, "params": params or {}}
        if session_id is not None:
            msg["sessionId"] = session_id
        fut: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = fut
        try:
            await self._ws.send(json.dumps(msg))
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise CDPError(f"CDP call {method} timed out after {timeout}s")


# ── High-level watch loop ───────────────────────────────────────────────────
async def watch_loop(
    on_navigation: Callable[[str, str, _CdpSession], Awaitable[None]],
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """Connect to Chrome and dispatch ``on_navigation(url, session_id, session)``
    for every page navigation across all tabs. Runs forever until stop_event
    is set or KeyboardInterrupt. Auto-reconnects on Chrome restart.
    """
    backoff = RECONNECT_BASE_DELAY

    while True:
        if stop_event is not None and stop_event.is_set():
            return

        try:
            browser_ws = await discover_browser_ws(host, port)
            logger.info("CDP discovered: %s", browser_ws)
        except CDPError as exc:
            logger.warning("CDP discovery failed: %s — retrying in %.0fs", exc, backoff)
            await _sleep_with_stop(backoff, stop_event)
            backoff = min(backoff * 2, RECONNECT_MAX_DELAY)
            continue

        try:
            async with websockets.connect(browser_ws, max_size=10_000_000) as ws:
                logger.info("CDP connected — listening for page navigations")
                backoff = RECONNECT_BASE_DELAY  # reset on successful connect

                async def on_event(method: str, params: dict, session_id: Optional[str]):
                    if method == "Page.frameNavigated":
                        frame = params.get("frame", {}) or {}
                        # Only fire for the TOP frame (not iframes)
                        if frame.get("parentId"):
                            return
                        url = frame.get("url") or ""
                        if not url or url.startswith("about:") or url.startswith("chrome://"):
                            return
                        await on_navigation(url, session_id or "", session)
                    elif method == "Target.attachedToTarget":
                        new_session = (params.get("sessionId") or "")
                        target_info = params.get("targetInfo", {}) or {}
                        if target_info.get("type") == "page":
                            try:
                                await session.call("Page.enable", session_id=new_session)
                            except CDPError as exc:
                                logger.debug("Page.enable on new target failed: %s", exc)

                session = _CdpSession(ws, on_event)
                await session.start()

                # Enable target auto-attach in flatMode so we see all existing
                # AND future page targets through the single browser connection.
                await session.call(
                    "Target.setAutoAttach",
                    {"autoAttach": True, "waitForDebuggerOnStart": False, "flatten": True},
                )
                # Also enable Page on already-attached targets (existing tabs).
                # We discover them via Target.getTargets and per-target Page.enable.
                targets_resp = await session.call("Target.getTargets")
                for t in (targets_resp.get("targetInfos") or []):
                    if t.get("type") != "page":
                        continue
                    target_id = t.get("targetId")
                    if not target_id:
                        continue
                    try:
                        attach = await session.call(
                            "Target.attachToTarget",
                            {"targetId": target_id, "flatten": True},
                        )
                        sess = attach.get("sessionId")
                        if sess:
                            await session.call("Page.enable", session_id=sess)
                    except CDPError as exc:
                        logger.debug("attach to target %s failed: %s", target_id, exc)

                # Hold connection open until stop_event or the WS closes.
                if stop_event is not None:
                    await stop_event.wait()
                else:
                    # Wait forever (until KeyboardInterrupt or connection drop).
                    await asyncio.Future()

                await session.stop()
                return

        except (ConnectionClosed, OSError) as exc:
            logger.warning("CDP connection lost: %s — reconnecting in %.0fs", exc, backoff)
            await _sleep_with_stop(backoff, stop_event)
            backoff = min(backoff * 2, RECONNECT_MAX_DELAY)
        except Exception:
            logger.exception("CDP watch loop unexpected error — reconnecting")
            await _sleep_with_stop(backoff, stop_event)
            backoff = min(backoff * 2, RECONNECT_MAX_DELAY)


async def _sleep_with_stop(delay: float, stop_event: Optional[asyncio.Event]):
    if stop_event is None:
        await asyncio.sleep(delay)
        return
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=delay)
    except asyncio.TimeoutError:
        pass


async def evaluate_in_page(
    session: _CdpSession,
    session_id: str,
    js: str,
    timeout: float = 10.0,
) -> Optional[dict]:
    """Run JS in the given page and return the deserialized result.

    Wraps ``Runtime.evaluate`` with ``returnByValue=True`` so we get the
    plain object back rather than a remote object handle.
    """
    try:
        result = await session.call(
            "Runtime.evaluate",
            {"expression": js, "returnByValue": True, "awaitPromise": False},
            session_id=session_id,
            timeout=timeout,
        )
    except CDPError as exc:
        logger.debug("Runtime.evaluate failed: %s", exc)
        return None

    res = result.get("result", {})
    if res.get("type") == "object" and "value" in res:
        return res["value"]
    if res.get("subtype") == "error":
        logger.debug("page JS threw: %s", res.get("description"))
    return None
