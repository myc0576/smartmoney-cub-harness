from __future__ import annotations

from smartmoney_cub.cli import doctor
from smartmoney_cub.schemas import SAFETY_DECLARATION


def test_doctor_reports_offline_no_credentials_required():
    result = doctor()

    assert result["network_required"] is False
    assert result["telemetry"] is False
    assert result["upload"] is False
    assert result["credentials_required"] is False
    assert result["github_auth_required"] is False
    assert result["external_api_required"] is False
    assert result["broker_api_required"] is False
    assert result["execution_integrations"] == "disabled"
    assert result["safety"] == SAFETY_DECLARATION

