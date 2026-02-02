#!/usr/bin/env python3
"""
BigQuery MCP Server

MCP 서버로 Google BigQuery에 연결하고 쿼리를 실행합니다.
"""
import json
import os
import sys
from mcp.server.fastmcp import FastMCP
from google.cloud import bigquery
from dotenv import load_dotenv

from .lifecycle import setup_signal_handlers, log_startup

load_dotenv()

mcp = FastMCP("bigquery-mcp-server")


def get_client(project_id: str = None):
    """Get BigQuery client with optional project ID override"""
    if project_id:
        return bigquery.Client(project=project_id)
    return bigquery.Client()


@mcp.tool()
def query(sql: str, projectId: str = None, location: str = None) -> str:
    """Execute a BigQuery SQL query

    Args:
        sql: The SQL query to execute
        projectId: GCP project ID (optional, uses default credentials if not provided)
        location: BigQuery dataset location (optional, e.g., 'US', 'EU')

    Returns:
        JSON array of result rows
    """
    client = get_client(projectId)

    job_config = bigquery.QueryJobConfig()
    if location:
        job_config.default_dataset = f"{projectId or client.project}.{location}"

    query_job = client.query(sql, job_config=job_config)
    results = query_job.result()

    rows = []
    for row in results:
        rows.append(dict(row.items()))

    return json.dumps(rows, indent=2, default=str)


@mcp.tool()
def list_datasets(projectId: str = None) -> str:
    """List all datasets in a BigQuery project

    Args:
        projectId: GCP project ID (optional, uses default credentials if not provided)

    Returns:
        JSON array of dataset IDs
    """
    client = get_client(projectId)
    datasets = list(client.list_datasets())

    dataset_ids = [dataset.dataset_id for dataset in datasets]
    return json.dumps(dataset_ids, indent=2)


@mcp.tool()
def list_tables(dataset_id: str, projectId: str = None) -> str:
    """List all tables in a BigQuery dataset

    Args:
        dataset_id: The dataset ID to list tables from
        projectId: GCP project ID (optional, uses default credentials if not provided)

    Returns:
        JSON array of table IDs
    """
    client = get_client(projectId)

    # Get dataset reference
    dataset_ref = bigquery.DatasetReference(
        project=projectId or client.project,
        dataset_id=dataset_id
    )

    tables = list(client.list_tables(dataset_ref))
    table_ids = [table.table_id for table in tables]

    return json.dumps(table_ids, indent=2)


if __name__ == "__main__":
    setup_signal_handlers()
    log_startup("BigQuery MCP Server")
    mcp.run(transport="stdio")
