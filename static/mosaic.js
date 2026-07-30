/* Shared page mosaic — full on home, soft on product subpages. */
(function () {
  const root = document.querySelector(".page-mosaic");
  const host = document.getElementById("heroMosaicWave");
  if (!root || !host) return;

  const soft =
    root.classList.contains("is-soft") ||
    document.body.dataset.mosaic === "soft";
  const alphaScale = soft ? 0.55 : 1;
  const ampScale = soft ? 0.45 : 1;
  const maxA = soft ? 0.28 : 0.42;

  function paint() {
    const gap = 3;
    const cell = window.matchMedia("(max-width: 720px)").matches ? 22 : 32;
    const cols = Math.max(18, Math.ceil(window.innerWidth / (cell + gap)));
    const rows = Math.max(14, Math.ceil(window.innerHeight / (cell + gap)));
    host.replaceChildren();
    host.style.setProperty("--cols", String(cols));
    host.style.setProperty("--rows", String(rows));
    host.style.setProperty("--cell", cell + "px");
    host.style.setProperty("--gap", gap + "px");
    const frag = document.createDocumentFragment();
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const el = document.createElement("i");
        const nx = c / Math.max(1, cols - 1);
        const ny = r / Math.max(1, rows - 1);
        const crest =
          0.5 +
          0.28 * Math.sin(nx * Math.PI * 2.6) +
          0.14 * Math.sin(nx * Math.PI * 5.2 + ny * 2.4);
        const fall = Math.pow(1 - ny, 1.4);
        const edge = Math.min(nx, 1 - nx, ny, 1 - ny);
        const edgeFade = Math.min(1, edge * 16);
        const a = Math.max(
          0.02,
          Math.min(
            maxA,
            (0.055 + fall * 0.34 + crest * 0.085) * edgeFade * alphaScale
          )
        );
        el.style.setProperty("--a", a.toFixed(3));
        el.style.setProperty("--d", (c * 0.06).toFixed(2) + "s");
        el.style.setProperty(
          "--amp",
          ((12 + crest * 22 + fall * 14) * ampScale).toFixed(1) + "px"
        );
        el.style.setProperty("--dur", soft ? "4.2s" : "3.2s");
        if ((c * 3 + r * 2) % 19 === 0) el.classList.add("is-amber");
        if ((c + r * 2) % 14 === 0) {
          el.style.setProperty("--a", (a * 0.1).toFixed(3));
        }
        frag.appendChild(el);
      }
    }
    host.appendChild(frag);
  }

  paint();
  let t = 0;
  window.addEventListener(
    "resize",
    () => {
      clearTimeout(t);
      t = setTimeout(paint, 180);
    },
    { passive: true }
  );
})();
