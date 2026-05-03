import argparse
import asyncio
import json
import os
import re
from pathlib import Path
import httpx
import yaml
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server


# === Configuration Models ===

class QQModeConfig(BaseModel):
    """QQ Bot mode configuration."""
    enabled: bool = False
    style: str = "detailed"  # compact / detailed
    chinese_responses: bool = True
    safe_commands_only: bool = False
    max_message_length: int = 4000


class CommandDefinition(BaseModel):
    """Definition of a command with usage info."""
    command: str  # The command prefix (e.g., "kick", "whitelist add")
    args: str = ""  # Argument template (e.g., "<玩家> [原因]")
    description: str = ""  # Chinese description for QQ display

    def matches(self, input_command: str) -> bool:
        """Check if input command matches this definition."""
        return input_command.lower().startswith(self.command.lower())

    def to_simple_string(self) -> str:
        """Convert to simple command string for matching."""
        return self.command


def get_builtin_guest_commands() -> List[CommandDefinition]:
    """Get built-in guest level commands."""
    return [
        CommandDefinition(command="list", args="", description="查看在线玩家列表"),
        CommandDefinition(command="tps", args="", description="查看服务器TPS"),
        CommandDefinition(command="seed", args="", description="查看世界种子"),
        CommandDefinition(command="difficulty", args="", description="查看游戏难度"),
        CommandDefinition(command="whitelist list", args="", description="查看白名单列表"),
        CommandDefinition(command="time query", args="[daytime/gametime/day]", description="查询游戏时间"),
        CommandDefinition(command="gamerule query", args="<规则名>", description="查询游戏规则"),
        CommandDefinition(command="scoreboard objectives list", args="", description="列出计分板目标"),
        CommandDefinition(command="scoreboard players list", args="[目标名]", description="列出计分板玩家"),
        CommandDefinition(command="bossbar list", args="", description="列出Boss栏"),
        CommandDefinition(command="trigger", args="<目标>", description="触发计分板目标"),
    ]


def get_builtin_admin_commands() -> List[CommandDefinition]:
    """Get built-in admin level commands."""
    return [
        CommandDefinition(command="kick", args="<玩家> [原因]", description="踢出玩家"),
        CommandDefinition(command="ban", args="<玩家> [原因]", description="封禁玩家"),
        CommandDefinition(command="pardon", args="<玩家>", description="解封玩家"),
        CommandDefinition(command="ban-ip", args="<地址|玩家> [原因]", description="封禁IP"),
        CommandDefinition(command="pardon-ip", args="<地址>", description="解封IP"),
        CommandDefinition(command="whitelist add", args="<玩家>", description="添加白名单"),
        CommandDefinition(command="whitelist remove", args="<玩家>", description="移除白名单"),
        CommandDefinition(command="whitelist on", args="", description="开启白名单"),
        CommandDefinition(command="whitelist off", args="", description="关闭白名单"),
        CommandDefinition(command="whitelist reload", args="", description="重载白名单"),
        CommandDefinition(command="gamemode", args="<模式> [玩家]", description="设置游戏模式"),
        CommandDefinition(command="tp", args="<实体|坐标>", description="传送实体"),
        CommandDefinition(command="teleport", args="<实体|坐标>", description="传送实体"),
        CommandDefinition(command="give", args="<玩家> <物品> [数量]", description="给予物品"),
        CommandDefinition(command="clear", args="[玩家] [物品] [数量]", description="清除物品"),
        CommandDefinition(command="effect", args="<玩家> give|clear ...", description="给予/清除效果"),
        CommandDefinition(command="enchant", args="<玩家> <附魔> [等级]", description="附魔物品"),
        CommandDefinition(command="summon", args="<实体> [坐标] [数据]", description="召唤实体"),
        CommandDefinition(command="kill", args="[实体]", description="杀死实体"),
        CommandDefinition(command="fill", args="<起点> <终点> <方块>", description="填充方块"),
        CommandDefinition(command="setblock", args="<坐标> <方块>", description="设置方块"),
        CommandDefinition(command="clone", args="<起点> <终点> <目标>", description="复制方块"),
        CommandDefinition(command="weather", args="clear|rain|thunder [时长]", description="设置天气"),
        CommandDefinition(command="time set", args="<时间>", description="设置游戏时间"),
        CommandDefinition(command="title", args="<玩家> title|subtitle ...", description="显示标题"),
        CommandDefinition(command="tellraw", args="<玩家> <JSON>", description="发送原始消息"),
        CommandDefinition(command="msg", args="<玩家> <消息>", description="私聊玩家"),
        CommandDefinition(command="say", args="<消息>", description="广播消息"),
        CommandDefinition(command="bossbar set", args="<ID> ...", description="设置Boss栏"),
        CommandDefinition(command="scoreboard", args="objectives|players ...", description="计分板操作"),
        CommandDefinition(command="tag", args="<实体> add|remove|list ...", description="标签操作"),
        CommandDefinition(command="team", args="add|remove|modify ...", description="队伍操作"),
        CommandDefinition(command="loot", args="<目标> ...", description="战利品操作"),
        CommandDefinition(command="attribute", args="<实体> <属性> ...", description="属性操作"),
        CommandDefinition(command="item", args="replace|modify ...", description="物品操作"),
        CommandDefinition(command="locate", args="structure|biome <类型>", description="定位结构/生物群系"),
        CommandDefinition(command="spreadplayers", args="<坐标> <间距> ...", description="分散玩家"),
        CommandDefinition(command="spawnpoint", args="[玩家] [坐标]", description="设置出生点"),
        CommandDefinition(command="setworldspawn", args="[坐标]", description="设置世界出生点"),
        CommandDefinition(command="defaultspawnpoint", args="[玩家] [坐标]", description="设置默认出生点"),
        CommandDefinition(command="worldborder", args="set|center|damage ...", description="世界边界"),
    ]


def get_builtin_superuser_commands() -> List[CommandDefinition]:
    """Get built-in super user level commands."""
    return [
        CommandDefinition(command="stop", args="", description="停止服务器"),
        CommandDefinition(command="restart", args="", description="重启服务器"),
        CommandDefinition(command="reload", args="", description="重载数据包"),
        CommandDefinition(command="save-all", args="[flush]", description="保存所有"),
        CommandDefinition(command="save-off", args="", description="关闭自动保存"),
        CommandDefinition(command="save-on", args="", description="开启自动保存"),
        CommandDefinition(command="debug", args="start|stop", description="调试性能分析"),
        CommandDefinition(command="perf", args="start|stop", description="性能分析"),
        CommandDefinition(command="forceload", args="add|remove|query ...", description="强制加载区块"),
        CommandDefinition(command="gamerule", args="set <规则> <值>", description="设置游戏规则"),
        CommandDefinition(command="defaultgamemode", args="<模式>", description="设置默认游戏模式"),
        CommandDefinition(command="publish", args="[端口]", description="开放局域网"),
        CommandDefinition(command="datapack", args="list|enable|disable ...", description="数据包管理"),
        CommandDefinition(command="recipe", args="give|take <玩家> ...", description="配方管理"),
        CommandDefinition(command="advancement", args="grant|revoke ...", description="进度管理"),
        CommandDefinition(command="experience", args="add|set|query ...", description="经验操作"),
    ]


class SafeCommandsConfig(BaseModel):
    """Safe commands configuration by permission level."""
    guest: List[CommandDefinition] = Field(default_factory=get_builtin_guest_commands)
    admin: List[CommandDefinition] = Field(default_factory=get_builtin_admin_commands)
    super_user: List[CommandDefinition] = Field(default_factory=get_builtin_superuser_commands)

    @classmethod
    def from_yaml(cls, data: dict) -> "SafeCommandsConfig":
        """
        Parse from YAML with support for both string and object formats.

        Custom commands are MERGED with built-in commands.
        Use the command field as key to override built-in command descriptions.
        """
        def parse_commands(items: list) -> List[CommandDefinition]:
            result = []
            for item in items:
                if isinstance(item, str):
                    # Simple string format: "command"
                    result.append(CommandDefinition(command=item))
                elif isinstance(item, dict):
                    # Object format: {command: "...", args: "...", description: "..."}
                    result.append(CommandDefinition(**item))
            return result

        def merge_commands(
            builtin: List[CommandDefinition],
            custom: List[CommandDefinition]
        ) -> List[CommandDefinition]:
            """Merge custom commands with built-in, allowing overrides."""
            # Create a map of command -> definition for quick lookup
            cmd_map = {cmd.command.lower(): cmd for cmd in builtin}

            # Add or override with custom commands
            for cmd in custom:
                cmd_map[cmd.command.lower()] = cmd

            return list(cmd_map.values())

        # Get custom commands from config
        custom_guest = parse_commands(data.get("guest", []))
        custom_admin = parse_commands(data.get("admin", []))
        custom_superuser = parse_commands(data.get("super_user", []))

        # Merge with built-in commands
        return cls(
            guest=merge_commands(get_builtin_guest_commands(), custom_guest),
            admin=merge_commands(get_builtin_admin_commands(), custom_admin),
            super_user=merge_commands(get_builtin_superuser_commands(), custom_superuser),
        )


class Config(BaseModel):
    """Main configuration."""
    qq_mode: QQModeConfig = QQModeConfig()
    safe_commands: SafeCommandsConfig = Field(default_factory=SafeCommandsConfig)
    blocked_patterns: List[str] = Field(default_factory=lambda: ["op\\s+", "deop\\s+", "execute\\s+"])
    server_aliases: Dict[str, str] = Field(default_factory=dict)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="CloudNet MCP Server")
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file (YAML)"
    )
    return parser.parse_args()


def load_config(config_path: Optional[str]) -> Config:
    """Load configuration from YAML file."""
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Parse safe_commands with custom parser for backward compatibility
        if "safe_commands" in data:
            safe_commands = SafeCommandsConfig.from_yaml(data["safe_commands"])
            data["safe_commands"] = safe_commands

        return Config(**data)
    return Config()


# Global configuration
APP_CONFIG = Config()


# === Pydantic Response Models ===

class CommandResult(BaseModel):
    """Result of a service command execution."""
    success: bool = Field(description="Whether the command was executed successfully")
    service: str = Field(description="The service identifier")
    command: str = Field(description="The command that was executed")
    message: Optional[str] = Field(default=None, description="Additional status message")


class ServiceLogsResult(BaseModel):
    """Result of fetching service logs."""
    service: str = Field(description="The service identifier")
    total_lines: int = Field(description="Total number of lines available")
    returned_lines: int = Field(description="Number of lines returned")
    lines: List[str] = Field(description="The log lines")
    truncated: bool = Field(default=False, description="Whether output was truncated")


class ProcessSnapshot(BaseModel):
    """Process resource usage snapshot."""
    pid: int = Field(description="Process ID")
    cpu_usage: float = Field(description="CPU usage as percentage")
    heap_memory: int = Field(description="Current heap memory usage in bytes")


class ServiceInfo(BaseModel):
    """Detailed service information."""
    name: str = Field(description="Service name")
    unique_id: str = Field(description="Service unique ID")
    lifecycle: str = Field(description="Current lifecycle state")
    address: str = Field(description="Service address (host:port)")
    connect_address: Optional[str] = Field(default=None, description="Connection address")
    process: Optional[ProcessSnapshot] = Field(default=None, description="Process snapshot")


class DeleteServiceResult(BaseModel):
    """Result of deleting a service."""
    success: bool = Field(description="Whether deletion was successful")
    service: str = Field(description="The deleted service identifier")
    message: str = Field(description="Status message")


# === QQ Mode Response Models ===

class ServiceSummary(BaseModel):
    """Summary of a single service for QQ display."""
    name: str
    alias: Optional[str] = None
    lifecycle: str
    player_count: int = 0
    max_players: int = 0
    cpu_usage: float = 0.0
    memory_used: int = 0
    memory_max: int = 0


class ServicesSummaryResult(BaseModel):
    """Summary of all services for QQ display."""
    total_services: int
    running_services: int
    total_players: int
    services: List[ServiceSummary]


class PlayerSearchResult(BaseModel):
    """Result of searching for a player across services."""
    found: bool
    player_name: str
    server: Optional[str] = None
    online: bool = False


class SafeCommandResult(BaseModel):
    """Result of safe command execution."""
    allowed: bool
    command: str
    service: str
    message: str
    permission_required: Optional[str] = None


class CommandHelpItem(BaseModel):
    """Single command help item."""
    command: str
    args: str = ""
    description: str = ""

    def to_display(self) -> str:
        """Format for display."""
        if self.args:
            return f"{self.command} {self.args} - {self.description}"
        return f"{self.command} - {self.description}"


class CommandHelpResult(BaseModel):
    """Available commands help for QQ users."""
    environment: str
    permission_level: str
    commands: Dict[str, List[CommandHelpItem]]


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
        self.token = data.get("accessToken", {}).get("token")
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

    async def request_with_error(self, method: str, endpoint: str, **kwargs) -> tuple[dict, bool]:
        """
        Make a request and return (data, is_error) tuple.

        Returns:
            tuple: (response_data, is_error_flag)
        """
        if not self.token:
            await self._authenticate()

        path = endpoint.lstrip("/")
        url = f"{self.base_url}/{path}"

        try:
            resp = await self.client.request(method, url, **kwargs)
            if resp.status_code == 401:
                await self._authenticate()
                resp = await self.client.request(method, url, **kwargs)

            if resp.status_code >= 400:
                error_data = {}
                try:
                    error_data = resp.json()
                except Exception:
                    pass
                return {
                    "error": True,
                    "status_code": resp.status_code,
                    "message": error_data.get("detail", f"HTTP {resp.status_code}"),
                    "title": error_data.get("title", "Request failed")
                }, True

            if resp.status_code == 204:
                return {"status": "success"}, False

            return resp.json(), False

        except httpx.HTTPError as e:
            return {
                "error": True,
                "message": str(e),
                "title": "Connection error"
            }, True

    async def execute_service_command(
        self,
        identifier: str,
        command: str
    ) -> tuple[CommandResult, bool]:
        """Execute a command on a service and return structured result."""
        if not identifier:
            raise ValueError("identifier is required")
        if not command:
            raise ValueError("command is required")

        data, is_error = await self.request_with_error(
            "POST",
            f"service/{identifier}/command",
            json={"command": command}
        )

        if is_error:
            return CommandResult(
                success=False,
                service=identifier,
                command=command,
                message=data.get("message", "Command execution failed")
            ), True

        return CommandResult(
            success=True,
            service=identifier,
            command=command,
            message="Command executed successfully"
        ), False

    async def get_service_logs(
        self,
        identifier: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        pattern: Optional[str] = None,
        tail: Optional[int] = None
    ) -> tuple[ServiceLogsResult, bool]:
        """
        Get service logs with optional filtering.

        Args:
            identifier: Service name or unique ID
            limit: Maximum number of lines to return
            offset: Number of lines to skip from start
            pattern: Regex pattern to filter lines
            tail: Get last N lines (overrides limit/offset)
        """
        if not identifier:
            raise ValueError("identifier is required")

        data, is_error = await self.request_with_error(
            "GET",
            f"service/{identifier}/logLines"
        )

        if is_error:
            return ServiceLogsResult(
                service=identifier,
                total_lines=0,
                returned_lines=0,
                lines=[]
            ), True

        lines = data.get("lines", []) if isinstance(data, dict) else []
        total_lines = len(lines)

        # Apply tail option (last N lines)
        if tail is not None and tail > 0:
            lines = lines[-tail:]
        else:
            # Apply offset
            if offset is not None and offset > 0:
                lines = lines[offset:]
            # Apply limit
            if limit is not None and limit > 0:
                lines = lines[:limit]

        # Apply pattern filtering
        if pattern:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                lines = [line for line in lines if regex.search(line)]
            except re.error:
                pass  # Invalid regex, return unfiltered

        return ServiceLogsResult(
            service=identifier,
            total_lines=total_lines,
            returned_lines=len(lines),
            lines=lines,
            truncated=len(lines) > 1000  # Safety limit
        ), False

    async def get_service_info(self, identifier: str) -> tuple[ServiceInfo, bool]:
        """Get detailed service information."""
        if not identifier:
            raise ValueError("identifier is required")

        data, is_error = await self.request_with_error(
            "GET",
            f"service/{identifier}"
        )

        if is_error:
            return ServiceInfo(
                name=identifier,
                unique_id="",
                lifecycle="UNKNOWN",
                address=""
            ), True

        # Parse process snapshot
        process_data = data.get("processSnapshot", {}) if isinstance(data, dict) else {}
        process = None
        if process_data:
            process = ProcessSnapshot(
                pid=process_data.get("pid", 0),
                cpu_usage=process_data.get("cpuUsage", 0.0),
                heap_memory=process_data.get("heapUsageMemory", 0)
            )

        # Parse address
        address_data = data.get("address", {}) if isinstance(data, dict) else {}
        host = address_data.get("host", "0.0.0.0") if isinstance(address_data, dict) else "0.0.0.0"
        port = address_data.get("port", 0) if isinstance(address_data, dict) else 0
        address = f"{host}:{port}"

        # Parse connect address
        connect_data = data.get("connectAddress", {}) if isinstance(data, dict) else {}
        connect_host = connect_data.get("host", "") if isinstance(connect_data, dict) else ""
        connect_port = connect_data.get("port", 0) if isinstance(connect_data, dict) else 0
        connect_address = f"{connect_host}:{connect_port}" if connect_host else None

        return ServiceInfo(
            name=data.get("name", identifier) if isinstance(data, dict) else identifier,
            unique_id=data.get("uniqueId", "") if isinstance(data, dict) else "",
            lifecycle=data.get("lifeCycle", "UNKNOWN") if isinstance(data, dict) else "UNKNOWN",
            address=address,
            connect_address=connect_address,
            process=process
        ), False

    async def delete_service(self, identifier: str) -> tuple[DeleteServiceResult, bool]:
        """Delete a service."""
        if not identifier:
            raise ValueError("identifier is required")

        data, is_error = await self.request_with_error(
            "DELETE",
            f"service/{identifier}"
        )

        if is_error:
            return DeleteServiceResult(
                success=False,
                service=identifier,
                message=data.get("message", "Failed to delete service")
            ), True

        return DeleteServiceResult(
            success=True,
            service=identifier,
            message="Service deleted successfully"
        ), False

    async def close(self):
        await self.client.aclose()


client = CloudNetClient(CLOUDNET_URL, CLOUDNET_USER, CLOUDNET_PASSWORD)


# === Helper Functions ===

def format_result(data: BaseModel, is_error: bool = False) -> types.CallToolResult:
    """Format a Pydantic model as a CallToolResult."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(data.model_dump(), indent=2))],
        isError=is_error
    )


def format_error(message: str, details: dict = None) -> types.CallToolResult:
    """Format an error response."""
    error_data = {"error": True, "message": message}
    if details:
        error_data.update(details)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(error_data, indent=2))],
        isError=True
    )


# === QQ Mode Helper Functions ===

def format_qq_message(text: str, max_length: int = 4000) -> str:
    """Format message for QQ with length limit."""
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


def get_server_alias(name: str) -> str:
    """Get friendly server name from alias config."""
    return APP_CONFIG.server_aliases.get(name, name)


def check_safe_command(command: str, permission: str = "guest") -> tuple[bool, str]:
    """
    Check if command is in safe list for permission level.

    Permission hierarchy:
    - guest: can only use guest commands
    - admin: can use admin + guest commands
    - super_user: can use all commands
    """
    if not APP_CONFIG.qq_mode.safe_commands_only:
        return True, "allowed"

    # Check blocked patterns first
    for pattern in APP_CONFIG.blocked_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False, "blocked"

    # Define which levels each permission can access
    # Higher privilege includes lower privilege commands
    accessible_levels = {
        "guest": ["guest"],
        "admin": ["admin", "guest"],
        "super_user": ["super_user", "admin", "guest"],
    }

    levels_to_check = accessible_levels.get(permission, ["guest"])

    # Check if command matches any safe command definition in accessible levels
    for level in levels_to_check:
        safe_commands = getattr(APP_CONFIG.safe_commands, level, [])
        for cmd_def in safe_commands:
            if cmd_def.matches(command):
                return True, "allowed"

    return False, "permission_denied"


def get_all_commands_for_permission(permission: str) -> List[CommandDefinition]:
    """Get all available commands for a permission level (including higher levels)."""
    levels = ["guest", "admin", "super_user"]
    start_idx = levels.index(permission) if permission in levels else 0

    commands = []
    for level in levels[start_idx:]:
        commands.extend(getattr(APP_CONFIG.safe_commands, level, []))

    return commands


def get_qq_tools() -> list[types.Tool]:
    """Get QQ-optimized tools."""
    return [
        types.Tool(
            name="get_services_summary",
            description=(
                "获取所有服务的摘要状态 (QQ优化). "
                "返回适合QQ群显示的服务器状态总览."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="find_player",
            description=(
                "跨服查找玩家 (QQ优化). "
                "搜索玩家所在的服务器."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "玩家名称 (支持模糊匹配)"
                    }
                },
                "required": ["player_name"],
            },
        ),
        types.Tool(
            name="get_command_help",
            description=(
                "获取可用命令列表 (QQ优化). "
                "显示指定服务类型支持的命令和权限要求."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": ["MINECRAFT_SERVER", "VELOCITY", "BUNGEECORD"],
                        "description": "服务类型"
                    },
                    "permission_level": {
                        "type": "string",
                        "enum": ["guest", "admin", "super_user"],
                        "default": "guest",
                        "description": "权限级别"
                    }
                },
                "required": ["environment"],
            },
        ),
        types.Tool(
            name="execute_safe_command",
            description=(
                "安全执行预定义命令 (QQ优化). "
                "只允许执行配置的安全命令列表中的命令."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "服务名称或唯一ID"
                    },
                    "command": {
                        "type": "string",
                        "description": "要执行的命令 (不含斜杠前缀)"
                    },
                    "permission_level": {
                        "type": "string",
                        "enum": ["guest", "admin", "super_user"],
                        "default": "guest",
                        "description": "当前用户权限级别"
                    }
                },
                "required": ["identifier", "command"],
            },
        ),
    ]


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
            name="get_online_player_count",
            description="Get the total number of currently online players in the network",
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
                    "limit": {"type": "integer", "description": "The maximum amount of players to respond with (max 25)", "maximum": 25},
                    "offset": {"type": "integer", "description": "The amount of players to skip"},
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
            description=(
                "Executes a command on a service console. "
                "Returns structured result indicating success or failure. "
                "Use this to run Minecraft server commands like 'list', 'whitelist on', etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "The name or unique ID of the service (e.g., 'Lobby-1')"
                    },
                    "command": {
                        "type": "string",
                        "description": "The command to execute (without leading slash)"
                    }
                },
                "required": ["identifier", "command"],
            },
        ),
        types.Tool(
            name="get_tasks",
            description="Lists all tasks that are known by the node",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="get_task_info",
            description="Get detailed information about a specific task",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the task to get"}
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="change_service_lifecycle",
            description="Updates the lifecycle of a service (start, stop, restart)",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "The name or unique id of the service"},
                    "target": {"type": "string", "enum": ["start", "stop", "restart"], "description": "The target service lifecycle phase"}
                },
                "required": ["identifier", "target"],
            },
        ),
        types.Tool(
            name="get_service_logs",
            description=(
                "Get cached log lines from a service with optional filtering. "
                "Supports pagination (limit/offset), pattern matching, and tail (last N lines). "
                "Returns structured log data with line counts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "The name or unique ID of the service"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to return (default: 100)",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of lines to skip from the beginning",
                        "default": 0,
                        "minimum": 0
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to filter log lines (case-insensitive)"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Get last N lines only (overrides limit/offset)",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["identifier"],
            },
        ),
        types.Tool(
            name="get_service_info",
            description=(
                "Get detailed information about a specific service. "
                "Includes lifecycle state, address, CPU/memory usage, and process details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "The name or unique ID of the service"
                    }
                },
                "required": ["identifier"],
            },
        ),
        types.Tool(
            name="delete_service",
            description=(
                "Delete a service from the cluster. "
                "WARNING: This action is irreversible. The service will be stopped and removed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "The name or unique ID of the service to delete"
                    }
                },
                "required": ["identifier"],
            },
        ),
        types.Tool(
            name="get_api_token",
            description="Gets the currently active access token for the REST API",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="refresh_api_token",
            description="Forces an immediate refresh of the REST API access token",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

    # Add QQ-optimized tools if QQ mode is enabled
    if APP_CONFIG.qq_mode.enabled:
        tools.extend(get_qq_tools())

    return tools

@app.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any] | None
) -> types.CallToolResult:
    if arguments is None:
        arguments = {}

    try:
        if name == "get_nodes":
            data = await client.request("GET", "node")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "get_node_info":
            node_id = arguments.get("node_id")
            if not node_id:
                return format_error("node_id is required")
            data = await client.request("GET", f"node/{node_id}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "get_services":
            data = await client.request("GET", "service")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "get_online_player_count":
            data = await client.request("GET", "player/onlineCount")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "get_online_players":
            params = {}
            for key in ["limit", "offset", "sort"]:
                if key in arguments:
                    params[key] = arguments[key]
            data = await client.request("GET", "player/online", params=params)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "get_player_info":
            identifier = arguments.get("identifier")
            if not identifier:
                return format_error("identifier is required")
            data = await client.request("GET", f"player/online/{identifier}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "kick_player":
            identifier = arguments.get("identifier")
            msg = arguments.get("message")
            if not identifier:
                return format_error("identifier is required")
            if not msg:
                return format_error("message is required")
            data = await client.request("POST", f"player/online/{identifier}/kick", json={"kickMessage": msg})
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "send_player_message":
            identifier = arguments.get("identifier")
            msg = arguments.get("message")
            if not identifier:
                return format_error("identifier is required")
            if not msg:
                return format_error("message is required")
            data = await client.request("POST", f"player/online/{identifier}/sendChat", json={"chatMessage": msg})
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "execute_player_command":
            identifier = arguments.get("identifier")
            cmd = arguments.get("command")
            if not identifier:
                return format_error("identifier is required")
            if not cmd:
                return format_error("command is required")
            params = {}
            if "redirectToServer" in arguments:
                params["redirectToServer"] = str(arguments["redirectToServer"]).lower()
            data = await client.request("POST", f"player/online/{identifier}/command", params=params, json={"command": cmd})
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "execute_service_command":
            identifier = arguments.get("identifier")
            cmd = arguments.get("command")
            if not identifier:
                return format_error("identifier is required")
            if not cmd:
                return format_error("command is required")
            result, is_error = await client.execute_service_command(identifier, cmd)
            return format_result(result, is_error)

        elif name == "get_tasks":
            data = await client.request("GET", "task")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "get_task_info":
            name_arg = arguments.get("name")
            if not name_arg:
                return format_error("name is required")
            data = await client.request("GET", f"task/{name_arg}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "change_service_lifecycle":
            identifier = arguments.get("identifier")
            target = arguments.get("target")
            if not identifier:
                return format_error("identifier is required")
            if not target:
                return format_error("target is required")
            data = await client.request("PATCH", f"service/{identifier}/lifecycle", params={"target": target})
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
            )

        elif name == "get_service_logs":
            identifier = arguments.get("identifier")
            if not identifier:
                return format_error("identifier is required")
            result, is_error = await client.get_service_logs(
                identifier=identifier,
                limit=arguments.get("limit"),
                offset=arguments.get("offset"),
                pattern=arguments.get("pattern"),
                tail=arguments.get("tail")
            )
            return format_result(result, is_error)

        elif name == "get_service_info":
            identifier = arguments.get("identifier")
            if not identifier:
                return format_error("identifier is required")
            result, is_error = await client.get_service_info(identifier)
            return format_result(result, is_error)

        elif name == "delete_service":
            identifier = arguments.get("identifier")
            if not identifier:
                return format_error("identifier is required")
            result, is_error = await client.delete_service(identifier)
            return format_result(result, is_error)

        elif name == "get_api_token":
            if not client.token:
                await client._authenticate()
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps({"token": client.token}, indent=2))]
            )

        elif name == "refresh_api_token":
            await client._authenticate()
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps({"token": client.token, "status": "refreshed"}, indent=2))]
            )

        # === QQ Mode Tools ===
        elif name == "get_services_summary":
            data = await client.request("GET", "service")
            services_data = data.get("services", []) if isinstance(data, dict) else []

            summaries = []
            total_players = 0
            running_count = 0

            for svc in services_data:
                if not isinstance(svc, dict):
                    continue

                lifecycle = svc.get("lifeCycle", "UNKNOWN")
                if lifecycle == "RUNNING":
                    running_count += 1

                process = svc.get("processSnapshot", {}) or {}
                address = svc.get("address", {}) or {}

                summary = ServiceSummary(
                    name=svc.get("name", "Unknown"),
                    alias=get_server_alias(svc.get("name", "")),
                    lifecycle=lifecycle,
                    player_count=0,  # Would need additional API call for accurate count
                    max_players=0,
                    cpu_usage=process.get("cpuUsage", 0.0),
                    memory_used=process.get("heapUsageMemory", 0),
                    memory_max=process.get("maxHeapMemory", 0)
                )
                summaries.append(summary)

            result = ServicesSummaryResult(
                total_services=len(summaries),
                running_services=running_count,
                total_players=total_players,
                services=summaries
            )
            return format_result(result)

        elif name == "find_player":
            player_name = arguments.get("player_name", "").lower()
            if not player_name:
                return format_error("player_name is required")

            # Get online players
            data = await client.request("GET", "player/online")
            players = data.get("onlinePlayers", []) if isinstance(data, dict) else []

            for player in players:
                if not isinstance(player, dict):
                    continue
                name = player.get("name", "").lower()
                if player_name in name or name in player_name:
                    connected_service = player.get("connectedService", {}) or {}
                    result = PlayerSearchResult(
                        found=True,
                        player_name=player.get("name", ""),
                        server=connected_service.get("name"),
                        online=True
                    )
                    return format_result(result)

            result = PlayerSearchResult(
                found=False,
                player_name=arguments.get("player_name", ""),
                server=None,
                online=False
            )
            return format_result(result)

        elif name == "get_command_help":
            environment = arguments.get("environment", "MINECRAFT_SERVER")
            permission = arguments.get("permission_level", "guest")

            # Get commands from config for this permission level and higher
            commands_by_level: Dict[str, List[CommandHelpItem]] = {}
            levels = ["guest", "admin", "super_user"]
            start_idx = levels.index(permission) if permission in levels else 0

            for level in levels[start_idx:]:
                cmd_defs = getattr(APP_CONFIG.safe_commands, level, [])
                commands_by_level[level] = [
                    CommandHelpItem(
                        command=cmd.command,
                        args=cmd.args,
                        description=cmd.description
                    )
                    for cmd in cmd_defs
                ]

            result = CommandHelpResult(
                environment=environment,
                permission_level=permission,
                commands=commands_by_level
            )
            return format_result(result)

        elif name == "execute_safe_command":
            identifier = arguments.get("identifier")
            command = arguments.get("command")
            permission = arguments.get("permission_level", "guest")

            if not identifier:
                return format_error("identifier is required")
            if not command:
                return format_error("command is required")

            # Check if command is allowed
            allowed, reason = check_safe_command(command, permission)

            if not allowed:
                result = SafeCommandResult(
                    allowed=False,
                    command=command,
                    service=identifier,
                    message="命令被拒绝: 不在安全命令列表中" if reason == "blocked" else "命令被拒绝: 权限不足",
                    permission_required="admin" if permission == "guest" else "super_user"
                )
                return format_result(result, is_error=True)

            # Execute the command
            cmd_result, is_error = await client.execute_service_command(identifier, command)

            result = SafeCommandResult(
                allowed=True,
                command=command,
                service=identifier,
                message=cmd_result.message or ("执行成功" if cmd_result.success else "执行失败")
            )
            return format_result(result, is_error=is_error)

        else:
            return format_error(f"Unknown tool: {name}")

    except ValueError as e:
        return format_error(str(e))
    except Exception as e:
        return format_error(f"Unexpected error: {str(e)}")

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
    global APP_CONFIG
    args = parse_args()
    APP_CONFIG = load_config(args.config)
    asyncio.run(run())

if __name__ == "__main__":
    main()
