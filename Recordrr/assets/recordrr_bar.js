/* Recordrr in-page control bar — injected by browser.install_bar() via Playwright
 * add_init_script (re-runs on every navigation) + a one-off evaluate for the
 * already-open page. NO proxy: the orchestrator owns the page through Playwright,
 * so the bar talks to it through a shared JS object:
 *
 *   window.__recordrr.cmd     -> button sets it ('rec' | 'stop' | ...);
 *                                the orchestrator reads + clears it each poll.
 *   window.__recordrr.status  -> the orchestrator pushes {state, ep, secs, audio};
 *                                the bar renders it.
 *
 * DURABLE CHANNEL: window.__recordrr is a per-DOCUMENT global — a full page
 * navigation (Prime's player->home are real document reloads) wipes it and the
 * init-script recreates it as {cmd:null, status:idle}, so the bar would show a
 * stale 'idle' (REC button) and a STOP click would set cmd='rec' the loop drops.
 * So the channel is MIRRORED through localStorage (per-ORIGIN, survives same-site
 * navigation): the button writes the cmd key, status is read from the status key.
 * The orchestrator reads/writes the SAME keys (browser.bar_cmd/bar_status). The
 * window global stays as a same-document fast path; localStorage is the truth that
 * outlives a reload. (Cross-origin nav — provider->amazon login — still resets it,
 * but record-time the page stays on the provider origin.)
 *
 * Premise: "if it fits in the browser, it stays in the browser." Add controls by
 * appending to BUTTONS below — render + command plumbing are generic.
 */
(() => {
  if (window.__recordrrBarInit) return;            // idempotent per document
  window.__recordrrBarInit = true;
  const NS = window.__recordrr = window.__recordrr || { cmd: null, status: { state: 'idle' } };
  const LS = 'recordrrBar';           // saved bar geometry
  const LS_CMD = 'recordrrCmd';       // durable cmd channel (button -> orchestrator)
  const LS_STAT = 'recordrrStatus';   // durable status channel (orchestrator -> bar)

  // Channel helpers — write through BOTH the window global (same-doc fast path)
  // and localStorage (survives a navigation/reload).
  const setCmd = (c) => { NS.cmd = c; try { localStorage.setItem(LS_CMD, c); } catch (e) {} };
  const readStatus = () => {
    try { const j = localStorage.getItem(LS_STAT); if (j) return JSON.parse(j); } catch (e) {}
    return NS.status || { state: 'idle' };
  };
  // Popover API → the bar renders in the browser TOP LAYER, above the player's
  // fullscreen video, while living on <body> (NOT inside Pluto's React subtree,
  // which prunes foreign nodes on every re-render). Feature-detected: on a Chrome
  // too old for it we fall back to following document.fullscreenElement.
  const POPOVER = ('showPopover' in HTMLElement.prototype);

  const load = () => { try { return JSON.parse(localStorage.getItem(LS)) || {}; } catch (e) { return {}; } };
  const save = (o) => { try { localStorage.setItem(LS, JSON.stringify(o)); } catch (e) {} };

  // --- control registry: extend here as the workflow grows --------------
  const BUTTONS = [
    { id: 'rec',  label: '⏺ REC',  title: 'Empezar a grabar el vídeo en reproducción',
      kind: 'rec',  show: s => s.state !== 'rec', on: () => { setCmd('rec'); } },
    { id: 'stop', label: '⏹ STOP', title: 'Parar la grabación actual',
      kind: 'stop', show: s => s.state === 'rec', on: () => { setCmd('stop'); } },
  ];

  const fmt = (s) => { s = Math.max(0, s | 0); const m = (s / 60) | 0; return m + ':' + String(s % 60).padStart(2, '0'); };

  function buildBar() {
    let bar = document.getElementById('rr-bar');
    if (bar) return bar;
    const pos = load();
    bar = document.createElement('div');
    bar.id = 'rr-bar';
    if (POPOVER) bar.setAttribute('popover', 'manual');   // manual = no light-dismiss
    Object.assign(bar.style, {
      position: 'fixed', zIndex: '2147483647',
      inset: 'auto', margin: '0',                          // cancel the popover UA centering
      left: (pos.left ?? 24) + 'px', top: (pos.top ?? 24) + 'px',
      width: (pos.width ?? 230) + 'px', minWidth: '130px', minHeight: '44px',
      background: 'rgba(18,18,24,0.92)', color: '#eee',
      font: '13px system-ui,Segoe UI,sans-serif', border: '1px solid #b14cff',
      borderRadius: '9px', boxShadow: '0 4px 16px rgba(0,0,0,.55)',
      resize: 'both', overflow: 'hidden', userSelect: 'none', backdropFilter: 'blur(2px)',
    });
    if (pos.height) bar.style.height = pos.height + 'px';

    const head = document.createElement('div');
    head.id = 'rr-head';
    Object.assign(head.style, {
      cursor: 'move', padding: '5px 9px', display: 'flex',
      justifyContent: 'space-between', alignItems: 'center', fontWeight: '600',
      background: 'linear-gradient(90deg,#b14cff33,#00e0ff22)', borderBottom: '1px solid #b14cff55',
    });
    const name = document.createElement('span'); name.textContent = 'Recordrr';
    const stat = document.createElement('span'); stat.id = 'rr-stat';
    Object.assign(stat.style, { fontWeight: '400', opacity: '.9' });
    head.appendChild(name); head.appendChild(stat);
    bar.appendChild(head);

    const body = document.createElement('div'); body.id = 'rr-body';
    Object.assign(body.style, { padding: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' });
    bar.appendChild(body);

    // drag (on the header)
    let drag = false, ox = 0, oy = 0;
    head.addEventListener('pointerdown', e => { drag = true; ox = e.clientX - bar.offsetLeft; oy = e.clientY - bar.offsetTop; head.setPointerCapture(e.pointerId); });
    head.addEventListener('pointermove', e => { if (!drag) return; bar.style.left = (e.clientX - ox) + 'px'; bar.style.top = (e.clientY - oy) + 'px'; });
    head.addEventListener('pointerup', () => { drag = false; persist(); });
    new ResizeObserver(() => persist()).observe(bar);
    function persist() { save({ left: bar.offsetLeft, top: bar.offsetTop, width: bar.offsetWidth, height: bar.offsetHeight }); }

    bar._body = body; bar._stat = stat;
    return bar;
  }

  let lastMove = Date.now();
  const seen = () => { lastMove = Date.now(); const b = document.getElementById('rr-bar'); if (b) b.style.opacity = '1'; };

  function render() {
    const bar = buildBar();
    // Keep the bar on <body> and float it in the top layer via the popover API.
    // The old code re-parented it into document.fullscreenElement — which on Pluto
    // is the React-owned player container; React PRUNED our injected node on its
    // next render (an ad blade / related-videos transition = a re-render), so the
    // bar vanished until you Escape'd out of fullscreen + F5'd. As a top-layer
    // popover it paints ABOVE the fullscreen video without being in React's subtree.
    if (POPOVER) {
      if (bar.parentElement !== document.body) document.body.appendChild(bar);
      if (!bar.matches(':popover-open')) { try { bar.showPopover(); } catch (e) {} }
    } else {
      const host = document.fullscreenElement || document.body;   // legacy fallback
      if (host && bar.parentElement !== host) host.appendChild(bar);
    }
    const s = readStatus();
    // While recording, fade the bar out when idle so it stays OUT of the capture
    // (x11grab records the framebuffer). Move the mouse to bring it back.
    bar.style.transition = 'opacity .35s';
    bar.style.opacity = (s.state === 'rec' && (Date.now() - lastMove > 2500)) ? '0' : '1';
    if (s.state === 'rec') {
      bar._stat.textContent = '● ' + (s.ep || '') + ' ' + (s.secs != null ? fmt(s.secs) : '') + ' ' + (s.audio === 'mute' ? '🔇' : '🔊');
      bar._stat.style.color = s.audio === 'mute' ? '#ff5555' : '#ff3b6b';
    } else {
      bar._stat.textContent = 'listo';
      bar._stat.style.color = '#7CFC00';
    }
    const body = bar._body; body.innerHTML = '';
    for (const b of BUTTONS) {
      if (b.show && !b.show(s)) continue;
      const el = document.createElement('button');
      el.textContent = b.label; el.title = b.title || '';
      Object.assign(el.style, {
        flex: '1 1 auto', padding: '9px 10px', cursor: 'pointer', border: 'none',
        borderRadius: '6px', fontWeight: '700', fontSize: '13px', color: '#fff',
        background: b.kind === 'rec' ? '#ff3b6b' : b.kind === 'stop' ? '#555' : '#2a2a35',
      });
      // blur after firing: a focused button swallows the player's keybinds
      // (the orchestrator presses 'm' to unmute — it must reach Pluto, not us).
      el.onclick = (ev) => { ev.stopPropagation(); try { b.on(); } catch (e) {} el.blur(); if (document.activeElement) document.activeElement.blur(); };
      body.appendChild(el);
    }
  }

  const tick = () => { try { render(); } catch (e) {} };
  const boot = () => {
    tick();
    setInterval(tick, 700);                                   // refresh status + re-add if SPA wiped it
    document.addEventListener('mousemove', seen, true);       // reveal the faded bar on movement
    document.addEventListener('fullscreenchange', tick);
    new MutationObserver(() => { if (!document.getElementById('rr-bar')) tick(); })
      .observe(document.documentElement, { childList: true, subtree: true });
  };
  if (document.body) boot(); else document.addEventListener('DOMContentLoaded', boot);
})();
