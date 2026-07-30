/* Variant E: Magnetic + Spotlight for primary CTAs. */
(function () {
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!fine || reduce) {
    window.QuantMagnetic = { enhance() {}, enhanceAll() {} };
    return;
  }

  function springStep(current, target, vel, stiff, damp, dt) {
    const force = -stiff * (current - target);
    vel = (vel + force * dt) * damp;
    current += vel * dt;
    return [current, vel];
  }

  function ensureStructure(el) {
    el.classList.add("btn-mag");
    el.dataset.magReady = "1";

    if (!el.querySelector(":scope > .btn-mag-spot")) {
      const spot = document.createElement("i");
      spot.className = "btn-mag-spot";
      spot.setAttribute("aria-hidden", "true");
      el.insertBefore(spot, el.firstChild);
    }

    let label = el.querySelector(":scope > .btn-mag-label");
    if (!label) {
      label = document.createElement("span");
      label.className = "btn-mag-label";
      const nodes = [];
      el.childNodes.forEach((n) => {
        if (n.nodeType === 1 && n.classList && n.classList.contains("btn-mag-spot")) return;
        nodes.push(n);
      });
      nodes.forEach((n) => label.appendChild(n));
      if (!label.textContent && !label.childNodes.length) {
        /* textContent wipe left only empty button */
      }
      el.appendChild(label);
    }
    return true;
  }

  function bind(el) {
    ensureStructure(el);
    if (el.dataset.magBound === "1") return;
    el.dataset.magBound = "1";

    const strength = 0.3;
    const inner = 0.48;
    const radius = 120;
    const label = el.querySelector(":scope > .btn-mag-label");

    let tx = 0, ty = 0, vx = 0, vy = 0;
    let ix = 0, iy = 0, ivx = 0, ivy = 0;
    let gx = 0, gy = 0, gix = 0, giy = 0;
    let sc = 1, gsc = 1, vsc = 0;
    let hot = false;
    let pressing = false;
    let raf = 0;

    function setSpot(e) {
      const r = el.getBoundingClientRect();
      const mx = ((e.clientX - r.left) / Math.max(1, r.width)) * 100;
      const my = ((e.clientY - r.top) / Math.max(1, r.height)) * 100;
      el.style.setProperty("--mx", mx.toFixed(2) + "%");
      el.style.setProperty("--my", my.toFixed(2) + "%");
    }

    function paint() {
      el.style.transform =
        "translate3d(" + tx.toFixed(2) + "px," + ty.toFixed(2) + "px,0) scale(" + sc.toFixed(3) + ")";
      if (label) {
        label.style.transform =
          "translate3d(" + ix.toFixed(2) + "px," + iy.toFixed(2) + "px,0)";
      }
    }

    function tick() {
      const stiff = pressing ? 300 : hot ? 200 : 240;
      const damp = pressing ? 0.72 : hot ? 0.74 : 0.7;
      [tx, vx] = springStep(tx, gx, vx, stiff, damp, 1 / 60);
      [ty, vy] = springStep(ty, gy, vy, stiff, damp, 1 / 60);
      [ix, ivx] = springStep(ix, gix, ivx, stiff, damp, 1 / 60);
      [iy, ivy] = springStep(iy, giy, ivy, stiff, damp, 1 / 60);
      [sc, vsc] = springStep(sc, gsc, vsc, stiff, damp, 1 / 60);
      paint();
      const moving =
        Math.abs(vx) + Math.abs(vy) + Math.abs(tx - gx) + Math.abs(ty - gy) > 0.04 ||
        Math.abs(ivx) + Math.abs(ivy) + Math.abs(ix - gix) + Math.abs(iy - giy) > 0.04 ||
        Math.abs(vsc) + Math.abs(sc - gsc) > 0.002;
      if (moving || hot || pressing) raf = requestAnimationFrame(tick);
      else raf = 0;
    }

    function ensureTick() {
      if (!raf) raf = requestAnimationFrame(tick);
    }

    function onMove(e) {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const dist = Math.hypot(dx, dy);
      if (dist < radius) {
        const fall = 1 - dist / radius;
        gx = dx * strength * fall;
        gy = dy * strength * fall;
        gix = dx * inner * fall;
        giy = dy * inner * fall;
        hot = true;
        el.classList.add("is-mag-hot");
        setSpot(e);
      } else {
        gx = gy = gix = giy = 0;
      }
      ensureTick();
    }

    function onLeave() {
      hot = false;
      pressing = false;
      el.classList.remove("is-mag-hot", "is-mag-press");
      gx = gy = gix = giy = 0;
      gsc = 1;
      ensureTick();
    }

    function onDown(e) {
      if (e.button != null && e.button !== 0) return;
      pressing = true;
      el.classList.add("is-mag-press");
      gx *= 0.4;
      gy *= 0.4;
      gix *= 0.4;
      giy *= 0.4;
      gsc = 0.96;
      ensureTick();
    }

    function onUp() {
      pressing = false;
      el.classList.remove("is-mag-press");
      gsc = 1;
      ensureTick();
    }

    el.addEventListener("pointermove", onMove, { passive: true });
    el.addEventListener("pointerenter", onMove, { passive: true });
    el.addEventListener("pointerleave", onLeave, { passive: true });
    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);
  }

  function setLabel(el, text) {
    if (!el) return;
    ensureStructure(el);
    const label = el.querySelector(":scope > .btn-mag-label");
    if (label) label.textContent = text;
    else el.textContent = text;
  }

  function enhance(el) {
    if (!el || !el.classList) return;
    if (el.classList.contains("secondary") || el.classList.contains("ghost")) return;
    if (!el.classList.contains("btn") && !el.classList.contains("btn-mag")) return;
    bind(el);
  }

  function enhanceAll(root) {
    const scope = root || document;
    scope.querySelectorAll(".btn-mag").forEach(enhance);
  }

  window.QuantMagnetic = { enhance, enhanceAll, setLabel };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => enhanceAll());
  } else {
    enhanceAll();
  }
})();
