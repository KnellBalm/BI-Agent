import json
import logging
import requests
from typing import Dict, Any, List
from backend.utils.logger_setup import setup_logger

logger = setup_logger("slack_notifier", "slack.log")

class SlackNotifier:
    """
    Sends BI report summaries and alerts to Slack via Webhooks.
    """
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_report_summary(self, result: Dict[str, Any], project_name: str):
        """Formats and sends a BI-Agent analysis summary to Slack."""
        if not self.webhook_url:
            logger.warning("No Slack webhook URL provided. Skipping notification.")
            return False

        summary = result.get("summary", {})
        visuals = ", ".join(summary.get("visuals", []))
        
        # Build Slack Block Kit message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 BI-Agent Insight: {project_name.upper()}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Analysis Summary:*\n>{result.get('reasoning', 'No reasoning provided.')}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Source Table:*\n`{summary.get('table', 'N/A')}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Visuals Created:*\n{visuals or 'None'}"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📍 Full Report: `{result.get('path')}`"
                    }
                ]
            }
        ]

        try:
            payload = {"blocks": blocks}
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            logger.info(f"Successfully sent Slack notification for project '{project_name}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def send_alert(self, title: str, message: str, level: str = "INFO"):
        """Sends a simple alert/notification to Slack."""
        color = "#36a64f" if level == "INFO" else "#eb4034"
        payload = {
            "attachments": [
                {
                    "fallback": f"[{level}] {title}",
                    "color": color,
                    "title": f"[{level}] {title}",
                    "text": message
                }
            ]
        }
        try:
            requests.post(self.webhook_url, json=payload)
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
