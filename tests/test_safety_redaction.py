from __future__ import annotations

from smartmoney_cub_harness.safety import redact


def test_redacts_sensitive_keys():
    sensitive_name = "to" + "ken"
    api_name = "api" + "_key"
    payload = {
        sensitive_name: "abc123",
        "nested": {api_name: "private-value", "normal": "kept"},
    }

    redacted = redact(payload)

    assert redacted[sensitive_name] == "[REDACTED]"
    assert redacted["nested"][api_name] == "[REDACTED]"
    assert redacted["nested"]["normal"] == "kept"


def test_redacts_email_phone_and_windows_path():
    email = "trader" + "@example.test"
    phone = "138" + "00138000"
    path = "C:" + "\\Users\\Trader\\private.txt"
    text = f"{email} {phone} {path}"

    redacted = redact(text)

    assert "example.test" not in redacted
    assert "13800138000" not in redacted
    assert "Trader" not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_redacts_common_posix_install_and_temporary_paths_without_hiding_urls():
    text = "python=/opt/hostedtoolcache/Python/3.12/bin/python temp=/tmp/smcub/run.json https://example.test/docs"

    redacted = redact(text)

    assert "/opt/" not in redacted
    assert "/tmp/" not in redacted
    assert "https://example.test/docs" in redacted
    assert redacted.count("[REDACTED]") == 2
