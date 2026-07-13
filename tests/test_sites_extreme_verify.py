"""Unit tests for pure helpers in scripts/sites_extreme_verify.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sites_extreme_verify.py"

spec = importlib.util.spec_from_file_location("sites_extreme_verify", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules["sites_extreme_verify"] = mod
spec.loader.exec_module(mod)


def test_title_of_basic():
    assert mod.title_of("<html><title>Hello World</title></html>") == "Hello World"


def test_title_of_missing():
    assert mod.title_of("<html><body>no title</body></html>") == ""


def test_title_of_truncates():
    long = "x" * 200
    t = mod.title_of(f"<title>{long}</title>")
    assert len(t) == 100


def test_is_tls_flake_ssl_eof():
    assert mod.is_tls_flake(0, "<urlopen error EOF occurred in violation of protocol (_ssl.c:1129)>")


def test_is_tls_flake_timeout():
    assert mod.is_tls_flake(0, "The read operation timed out")


def test_is_tls_flake_not_http_error():
    assert not mod.is_tls_flake(500, "Internal Server Error")
    assert not mod.is_tls_flake(404, "not found")


def test_is_tls_flake_empty_ok_body_not_flake():
    # code 0 with unrelated message
    assert not mod.is_tls_flake(0, "some other failure without keywords")


def test_host_of():
    assert mod.host_of("https://quantradar.one/health") == "quantradar.one"
