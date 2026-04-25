import asyncio
import os
import httpx
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("cloudnet-mcp")

CLOUDNET_URL = os.environ.get("CLOUDNET_URL", "http://127.0.0.1:2812/api/v3")
CLOUDNET_USER = os.environ.get("CLOUDNET_USER", "admin")
CLOUDNET_PASSWORD = os.environ.get("CLOUDNET_PASSWORD", "admin")

class CloudNetClient:
    def __init__(self, base_url: str, user: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.token = None
        self.client = httpx.AsyncClient()

    async def _authenticate(self):
        resp = await self.client.post(
            f"{self.base_url}/auth",
            auth=(self.user, self.password)
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data.get("token")
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    async def request(self, method: str, endpoint: str, **kwargs):
        if not self.token:
            await self._authenticate()
        
        path = endpoint.lstrip("/")
        url = f"{self.base_url}/{path}"
        
        try:
            resp = await self.client.request(method, url, **kwargs)
            if resp.status_code == 401:
                # Token might be expired, re-authenticate and retry
                await self._authenticate()
                resp = await self.client.request(method, url, **kwargs)
            resp.raise_for_status()
            if resp.status_code == 204:
                return {"status": "success"}
            return resp.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    async def close(self):
        await self.client.aclose()


client = CloudNetClient(CLOUDNET_URL, CLOUDNET_USER, CLOUDNET_PASSWORD)

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_nodes",
            description="List all nodes in the CloudNet cluster",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_node_info",
            description="Get detailed information about a specific node",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "The ID of the node"}
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="get_services",
            description="List all smart services",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_online_players",
            description="Get a list of online players based on the query parameters",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "The maximum amount of players to respond with"},
                    "skip": {"type": "integer", "description": "The amount of players to skip"},
                    "sort": {"type": "string", "enum": ["asc", "desc"], "description": "Sort players by name"},
                },
            },
        ),
        types.Tool(
            name="get_player_info",
            description="Get a player by their unique id or name",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "The name or unique id of the player"}
                },
                "required": ["identifier"],
            },
        ),
        types.Tool(
            name="kick_player",
            description="Kicks a given player from the entire network",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "The name or unique id of the player"},
                    "message": {"type": "string", "description": "The kick message/reason"}
                },
                "required": ["identifier", "message"],
            },
        ),
        types.Tool(
            name="send_player_message",
            description="Sends a chat message to a given player",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "The name or unique id of the player"},
                    "message": {"type": "string", "description": "The chat message to send"}
                },
                "required": ["identifier", "message"],
            },
        ),
        types.Tool(
            name="execute_player_command",
            description="Executes a command for a given player",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "The name or unique id of the player"},
                    "command": {"type": "string", "description": "The command to execute (without prefixing slash)"},
                    "redirectToServer": {"type": "boolean", "description": "Redirect downstream if not found on proxy"}
                },
                "required": ["identifier", "command"],
            },
        ),
        types.Tool(
            name="execute_service_command",
            description="Executes the specified command on a service console",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "The name or unique id of the service"},
                    "command": {"type": "string", "description": "The command to execute on the service"}
                },
                "required": ["identifier", "command"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if arguments is None:
        arguments = {}

    if name == "get_nodes":
        data = await client.request("GET", "node")
        return [types.TextContent(type="text", text=str(data))]
    elif name == "get_node_info":
        node_id = arguments.get("node_id")
        if not node_id:
            raise ValueError("node_id is required")
        data = await client.request("GET", f"node/{node_id}")
        return [types.TextContent(type="text", text=str(data))]
    elif name == "get_services":
        data = await client.request("GET", "service")
        return [types.TextContent(type="text", text=str(data))]
    elif name == "get_online_players":
        params = {}
        for key in ["limit", "skip", "sort"]:
            if key in arguments:
                params[key] = arguments[key]
        data = await client.request("GET", "player/online", params=params)
        return [types.TextContent(type="text", text=str(data))]
    elif name == "get_player_info":
        identifier = arguments.get("identifier")
        data = await client.request("GET", f"player/online/{identifier}")
        return [types.TextContent(type="text", text=str(data))]
    elif name == "kick_player":
        identifier = arguments.get("identifier")
        msg = arguments.get("message")
        data = await client.request("POST", f"player/online/{identifier}/kick", json={"kickMessage": msg})
        return [types.TextContent(type="text", text=str(data))]
    elif name == "send_player_message":
        identifier = arguments.get("identifier")
        msg = arguments.get("message")
        data = await client.request("POST", f"player/online/{identifier}/sendChat", json={"chatMessage": msg})
        return [types.TextContent(type="text", text=str(data))]
    elif name == "execute_player_command":
        identifier = arguments.get("identifier")
        cmd = arguments.get("command")
        params = {}
        if "redirectToServer" in arguments:
            params["redirectToServer"] = str(arguments["redirectToServer"]).lower()
        data = await client.request("POST", f"player/online/{identifier}/command", params=params, json={"command": cmd})
        return [types.TextContent(type="text", text=str(data))]
    elif name == "execute_service_command":
        identifier = arguments.get("identifier")
        cmd = arguments.get("command")
        data = await client.request("POST", f"service/{identifier}/command", json={"command": cmd})
        return [types.TextContent(type="text", text=str(data))]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def run():
    async with stdio_server() as (read_stream, write_stream):
        try:
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
        finally:
            await client.close()

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
