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

  // Geometry guards. The bar is a top-layer popover; entering element-fullscreen
  // (Disney) or an SPA re-render (Prime) force-closes+reopens it, which fired the
  // ResizeObserver with a COLLAPSED/zero size → persist() saved garbage → next
  // render loaded a tiny bar with its drag-header off-screen-top (unstoppable
  // record, had to use 'q'). So: clamp loaded geometry into the viewport (header
  // always grabbable), and refuse to persist degenerate sizes. (§20.5o)
  const VW = () => window.innerWidth || 1920, VH = () => window.innerHeight || 1080;
  const W_MIN = 160, W_MAX = 640, H_MIN = 56, H_MAX = 480, HEAD_H = 44;
  const clampGeom = (p) => {
    const w = Math.min(Math.max(p.width || 230, W_MIN), W_MAX);
    const h = (p.height && p.height >= H_MIN) ? Math.min(p.height, H_MAX) : null;
    let left = p.left ?? 24, top = p.top ?? 24;
    left = Math.min(Math.max(left, 0), Math.max(0, VW() - 120));
    top = Math.min(Math.max(top, 0), Math.max(0, VH() - HEAD_H));   // header stays on-screen
    return { left, top, width: w, height: h };
  };

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
    const pos = clampGeom(load());
    bar = document.createElement('div');
    bar.id = 'rr-bar';
    if (POPOVER) bar.setAttribute('popover', 'manual');   // manual = no light-dismiss
    Object.assign(bar.style, {
      position: 'fixed', zIndex: '2147483647',
      inset: 'auto', margin: '0',                          // cancel the popover UA centering
      left: pos.left + 'px', top: pos.top + 'px',
      width: pos.width + 'px', minWidth: '160px', minHeight: '56px',
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

    // drag (on the header) — clamp so the header can never leave the viewport
    // (a top<=0 was what made it ungrabbable at the top of the screen).
    let drag = false, ox = 0, oy = 0;
    head.addEventListener('pointerdown', e => { drag = true; ox = e.clientX - bar.offsetLeft; oy = e.clientY - bar.offsetTop; head.setPointerCapture(e.pointerId); });
    head.addEventListener('pointermove', e => {
      if (!drag) return;
      const nl = Math.min(Math.max(e.clientX - ox, 0), Math.max(0, VW() - 120));
      const nt = Math.min(Math.max(e.clientY - oy, 0), Math.max(0, VH() - HEAD_H));
      bar.style.left = nl + 'px'; bar.style.top = nt + 'px';
    });
    head.addEventListener('pointerup', () => { drag = false; persist(); });
    // Persist on resize too, but NEVER save a degenerate size — a popover
    // close/reopen (fullscreen/SPA) momentarily reports a collapsed box.
    new ResizeObserver(() => persist()).observe(bar);
    function persist() {
      const w = bar.offsetWidth, h = bar.offsetHeight;
      if (w < W_MIN || h < H_MIN) return;                 // transition/collapsed → drop it
      save({ left: Math.max(0, bar.offsetLeft), top: Math.max(0, bar.offsetTop), width: w, height: h });
    }

    bar._body = body; bar._stat = stat;
    return bar;
  }

  let lastMove = Date.now();
  const seen = () => { lastMove = Date.now(); const b = document.getElementById('rr-bar'); if (b) b.style.opacity = '1'; };

  // Place the bar so it is ALWAYS clickable. The popover top layer paints above
  // the page but NOT above a fullscreen element (a fullscreen <video>/player wins
  // the top layer over popovers — proven live: clicks fell through to the video,
  // so REC never registered on Disney's fullscreen player). So:
  //   • no fullscreen element  -> popover on <body> (clean top layer over the page)
  //   • fullscreen element here -> NON-popover child OF the fullscreen element,
  //     which shares its top-layer context and sits above the video (clickable).
  // The MutationObserver in boot() re-adds the bar if the player prunes it. (§20.5p)
  function placeBar(bar) {
    const fs = document.fullscreenElement;
    if (POPOVER && !fs) {
      // popover mode (windowed / kiosk-fill, e.g. Prime)
      if (bar.hasAttribute('popover') === false) bar.setAttribute('popover', 'manual');
      if (bar.parentElement !== document.body) {
        try { if (bar.matches(':popover-open')) bar.hidePopover(); } catch (e) {}
        document.body.appendChild(bar);
      }
      if (!bar.matches(':popover-open')) { try { bar.showPopover(); } catch (e) {} }
    } else if (fs) {
      // fullscreen mode: live INSIDE the fullscreen element as a plain fixed child
      if (bar.hasAttribute('popover')) {
        try { if (bar.matches(':popover-open')) bar.hidePopover(); } catch (e) {}
        bar.removeAttribute('popover');
        bar.style.display = '';                  // clear the popover UA display:none
      }
      if (bar.parentElement !== fs) fs.appendChild(bar);
    } else {
      // no Popover API support, no fullscreen → plain child of body
      if (bar.parentElement !== document.body) document.body.appendChild(bar);
    }
  }

  function render() {
    const bar = buildBar();
    placeBar(bar);
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
    // Rebuild the buttons ONLY when the visible set changes (rec<->stop). render()
    // runs every 700ms; the old code wiped+recreated the buttons EVERY tick, so a
    // render firing between a click's mousedown and mouseup destroyed the button
    // mid-click → the click never completed. That's why a single click did nothing
    // and only a fast double-click registered (more events, better odds of landing
    // on one stable instance). Keeping the element stable between state changes
    // makes a single click land. (§20.5q)
    const show = BUTTONS.filter(b => !b.show || b.show(s));
    const key = show.map(b => b.id).join(',');
    if (bar._btnKey !== key) {
      bar._btnKey = key;
      const body = bar._body; body.innerHTML = '';
      for (const b of show) {
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
