"""Unit tests for the credential-redaction structlog processor."""
from __future__ import annotations

from paczkomat_atlas_api.logging import redact_sensitive


def test_redacts_password_query_param() -> None:
    # Matches the ogr2ogr PG DSN form: "host=... password=secret dbname=..."
    event = {"event": "ogr.start", "cmd": "PG:host=db port=5432 password=s3cretP@ss dbname=x"}
    out = redact_sensitive(None, "info", event)
    assert "s3cretP@ss" not in out["cmd"]
    assert "***REDACTED***" in out["cmd"]
    # Non-sensitive parts survive.
    assert "host=db" in out["cmd"]
    assert "dbname=x" in out["cmd"]


def test_redacts_bearer_token() -> None:
    event = {"event": "http.outbound", "header": 'Authorization: bearer="abc123def456"'}
    out = redact_sensitive(None, "info", event)
    assert "abc123def456" not in out["header"]


def test_redacts_api_key_query_string() -> None:
    event = {"event": "http.outbound", "url": "https://api.example/v1/x?api_key=k_live_999&q=foo"}
    out = redact_sensitive(None, "info", event)
    assert "k_live_999" not in out["url"]
    assert "q=foo" in out["url"]


def test_redacts_underscore_and_dash_variants() -> None:
    event_a = {"k": "api_key=AAA"}
    event_b = {"k": "api-key=BBB"}
    event_c = {"k": "apikey=CCC"}
    assert "AAA" not in redact_sensitive(None, "info", event_a)["k"]
    assert "BBB" not in redact_sensitive(None, "info", event_b)["k"]
    assert "CCC" not in redact_sensitive(None, "info", event_c)["k"]


def test_passes_through_non_sensitive_strings() -> None:
    event = {"event": "kpi.refresh", "country": "PL", "count": 27450}
    out = redact_sensitive(None, "info", event)
    assert out["country"] == "PL"
    assert out["count"] == 27450


def test_handles_non_string_values() -> None:
    event = {"event": "ingest.done", "rows": 100, "ok": True, "data": {"nested": "dict"}}
    out = redact_sensitive(None, "info", event)
    assert out["rows"] == 100
    assert out["ok"] is True
