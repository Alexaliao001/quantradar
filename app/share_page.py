"""Read-only share card HTML for /r/{ticker} (QD2-5 P0 slice).

Server-rendered so crawlers see verdict text without JS.
Never invent scores — only render charts artifact via analyze(mode=artifact).
"""

from __future__ import annotations

import html
from typing import Any


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_share_html(ticker: str, result: dict[str, Any]) -> bytes:
    """Build a minimal share page. result should already be analyze() output."""
    t = (ticker or "INTC").strip().upper() or "INTC"
    ok = bool(result.get("ok"))
    primary = ""
    label = ""
    score_txt = "—"
    why = ""
    freeze = "Frozen demo snapshot · not a live feed"
    posture = "Mechanical posture ≠ trade direction. PUT ≠ sell order."
    avoided = ""

    if ok:
        primary = str((result.get("primary") or {}).get("action") or "—").upper()
        label = str((result.get("primary") or {}).get("label") or "")
        ps = result.get("primary_score") or {}
        if ps.get("value") is not None and not ps.get("withheld"):
            score_txt = f"{float(ps['value']):.0f}"
        why = str(result.get("summary") or "")
        eng = result.get("engagement") or {}
        freeze = str(eng.get("freeze_label") or freeze)
        posture = str(eng.get("posture_note") or posture)
        avoided = str(eng.get("avoided_line") or "")
    else:
        primary = "UNAVAILABLE"
        label = "No demo artifact for this ticker"
        why = str(result.get("error_detail") or result.get("error") or "Artifact not found.")

    title = f"{t} · {primary} · score {score_txt} — QuantRadar"
    desc = (
        f"{t} mechanical posture {primary}"
        + (f" ({label})" if label else "")
        + f". Score {score_txt}/100. Educational demo — not investment advice."
    )
    desk_href = f"/?demo={_esc(t)}"
    put_note = ""
    if primary.startswith("PUT"):
        put_note = "<p class=\"muted\">PUT is hedge bias — not a sell order.</p>"

    avoided_html = f"<p class=\"avoided-line\">{_esc(avoided)}</p>" if avoided else ""

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(desc)}" />
  <meta property="og:title" content="{_esc(title)}" />
  <meta property="og:description" content="{_esc(desc)}" />
  <meta property="og:image" content="/static/og-default.svg" />
  <meta property="og:type" content="website" />
  <link rel="canonical" href="/r/{_esc(t)}" />
  <link rel="stylesheet" href="/static/site.css" />
</head>
<body>
  <header class="top">
    <a class="brand" href="/">Quant<span>Radar</span></a>
    <nav>
      <a href="/methodology">Methodology</a>
      <a href="/track">Track</a>
      <a href="/pricing">Pricing</a>
      <a href="/login">Sign in</a>
      <a href="{desk_href}">Open desk</a>
    </nav>
  </header>
  <main class="prose share-card">
    <p class="eyebrow">Read-only demo share · Beta · no fake social proof</p>
    <p class="brand-mark">Quant<span>Radar</span></p>
    <h1>{_esc(t)}</h1>
    <p class="verdict-action" data-tone="{'bad' if primary in ('NO', 'PUT') or primary.startswith('PUT') else 'warn' if primary == 'WAIT' else 'ok' if ok else 'neutral'}">{_esc(primary)}</p>
    <p class="muted">{_esc(label)}</p>
    <p class="share-score">Mechanical posture <b>{_esc(score_txt)}</b><span class="muted"> / 100</span></p>
    <p>{_esc(why)}</p>
    {put_note}
    {avoided_html}
    <p class="freeze-pill" style="display:inline-block">{_esc(freeze)}</p>
    <p class="muted" style="margin-top:1rem">{_esc(posture)}</p>
    <div class="hero-cta" style="margin-top:1.5rem">
      <a class="btn" href="{desk_href}">Open full desk</a>
      <a class="btn secondary" href="/pricing">Pricing</a>
    </div>
    <p class="muted" style="margin-top:1.25rem">Educational only — not investment advice. Fortune Insight, LLC.</p>
  </main>
  <footer class="foot">
    <a href="/methodology">Methodology</a> ·
    <a href="/track">Track</a> ·
    <a href="/pricing">Pricing</a> ·
    <a href="/terms">Terms</a> ·
    <a href="/privacy">Privacy</a> ·
    <a href="/refund">Refund</a>
  </footer>
</body>
</html>
"""
    return body.encode("utf-8")
