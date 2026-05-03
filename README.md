# CloudNet MCP Server

This is a Model Context Protocol (MCP) server that provides an interface to the [CloudNet Service](https://cloudnetservice.eu) REST API v3. This allows AI assistants to observe your CloudNet nodes and services safely and accurately.

## Features

- **Get Nodes & Information**: List all cluster nodes and fetch detailed statistics.
- **Manage Services**: List active smart services and seamlessly execute commands on server consoles.
- **Player Management**: Retrieve online players, inspect player profiles, kick players, send messages, and execute commands on their behalf.
- **QQ Bot Mode**: Optimized for QQ group server management bots with safe command execution.

## Prerequisites

- Python 3.12+
- `uv` Package Manager

## Installation

```bash
git clone https://github.com/yourusername/cloudnet-mcp.git
cd cloudnet-mcp
uv sync
```

## Configuration

### Environment Variables

- `CLOUDNET_URL`: The URL to the REST API (default: `http://127.0.0.1:2812/api/v3`)
- `CLOUDNET_USER`: Basic auth username
- `CLOUDNET_PASSWORD`: Basic auth password

### QQ Bot Mode (Optional)

Copy the example config and customize:

```bash
cp config.example.yaml config.yaml
```

Enable QQ mode in `config.yaml`:

```yaml
qq_mode:
  enabled: true
  safe_commands_only: true
  chinese_responses: true
```

## Running

```bash
# Basic usage
uv run cloudnet-mcp

# With config file
uv run cloudnet-mcp -c config.yaml
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-c, --config` | Path to YAML configuration file |

## QQ Bot Mode

When QQ mode is enabled, additional tools become available:

| Tool | Description |
|------|-------------|
| `get_services_summary` | Get server status overview |
| `find_player` | Search player across servers |
| `get_command_help` | List available commands by permission |
| `execute_safe_command` | Execute whitelisted commands only |

### Safe Command Execution

Commands are organized by permission level:

- **Guest**: Query commands (`list`, `tps`, `seed`, etc.)
- **Admin**: Management commands (`kick`, `ban`, `whitelist`, `gamemode`, etc.)
- **Super User**: Server commands (`stop`, `restart`, `reload`, etc.)

Permission inheritance: Admin inherits Guest, Super User inherits all.

### Custom Commands

Add custom commands in `config.yaml`:

```yaml
safe_commands:
  guest:
    - command: stats
      args: "<player>"
      description: "View player statistics"
  admin:
    - command: money
      args: "set <player> <amount>"
      description: "Set player balance"
```

Custom commands merge with built-in commands. Override built-in descriptions by using the same command name.

### Blocked Commands

These patterns are always blocked:

- `op` - Grant operator status
- `deop` - Revoke operator status
- `execute` - Execute as another entity

## Using with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cloudnet": {
      "command": "uv",
      "args": [
        "--directory",
        "PATH/TO/YOUR/cloudnet-mcp",
        "run",
        "cloudnet-mcp",
        "-c",
        "PATH/TO/YOUR/cloudnet-mcp/config.yaml"
      ],
      "env": {
        "CLOUDNET_URL": "http://127.0.0.1:2812/api/v3",
        "CLOUDNET_USER": "your_user",
        "CLOUDNET_PASSWORD": "your_password"
      }
    }
  }
}
```

---

# CloudNet MCP 服务器

这是一个模型上下文协议 (MCP) 服务器，提供了对 [CloudNet Service](https://cloudnetservice.eu) REST API v3 的接口访问支持。它使得 AI 助手能够安全准确地观测您的 CloudNet 节点和服务。

## 功能特性

- **获取节点列表及信息**: 查看整个 CloudNet 集群内所有节点的详细统计数据和信息
- **管理服务**: 获取运行中的智能服务列表，支持在服务端控制台远程执行命令
- **玩家管理**: 查询在线玩家、查看玩家详情、踢出玩家、发送消息、代替玩家执行命令
- **QQ Bot 模式**: 针对 QQ 群服务器管理机器人的优化模式，支持安全命令执行

## 前置要求

- Python 3.12 及以上版本
- `uv` 包管理器

## 安装指南

```bash
git clone https://github.com/yourusername/cloudnet-mcp.git
cd cloudnet-mcp
uv sync
```

## 配置

### 环境变量

- `CLOUDNET_URL`: CloudNet REST API 地址 (默认: `http://127.0.0.1:2812/api/v3`)
- `CLOUDNET_USER`: 基本认证的用户名
- `CLOUDNET_PASSWORD`: 基本认证的密码

### QQ Bot 模式 (可选)

复制示例配置文件并修改：

```bash
cp config.example.yaml config.yaml
```

在 `config.yaml` 中启用 QQ 模式：

```yaml
qq_mode:
  enabled: true
  safe_commands_only: true
  chinese_responses: true
```

## 运行

```bash
# 基本用法
uv run cloudnet-mcp

# 使用配置文件
uv run cloudnet-mcp -c config.yaml
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `-c, --config` | YAML 配置文件路径 |

## QQ Bot 模式

启用 QQ 模式后，将提供以下额外工具：

| 工具 | 说明 |
|------|------|
| `get_services_summary` | 获取服务器状态总览 |
| `find_player` | 跨服搜索玩家 |
| `get_command_help` | 按权限列出可用命令 |
| `execute_safe_command` | 仅执行白名单内的命令 |

### 安全命令执行

命令按权限级别组织：

- **Guest (访客)**: 查询类命令 (`list`, `tps`, `seed` 等)
- **Admin (管理员)**: 管理类命令 (`kick`, `ban`, `whitelist`, `gamemode` 等)
- **Super User (超级用户)**: 服务器管理命令 (`stop`, `restart`, `reload` 等)

权限继承：管理员继承访客权限，超级用户继承所有权限。

### 内置命令列表

<details>
<summary>点击展开完整命令列表</summary>

**Guest 级别 (11个)**:
- `list` - 查看在线玩家列表
- `tps` - 查看服务器TPS
- `seed` - 查看世界种子
- `difficulty` - 查看游戏难度
- `whitelist list` - 查看白名单列表
- `time query` - 查询游戏时间
- `gamerule query` - 查询游戏规则
- `scoreboard objectives list` - 列出计分板目标
- `scoreboard players list` - 列出计分板玩家
- `bossbar list` - 列出Boss栏
- `trigger` - 触发计分板目标

**Admin 级别 (41个)**:
- `kick <玩家> [原因]` - 踢出玩家
- `ban <玩家> [原因]` - 封禁玩家
- `pardon <玩家>` - 解封玩家
- `ban-ip <地址|玩家> [原因]` - 封禁IP
- `pardon-ip <地址>` - 解封IP
- `whitelist add/remove <玩家>` - 白名单管理
- `whitelist on/off/reload` - 白名单开关与重载
- `gamemode <模式> [玩家]` - 设置游戏模式
- `tp <实体|坐标>` - 传送实体
- `give <玩家> <物品> [数量]` - 给予物品
- `clear [玩家] [物品] [数量]` - 清除物品
- `effect <玩家> give|clear` - 给予/清除效果
- `enchant <玩家> <附魔> [等级]` - 附魔物品
- `summon <实体> [坐标]` - 召唤实体
- `kill [实体]` - 杀死实体
- `fill/setblock/clone` - 方块操作
- `weather clear|rain|thunder` - 设置天气
- `time set <时间>` - 设置游戏时间
- 更多...

**Super User 级别 (16个)**:
- `stop` - 停止服务器
- `restart` - 重启服务器
- `reload` - 重载数据包
- `save-all/save-off/save-on` - 保存控制
- `debug start|stop` - 调试性能分析
- `gamerule set <规则> <值>` - 设置游戏规则
- `defaultgamemode <模式>` - 设置默认游戏模式
- 更多...

</details>

### 自定义命令

在 `config.yaml` 中添加自定义命令：

```yaml
safe_commands:
  guest:
    - command: stats
      args: "<玩家>"
      description: "查看玩家统计"
    - command: ping
      description: "查看延迟"
  admin:
    - command: money
      args: "set <玩家> <金额>"
      description: "设置玩家余额"
    - command: heal
      args: "[玩家]"
      description: "治疗玩家"
  super_user:
    - command: plugins
      description: "查看插件列表"
```

自定义命令会与内置命令合并。使用相同的命令名可覆盖内置命令的描述。

### 被阻止的命令

以下命令模板始终被阻止：

- `op` - 授予管理员权限
- `deop` - 撤销管理员权限
- `execute` - 以其他实体身份执行

## 在 Claude Desktop 中使用

将以下配置添加至您的 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "cloudnet": {
      "command": "uv",
      "args": [
        "--directory",
        "PATH/TO/YOUR/cloudnet-mcp",
        "run",
        "cloudnet-mcp",
        "-c",
        "PATH/TO/YOUR/cloudnet-mcp/config.yaml"
      ],
      "env": {
        "CLOUDNET_URL": "http://127.0.0.1:2812/api/v3",
        "CLOUDNET_USER": "您的用户名",
        "CLOUDNET_PASSWORD": "您的密码"
      }
    }
  }
}
```
