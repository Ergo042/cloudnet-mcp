# CloudNet MCP Server

This is a Model Context Protocol (MCP) server that provides an interface to the [CloudNet Service](https://cloudnetservice.eu) REST API v3. This allows AI assistants to observe your CloudNet nodes and services safely and accurately.

## 🌟 Features

- **Get Nodes & Information**: List all cluster nodes and fetch detailed statistics.
- **Manage Services**: List active smart services and seamlessly execute commands on server consoles (`execute_service_command`).
- **Player Management**: Retrieve online players (`get_online_players`), inspect detailed player profiles (`get_player_info`), kick players from the network (`kick_player`), exchange messages (`send_player_message`), and act on their behalf via proxy or downstream bounds (`execute_player_command`).

*Developed based on the CloudNet Swagger Documentation.*

## 🛠 Prerequisites

- Python 3.12+
- `uv` Package Manager

## 📦 Installation

```bash
git clone https://github.com/yourusername/cloudnet-mcp.git
cd cloudnet-mcp
uv sync
```

## ⚙️ Configuration

Set the following environment variables before running:

- `CLOUDNET_URL`: The URL to the rest API (defaults to `http://127.0.0.1:2812/api/v3`)
- `CLOUDNET_USER`: The basic auth username
- `CLOUDNET_PASSWORD`: The basic auth password

## 🚀 Running

Using `uv`:
```bash
uv run cloudnet-mcp
```

## 🔌 Using with Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cloudnet": {
      "command": "uv",
      "args": [
        "--directory",
        "PATH/TO/YOUR/cloudnet-mcp",
        "run",
        "cloudnet-mcp"
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

## 🌟 功能特性

- **获取节点列表及信息**: 查看整个 CloudNet 集群内所有节点的详细统计数据和信息
- **管理服务 (Services)**: 获取运行中的智能服务列表，支持在服务端控制台远程异步执行命令 (`execute_service_command`)
- **玩家管理与交互 (Player Management)**: 查询在线玩家列表或通过唯一下位码查询 (`get_online_players`, `get_player_info`)、全局踢出玩家 (`kick_player`)、互发消息聊天 (`send_player_message`) 以及代替玩家执行代理层或子服命令 (`execute_player_command`)

*基于 CloudNet 官方 Swagger API 文档开发.*

## 🛠 前置要求

- Python 3.12 及以上版本
- `uv` 包管理器

## 📦 安装指南

```bash
git clone https://github.com/yourusername/cloudnet-mcp.git
cd cloudnet-mcp
uv sync
```

## ⚙️ 参数配置

在运行前，请配置以下环境变量：

- `CLOUDNET_URL`: CloudNet REST API 地址 (默认: `http://127.0.0.1:2812/api/v3`)
- `CLOUDNET_USER`: 基本认证的用户名
- `CLOUDNET_PASSWORD`: 基本认证的密码

## 🚀 运行方法

使用 `uv`:
```bash
uv run cloudnet-mcp
```

## 🔌 在 Claude Desktop 中使用

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
        "cloudnet-mcp"
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