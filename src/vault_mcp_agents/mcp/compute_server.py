"""MCP server for GCE Compute Engine operations (used by the compute agent).

Same structure as the data server: all tools are registered in __init__,
then filtered at runtime by the identity context.
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


class ComputeMCPServer(BaseMCPServer):
    """Exposes GCE instance management tools, gated by identity policy."""

    def __init__(self) -> None:
        super().__init__("compute-server")
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        self._register_tool(
            name="list_instances",
            description="List GCE instances in a given zone.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "GCP project ID."},
                    "zone": {"type": "string", "description": "GCE zone (e.g. us-central1-a)."},
                },
                "required": ["project", "zone"],
            },
            handler=self._list_instances,
        )

        self._register_tool(
            name="get_instance",
            description="Get details of a single GCE instance.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "GCP project ID."},
                    "zone": {"type": "string", "description": "GCE zone."},
                    "instance_name": {"type": "string", "description": "Instance name."},
                },
                "required": ["project", "zone", "instance_name"],
            },
            handler=self._get_instance,
        )

        self._register_tool(
            name="start_instance",
            description="Start a stopped GCE instance.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "GCP project ID."},
                    "zone": {"type": "string", "description": "GCE zone."},
                    "instance_name": {"type": "string", "description": "Instance name."},
                },
                "required": ["project", "zone", "instance_name"],
            },
            handler=self._start_instance,
        )

        self._register_tool(
            name="stop_instance",
            description="Stop a running GCE instance.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "GCP project ID."},
                    "zone": {"type": "string", "description": "GCE zone."},
                    "instance_name": {"type": "string", "description": "Instance name."},
                },
                "required": ["project", "zone", "instance_name"],
            },
            handler=self._stop_instance,
        )

        self._register_tool(
            name="create_instance",
            description="Create a new GCE instance from a machine type and image.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "GCP project ID."},
                    "zone": {"type": "string", "description": "GCE zone."},
                    "instance_name": {"type": "string", "description": "Instance name."},
                    "machine_type": {
                        "type": "string",
                        "description": "Machine type (e.g. e2-micro).",
                        "default": "e2-micro",
                    },
                    "source_image": {
                        "type": "string",
                        "description": "Full image URL.",
                        "default": "projects/debian-cloud/global/images/family/debian-12",
                    },
                },
                "required": ["project", "zone", "instance_name"],
            },
            handler=self._create_instance,
        )

        self._register_tool(
            name="delete_instance",
            description="Delete a GCE instance.",
            input_schema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "GCP project ID."},
                    "zone": {"type": "string", "description": "GCE zone."},
                    "instance_name": {"type": "string", "description": "Instance name."},
                },
                "required": ["project", "zone", "instance_name"],
            },
            handler=self._delete_instance,
        )

    # -- tool handlers --------------------------------------------------------

    async def _list_instances(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import compute_v1
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = compute_v1.InstancesClient(credentials=credentials)
        instances = client.list(project=args["project"], zone=args["zone"])
        result = [
            {"name": i.name, "status": i.status, "machine_type": i.machine_type}
            for i in instances
        ]
        return [TextContent(type="text", text=json.dumps({"instances": result}))]

    async def _get_instance(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import compute_v1
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = compute_v1.InstancesClient(credentials=credentials)
        instance = client.get(
            project=args["project"],
            zone=args["zone"],
            instance=args["instance_name"],
        )
        return [TextContent(type="text", text=json.dumps({
            "name": instance.name,
            "status": instance.status,
            "machine_type": instance.machine_type,
            "network_interfaces": [
                {"network": ni.network, "ip": ni.network_i_p}
                for ni in instance.network_interfaces
            ],
        }))]

    async def _start_instance(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import compute_v1
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = compute_v1.InstancesClient(credentials=credentials)
        operation = client.start(
            project=args["project"],
            zone=args["zone"],
            instance=args["instance_name"],
        )
        operation.result()
        return [TextContent(type="text", text=json.dumps({
            "status": "started", "instance": args["instance_name"],
        }))]

    async def _stop_instance(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import compute_v1
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = compute_v1.InstancesClient(credentials=credentials)
        operation = client.stop(
            project=args["project"],
            zone=args["zone"],
            instance=args["instance_name"],
        )
        operation.result()
        return [TextContent(type="text", text=json.dumps({
            "status": "stopped", "instance": args["instance_name"],
        }))]

    async def _create_instance(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import compute_v1
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = compute_v1.InstancesClient(credentials=credentials)

        machine_type = f"zones/{args['zone']}/machineTypes/{args.get('machine_type', 'e2-micro')}"
        source_image = args.get(
            "source_image",
            "projects/debian-cloud/global/images/family/debian-12",
        )

        instance_resource = compute_v1.Instance(
            name=args["instance_name"],
            machine_type=machine_type,
            disks=[
                compute_v1.AttachedDisk(
                    boot=True,
                    auto_delete=True,
                    initialize_params=compute_v1.AttachedDiskInitializeParams(
                        source_image=source_image,
                    ),
                )
            ],
            network_interfaces=[
                compute_v1.NetworkInterface(name="global/networks/default")
            ],
        )

        operation = client.insert(
            project=args["project"],
            zone=args["zone"],
            instance_resource=instance_resource,
        )
        operation.result()
        return [TextContent(type="text", text=json.dumps({
            "status": "created", "instance": args["instance_name"],
        }))]

    async def _delete_instance(
        self,
        args: dict[str, Any],
        gcp_token: Callable[[], GCPAccessToken],
    ) -> list[TextContent]:
        token = gcp_token()
        from google.cloud import compute_v1
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token.token)
        client = compute_v1.InstancesClient(credentials=credentials)
        operation = client.delete(
            project=args["project"],
            zone=args["zone"],
            instance=args["instance_name"],
        )
        operation.result()
        return [TextContent(type="text", text=json.dumps({
            "status": "deleted", "instance": args["instance_name"],
        }))]


# Entry point — supports both stdio and HTTP transports.
if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO)
    server = ComputeMCPServer()
    if os.environ.get("MCP_TRANSPORT", "stdio") == "http":
        server.run_http()
    else:
        asyncio.run(server.run())
