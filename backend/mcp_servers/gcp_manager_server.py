#!/usr/bin/env python3
"""
GCP Manager MCP Server

MCP 서버로 Google Cloud Platform 리소스를 관리합니다 (쿼터, 빌링).
"""
import json
import sys
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP
from google.cloud import monitoring_v3
from google.cloud import billing_v1
from dotenv import load_dotenv

from .lifecycle import setup_signal_handlers, log_startup

load_dotenv()

mcp = FastMCP("gcp-manager-mcp-server")


@mcp.tool()
def get_quota_usage(project_id: str, service: str = "compute.googleapis.com") -> str:
    """Get quota usage for a GCP service

    Args:
        project_id: GCP project ID
        service: GCP service name (default: compute.googleapis.com)

    Returns:
        JSON with service name, usage data, and optional message
    """
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    # Query last hour of quota usage
    now = datetime.utcnow()
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(now.timestamp())},
            "start_time": {"seconds": int((now - timedelta(hours=1)).timestamp())},
        }
    )

    # Build the metric filter
    metric_filter = f'metric.type="serviceruntime.googleapis.com/quota/rate/net_usage" AND resource.labels.service="{service}"'

    results = client.list_time_series(
        request={
            "name": project_name,
            "filter": metric_filter,
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }
    )

    usage_data = []
    for result in results:
        for point in result.points:
            usage_data.append({
                "timestamp": point.interval.end_time.isoformat(),
                "value": point.value.double_value or point.value.int64_value,
                "metric": dict(result.metric.labels),
            })

    return json.dumps({
        "service": service,
        "usageData": usage_data,
        "message": f"Retrieved quota usage for {service}" if usage_data else f"No quota usage data found for {service}"
    }, indent=2, default=str)


@mcp.tool()
def get_billing_info(billing_account_name: str) -> str:
    """Get billing information for a GCP billing account

    Args:
        billing_account_name: Billing account name (format: billingAccounts/XXXXXX-XXXXXX-XXXXXX)

    Returns:
        JSON with billing account information
    """
    client = billing_v1.CloudBillingClient()

    try:
        billing_account = client.get_billing_account(name=billing_account_name)

        result = {
            "name": billing_account.name,
            "displayName": billing_account.display_name,
            "open": billing_account.open,
            "masterBillingAccount": billing_account.master_billing_account if billing_account.master_billing_account else None,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        raise ValueError(f"Failed to retrieve billing info: {str(e)}")


if __name__ == "__main__":
    setup_signal_handlers()
    log_startup("GCP Manager MCP Server")
    mcp.run(transport="stdio")
