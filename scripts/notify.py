import os
import requests


def post_to_slack(text: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("SLACK_WEBHOOK_URL environment variable is not set.")
    resp = requests.post(webhook_url, json={"text": text}, timeout=10)
    resp.raise_for_status()
