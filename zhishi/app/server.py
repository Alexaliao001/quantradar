"""知势 HTTP 壳：stdlib，无强制第三方依赖。绑定 0.0.0.0:$PORT。"""
from __future__ import annotations

import json
import re
import secrets
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app import config
from app.engine import analyze, fail_closed, load_bars

STATIC = Path(__file__).resolve().parent / "static"
CONTENT = config.CONTENT

# 内存会话 / 复盘本 / 错题（MVP；生产换 DB）
SESSIONS: dict[str, dict[str, Any]] = {}
REVIEWS: dict[str, list[dict[str, Any]]] = {}
DRILLS: dict[str, list[dict[str, Any]]] = {}
REMINDERS: dict[str, list[dict[str, Any]]] = {}

SYMBOL_RE = re.compile(r"^\d{6}$")
HK_RE = re.compile(r"^\d{5}$")


def _json_bytes(data: Any, code: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return code, body, "application/json; charset=utf-8"


def _read_json_file(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def health() -> dict[str, Any]:
    return {
        "service": "zhishi",
        "ok": True,
        "contract_version": config.CONTRACT_VERSION,
        "mode_default": config.MODE,
        "data_path": "fixtures" if not config.live_eligible() else "tushare",
        "live_eligible": config.live_eligible(),
        "disclaimer": config.DISCLAIMER,
    }


def do_analyze(symbol: str, market: str = "A", mode: str | None = None, as_of: str | None = None) -> dict[str, Any]:
    symbol = symbol.strip()
    market = (market or "A").upper()
    if market == "A" and not SYMBOL_RE.match(symbol):
        return fail_closed(symbol, "invalid_symbol")
    if market == "HKCONNECT" and not (HK_RE.match(symbol) or SYMBOL_RE.match(symbol)):
        return fail_closed(symbol, "invalid_symbol")

    payload = load_bars(symbol, mode=mode)
    if payload is None:
        # 港股通教学：尝试 hk fixture
        if market == "HKCONNECT":
            payload = load_bars(symbol, mode="artifact")
        if payload is None:
            return fail_closed(symbol, "symbol_not_found")

    if market == "HKCONNECT":
        payload = dict(payload)
        payload["market"] = "HKCONNECT"

    result = analyze(payload)
    if as_of and result.get("ok"):
        result["requested_as_of"] = as_of
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = "Zhishi/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        # quieter default
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            code, body, ct = _json_bytes(health())
            return self._send(code, body, ct)

        if path == "/api/skus":
            code, body, ct = _json_bytes({"ok": True, "skus": config.SKUS, "disclaimer": config.DISCLAIMER})
            return self._send(code, body, ct)

        if path == "/api/lessons":
            return self._send(*_json_bytes({"ok": True, "lessons": _list_lessons()}))

        if path.startswith("/api/lessons/"):
            lid = path.rsplit("/", 1)[-1]
            lesson = _load_lesson(lid)
            if lesson is None:
                return self._send(*_json_bytes({"ok": False, "error": "not_found"}, 404))
            return self._send(*_json_bytes({"ok": True, "lesson": lesson}))

        if path == "/api/cases":
            idx = CONTENT / "cases" / "index.json"
            cases = _read_json_file(idx) if idx.is_file() else []
            free_only = qs.get("free", ["0"])[0] == "1"
            if free_only:
                cases = [c for c in cases if c.get("free_demo")]
            return self._send(*_json_bytes({"ok": True, "cases": cases}))

        if path == "/api/analyze":
            symbol = (qs.get("symbol") or qs.get("ticker") or [""])[0]
            market = (qs.get("market") or ["A"])[0]
            mode = (qs.get("mode") or [None])[0]
            as_of = (qs.get("as_of") or [None])[0]
            result = do_analyze(symbol, market=market, mode=mode, as_of=as_of)
            code = 200 if result.get("ok") else (400 if result.get("error") == "invalid_symbol" else 404)
            return self._send(*_json_bytes(result, code))

        if path == "/api/sample":
            # 固定免费 Demo：600519
            result = do_analyze("600519", mode="artifact")
            result["sample"] = True
            return self._send(*_json_bytes(result))

        if path == "/api/hkconnect/checklist":
            return self._send(*_json_bytes({"ok": True, "items": _hk_checklist_diff()}))

        if path == "/api/me/reviews":
            sid = self.headers.get("X-Session") or ""
            return self._send(*_json_bytes({"ok": True, "reviews": REVIEWS.get(sid, [])}))

        if path == "/api/me/drills":
            sid = self.headers.get("X-Session") or ""
            return self._send(*_json_bytes({"ok": True, "drills": DRILLS.get(sid, [])}))

        if path == "/api/me/reminders":
            sid = self.headers.get("X-Session") or ""
            return self._send(*_json_bytes({"ok": True, "reminders": REMINDERS.get(sid, [])}))

        # static / pages
        if path == "/" or path == "/index.html":
            return self._file(STATIC / "index.html", "text/html; charset=utf-8")
        if path == "/app.css":
            return self._file(STATIC / "app.css", "text/css; charset=utf-8")
        if path == "/app.js":
            return self._file(STATIC / "app.js", "application/javascript; charset=utf-8")
        if path == "/terms":
            return self._file(STATIC / "terms.html", "text/html; charset=utf-8")
        if path == "/privacy":
            return self._file(STATIC / "privacy.html", "text/html; charset=utf-8")
        if path == "/disclaimer":
            return self._file(STATIC / "disclaimer.html", "text/html; charset=utf-8")
        if path == "/methodology":
            return self._file(STATIC / "methodology.html", "text/html; charset=utf-8")
        if path == "/pricing":
            return self._file(STATIC / "pricing.html", "text/html; charset=utf-8")

        self._send(*_json_bytes({"ok": False, "error": "not_found"}, 404))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._send(*_json_bytes({"ok": False, "error": "invalid_json"}, 400))

        if path == "/api/session":
            sid = secrets.token_urlsafe(16)
            plan = data.get("plan") or "free"
            SESSIONS[sid] = {"plan": plan, "created": time.time()}
            REVIEWS.setdefault(sid, [])
            DRILLS.setdefault(sid, [])
            REMINDERS.setdefault(sid, [])
            return self._send(*_json_bytes({"ok": True, "session": sid, "plan": plan}))

        if path == "/api/analyze":
            symbol = str(data.get("symbol") or "")
            market = str(data.get("market") or "A")
            mode = (data.get("context") or {}).get("mode")
            as_of = (data.get("context") or {}).get("as_of")
            result = do_analyze(symbol, market=market, mode=mode, as_of=as_of)
            code = 200 if result.get("ok") else (400 if result.get("error") == "invalid_symbol" else 404)
            return self._send(*_json_bytes(result, code))

        if path == "/api/reviews":
            sid = self.headers.get("X-Session") or ""
            if sid not in SESSIONS:
                return self._send(*_json_bytes({"ok": False, "error": "login_required"}, 401))
            entry = {
                "id": secrets.token_hex(6),
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "primary_score": data.get("primary_score"),
                "posture": data.get("posture"),
                "hypothesis": (data.get("hypothesis") or "").strip(),
                "invalidation": (data.get("invalidation") or "").strip(),
                "created_at": time.time(),
            }
            if not entry["hypothesis"] or not entry["invalidation"]:
                return self._send(*_json_bytes({"ok": False, "error": "hypothesis_and_invalidation_required"}, 400))
            REVIEWS.setdefault(sid, []).insert(0, entry)
            # 自动创建次日复盘提醒
            REMINDERS.setdefault(sid, []).append(
                {
                    "id": secrets.token_hex(4),
                    "review_id": entry["id"],
                    "symbol": entry["symbol"],
                    "due_at": time.time() + 86400,
                    "kind": "next_day_review",
                    "done": False,
                }
            )
            return self._send(*_json_bytes({"ok": True, "review": entry}))

        if path == "/api/drills":
            sid = self.headers.get("X-Session") or ""
            if sid not in SESSIONS:
                return self._send(*_json_bytes({"ok": False, "error": "login_required"}, 401))
            item = {
                "id": secrets.token_hex(6),
                "prompt": data.get("prompt"),
                "user_answer": data.get("user_answer"),
                "correct": bool(data.get("correct")),
                "explanation": data.get("explanation"),
                "created_at": time.time(),
            }
            DRILLS.setdefault(sid, []).insert(0, item)
            return self._send(*_json_bytes({"ok": True, "drill": item}))

        if path == "/api/pay/mock_checkout":
            # 微信小程序支付占位：返回 mock prepay 信息，生产换真实统一下单
            sku_id = str(data.get("sku") or "")
            sku = config.SKUS.get(sku_id)
            if not sku:
                return self._send(*_json_bytes({"ok": False, "error": "unknown_sku"}, 400))
            if sku["price_fen"] <= 0:
                return self._send(*_json_bytes({"ok": True, "sku": sku_id, "paid": True, "mock": True}))
            return self._send(
                *_json_bytes(
                    {
                        "ok": True,
                        "mock": True,
                        "sku": sku_id,
                        "name": sku["name"],
                        "price_fen": sku["price_fen"],
                        "prepay_id": f"mock_prepay_{sku_id}",
                        "message": "生产环境替换为微信统一下单；商品名必须为知识付费课包/研习会员。",
                    }
                )
            )

        if path == "/api/reminders/complete":
            sid = self.headers.get("X-Session") or ""
            rid = data.get("id")
            for r in REMINDERS.get(sid, []):
                if r.get("id") == rid:
                    r["done"] = True
                    return self._send(*_json_bytes({"ok": True, "reminder": r}))
            return self._send(*_json_bytes({"ok": False, "error": "not_found"}, 404))

        self._send(*_json_bytes({"ok": False, "error": "not_found"}, 404))

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            return self._send(*_json_bytes({"ok": False, "error": "not_found"}, 404))
        body = path.read_bytes()
        self._send(200, body, content_type)


def _list_lessons() -> list[dict[str, Any]]:
    lessons_dir = CONTENT / "lessons"
    out = []
    if not lessons_dir.is_dir():
        return out
    for p in sorted(lessons_dir.glob("*.md")):
        meta = _parse_lesson_meta(p)
        out.append(meta)
    # hkconnect lessons
    hk = CONTENT / "hkconnect"
    if hk.is_dir():
        for p in sorted(hk.glob("*.md")):
            meta = _parse_lesson_meta(p)
            meta["track"] = "hkconnect"
            out.append(meta)
    return out


def _parse_lesson_meta(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    title = path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return {
        "id": path.stem,
        "title": title,
        "path": str(path.relative_to(CONTENT)),
        "free": path.stem.startswith(("01-", "02-", "03-")),
    }


def _load_lesson(lesson_id: str) -> dict[str, Any] | None:
    for folder in (CONTENT / "lessons", CONTENT / "hkconnect"):
        path = folder / f"{lesson_id}.md"
        if path.is_file():
            return {
                "id": lesson_id,
                "title": _parse_lesson_meta(path)["title"],
                "markdown": path.read_text(encoding="utf-8"),
                "track": "hkconnect" if folder.name == "hkconnect" else "a",
            }
    return None


def _hk_checklist_diff() -> list[dict[str, str]]:
    return [
        {
            "id": "session",
            "a_share": "连续竞价为主，有集合竞价",
            "hkconnect": "需同时关注港股通开通时段与额度状态",
            "teaching": "先确认「今天能不能通过港股通交易」，再谈形态。",
        },
        {
            "id": "settlement",
            "a_share": "T+1 股票交收直觉强",
            "hkconnect": "交收与资金可用节奏不同，勿混用",
            "teaching": "复盘本单独标注市场：A 或 港股通。",
        },
        {
            "id": "fx",
            "a_share": "人民币计价",
            "hkconnect": "汇率影响真实盈亏体感",
            "teaching": "假设里写清汇率是否纳入判断。",
        },
        {
            "id": "limits",
            "a_share": "涨跌停制度显著影响行为",
            "hkconnect": "无 A 股式涨跌停，波动叙事不同",
            "teaching": "不要把涨停板战术迁移到港股通标的。",
        },
        {
            "id": "spread",
            "a_share": "流动性分层看板块",
            "hkconnect": "价差与深度可能更差",
            "teaching": "自检增加「价差可接受吗」一项。",
        },
    ]


def main() -> None:
    server = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    print(f"知势 listening on http://{config.HOST}:{config.PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
