from __future__ import annotations

import json
import os
import urllib.request

API = "https://api.digitalocean.com/v2/uptime/checks"


def fetch(url: str, token: str | None = None) -> bytes:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)  # noqa: S310
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        return response.read()


def main() -> None:
    health_url = os.environ["APP_HEALTH_URL"]
    check_id = os.environ["UPTIME_CHECK_ID"]
    token = os.environ["DO_TOKEN"]

    fetch(health_url)
    print(f"{health_url} is healthy")

    regions = json.loads(fetch(f"{API}/{check_id}/state", token)).get("state", {}).get("regions", {})
    statuses = {region: details.get("status") for region, details in regions.items()}
    print("Uptime status:", statuses)
    if not statuses or any(status != "UP" for status in statuses.values()):
        raise SystemExit("Production monitoring reports an unhealthy or unknown state")

    alerts = json.loads(fetch(f"{API}/{check_id}/alerts?per_page=200", token)).get("alerts", [])
    downtime_alerts = [alert for alert in alerts if alert.get("type") in ("down", "down_global") and (alert.get("notifications", {}).get("email") or alert.get("notifications", {}).get("slack"))]
    if not downtime_alerts:
        raise SystemExit("No downtime alert with notification recipients configured")
    print("Downtime alert configuration verified")


if __name__ == "__main__":
    main()
