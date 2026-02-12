"""MCP server for GCS and BigQuery operations (used by the data agent).

Every tool handler receives a ``gcp_token`` callback so it can obtain a
fresh short-lived credential right before making the GCP API call.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from mcp.types import TextContent

from vault_mcp_agents.mcp.base_server import BaseMCPServer
from vault_mcp_agents.vault.gcp_credentials import GCPAccessToken

logger = logging.getLogger(__name__)


class DataMCPServer(BaseMCPServer):
    """Exposes GCS bucket/object and BigQuery tools, gated by identity policy."""

    def __init__(self) -> None:
        super().__init__("data-server")
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        self._register_tool(
            name="list_buckets",
            description="List GCS buckets in the configured project.",
            input_schema={
                "type": "object",
                "properties": {
                    "prefix": {
                        "type": "string",
                        "description": "Optional prefix filter for bucket names.",
                    }
                },
            },
            handler=self._list_buckets,
        )

        self._register_tool(
            name="read_object",
            description="Read the contents of a GCS object.",
            input_schema={
                "type": "object",
                "properties": {
                    "bucket": {"type": "string", "description": "Bucket name."},
                    "object_path": {"type": "string", "description": "Object key / path."},
                },
                "required": ["bucket", "object_path"],
            },
            handler=self._read_object,
        )

        self._register_tool(
            name="write_object",
            description="Write content to a GCS object.",
            input_schema={
                "type": "object",
                "properties": {
                    "bucket": {"type": "string", "description": "Bucket name."},
                    "object_path": {"type": "string", "description": "Object key / path."},
                    "content": {"type": "string", "description": "UTF-8 content to write."},
                },
                "required": ["bucket", "object_path", "content"],
            },
            handler=self._write_object,
        )

        self._register_tool(
            name="delete_object",
            description="Delete a GCS object.",
            input_schema={
                "type": "object",
                "properties": {
                    "bucket": {"type": "string", "description": "Bucket name."},
                    "object_path": {"type": "string", "description": "Object key / path."},
                },
                "required": ["bucket", "object_path"],
            },
            handler=self._delete_object,
        )

        self._register_tool(
            name="query_bigquery",
            description="Execute a read-only BigQuery SQL query and return results as JSON.",
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to execute."},
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum rows to return (default 100).",
                        "default": 100,
                    },
                },
                "required": ["sql"],
            },
            handler=self._query_bigquery,
        )

        self._register_tool(
            name="list_datasets",
            description="List BigQuery datasets in the configured project.",
            input_schema={
                "type": "object",
                "properties": {
                    "prefix": {
                        "type": "string",
                        "description": "Optional prefix filter for dataset IDs.",
                    }
                },
            },
            handler=self._list_datasets,
        )

        self._register_tool(
            name="create_dataset",
            description="Create a new BigQuery dataset.",
            input_schema={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "Dataset name."},
                    "location": {
                        "type": "string",
                        "description": "GCP region (default us-central1).",
                        "default": "us-central1",
                    },
                },
                "required": ["dataset_id"],
            },
            handler=self._create_dataset,
        )

    # -- tool handlers --------------------------------------------------------
    # Each handler follows the same signature:
    #   async def handler(args: dict, gcp_token: Callable[[], GCPAccessToken]) -> list[TextContent]

    async def _list_buckets(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import storage
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = storage.Client(project=self._identity.gcp_project, credentials=credentials)
        prefix = args.get("prefix", "")
        buckets = [b.name for b in client.list_buckets() if b.name.startswith(prefix)]
        return [TextContent(type="text", text=json.dumps({"buckets": buckets}))]

    async def _read_object(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import storage
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = storage.Client(project=self._identity.gcp_project, credentials=credentials)
        bucket = client.bucket(args["bucket"])
        blob = bucket.blob(args["object_path"])
        content = blob.download_as_text()
        return [TextContent(type="text", text=content)]

    async def _write_object(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import storage
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = storage.Client(project=self._identity.gcp_project, credentials=credentials)
        bucket = client.bucket(args["bucket"])
        blob = bucket.blob(args["object_path"])
        blob.upload_from_string(args["content"])
        return [TextContent(
            type="text",
            text=json.dumps({"status": "ok", "path": f"gs://{args['bucket']}/{args['object_path']}"}),
        )]

    async def _delete_object(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import storage
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = storage.Client(project=self._identity.gcp_project, credentials=credentials)
        bucket = client.bucket(args["bucket"])
        blob = bucket.blob(args["object_path"])
        blob.delete()
        return [TextContent(
            type="text",
            text=json.dumps({"status": "deleted", "path": f"gs://{args['bucket']}/{args['object_path']}"}),
        )]

    async def _query_bigquery(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import bigquery
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = bigquery.Client(project=self._identity.gcp_project, credentials=credentials)
        max_rows = args.get("max_rows", 100)
        query_job = client.query(args["sql"])
        rows = [dict(row) for row in query_job.result(max_results=max_rows)]
        return [TextContent(type="text", text=json.dumps({"rows": rows, "count": len(rows)}, default=str))]

    async def _list_datasets(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import bigquery
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = bigquery.Client(project=self._identity.gcp_project, credentials=credentials)
        prefix = args.get("prefix", "")
        datasets = [
            ds.dataset_id for ds in client.list_datasets() if ds.dataset_id.startswith(prefix)
        ]
        return [TextContent(type="text", text=json.dumps({"datasets": datasets}))]

    async def _create_dataset(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import bigquery
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = bigquery.Client(project=self._identity.gcp_project, credentials=credentials)
        dataset_ref = client.dataset(args["dataset_id"])
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = args.get("location", "us-central1")
        client.create_dataset(dataset)
        return [TextContent(
            type="text",
            text=json.dumps({"status": "created", "dataset": args["dataset_id"]}),
        )]


# Entry point — supports both stdio and HTTP transports.
if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO)
    server = DataMCPServer()
    if os.environ.get("MCP_TRANSPORT", "stdio") == "http":
        server.run_http()
    else:
        asyncio.run(server.run())
