from __future__ import annotations

import json

import pytest

from scripts import check_monitoring

HEALTH_URL = "https://example.test/_stcore/health"
CHECK_URL = f"{check_monitoring.API}/check-id"
EMAIL_ALERT = {"type": "down", "notifications": {"email": ["ops@example.test"], "slack": []}}


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("APP_HEALTH_URL", HEALTH_URL)
    monkeypatch.setenv("UPTIME_CHECK_ID", "check-id")
    monkeypatch.setenv("DO_TOKEN", "secret")
    responses = {
        HEALTH_URL: b"ok",
        f"{CHECK_URL}/state": {"state": {"regions": {"us_east": {"status": "UP"}, "eu_west": {"status": "UP"}}}},
        f"{CHECK_URL}/alerts?per_page=200": {"alerts": [EMAIL_ALERT]},
    }

    def fake_fetch(url, token=None):
        body = responses[url]
        return body if isinstance(body, bytes) else json.dumps(body).encode()

    monkeypatch.setattr(check_monitoring, "fetch", fake_fetch)
    return responses


def test_fetch_sends_the_bearer_token(monkeypatch):
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"body"

    def fake_urlopen(request, timeout):
        seen["auth"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(check_monitoring.urllib.request, "urlopen", fake_urlopen)

    assert check_monitoring.fetch(HEALTH_URL, "secret") == b"body"
    assert seen == {"auth": "Bearer secret", "timeout": 20}
    check_monitoring.fetch(HEALTH_URL)
    assert seen["auth"] is None


def test_main_passes_when_every_region_is_up_and_an_alert_notifies(api, capsys):
    check_monitoring.main()

    assert "Downtime alert configuration verified" in capsys.readouterr().out


def test_main_passes_with_a_slack_only_global_alert(api):
    api[f"{CHECK_URL}/alerts?per_page=200"] = {"alerts": [{"type": "down_global", "notifications": {"email": [], "slack": [{"channel": "#ops"}]}}]}

    check_monitoring.main()


@pytest.mark.parametrize("regions", [{}, {"us_east": {"status": "UP"}, "eu_west": {"status": "DOWN"}}])
def test_main_fails_when_a_region_is_down_or_missing(api, regions):
    api[f"{CHECK_URL}/state"] = {"state": {"regions": regions}}

    with pytest.raises(SystemExit, match="unhealthy or unknown"):
        check_monitoring.main()


@pytest.mark.parametrize(
    "alerts",
    [
        [],
        [{"type": "latency", "notifications": {"email": ["ops@example.test"]}}],
        [{"type": "down", "notifications": {"email": [], "slack": []}}],
    ],
)
def test_main_fails_without_a_notifying_downtime_alert(api, alerts):
    api[f"{CHECK_URL}/alerts?per_page=200"] = {"alerts": alerts}

    with pytest.raises(SystemExit, match="No downtime alert"):
        check_monitoring.main()
