# MCP Anywhere

A unified gateway for Model Context Protocol (MCP) servers that enables discovery, configuration, and access to tools from GitHub repositories through a single endpoint.

> **Current Version**: 0.8.0  
> **Note**: This project is in beta. APIs and features are subject to change.

## Overview

MCP Anywhere provides:
- Automatic tool discovery from GitHub repositories
- Centralized API key and credential management
- Selective tool enablement and access control
- Unified endpoint for all MCP tools
- Docker-based isolation for secure execution

## Documentation

📚 **Full documentation is available at [mcpanywhere.com](https://mcpanywhere.com)**

- [Quick Start Guide](https://mcpanywhere.com/getting-started/quick-start/) - Get up and running in 5 minutes
- [Installation Guide](https://mcpanywhere.com/getting-started/installation/) - Local and production setup
- [Adding MCP Servers](https://mcpanywhere.com/guide/adding-servers/) - Discover and configure tools
- [Claude Desktop Integration](https://mcpanywhere.com/integration/claude-desktop/) - Connect to Claude Desktop
- [API Reference](https://mcpanywhere.com/api-reference/) - Complete API documentation

## Installation

### Local Installation

```bash
# Clone repository
git clone https://github.com/locomotive-agency/mcp-anywhere.git
cd mcp-anywhere

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .

# Configure environment
cp env.example .env
# Edit .env with required values:
# SECRET_KEY=<secure-random-key>
# ANTHROPIC_API_KEY=<your-api-key>

# Start server
mcp-anywhere serve http
# Or: python -m mcp_anywhere serve http
# Access at http://localhost:8000
```

### Production Deployment (Fly.io)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Deploy application
cd mcp-anywhere
fly launch
fly secrets set SECRET_KEY=<secure-random-key>
fly secrets set JWT_SECRET_KEY=<jwt-secret-key>
fly secrets set ANTHROPIC_API_KEY=<your-api-key>
fly deploy

# Application available at https://your-app.fly.dev
```

## Usage

### Adding Tools from GitHub

Use the web interface to add MCP server repositories:
- Official MCP servers: `https://github.com/modelcontextprotocol/servers`
- Python interpreter: `https://github.com/yzfly/mcp-python-interpreter`
- Any compatible MCP repository

The system uses Claude AI to automatically analyze and configure repositories.

### Configuration

- **API Keys**: Centralized credential storage
- **Tool Management**: Enable or disable specific tools
- **Container Settings**: Automatic Docker containerization

### Client Integration

**Claude Desktop Configuration:**
```json
{
  "mcpServers": {
    "mcp-anywhere": {
      "command": "mcp-anywhere",
      "args": ["connect"]
    }
  }
}
```

**HTTP API Integration:**
```python
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

async with Client(
    "https://your-app.fly.dev/mcp/",
    auth=BearerAuth(token="<oauth-token>")
) as client:
    tools = await client.list_tools()
```

**Command Line Interface:**
```bash
# For MCP client connection
mcp-anywhere connect
# Or: python -m mcp_anywhere connect

# For STDIO server mode (local Claude Desktop integration)
mcp-anywhere serve stdio

# For HTTP server mode with OAuth (production)
mcp-anywhere serve http --host 0.0.0.0 --port 8000
```

## Features

### Tool Discovery and Management
- Automatic repository analysis using Claude AI
- Container health monitoring with intelligent remounting
- Support for npx, uvx, and Docker runtimes
- Selective tool enablement
- Pre-configured Python interpreter

### Security and Authentication
- OAuth 2.0/2.1 with PKCE support (MCP SDK implementation)
- JWT-based API authentication
- Docker container isolation for tool execution
- Session-based authentication for web interface

### Production Architecture
- Asynchronous architecture (Starlette/FastAPI)
- Health monitoring with automatic recovery
- Streamlined deployment process
- CLI support for direct tool access

## Architecture

```
Client Application → MCP Anywhere Gateway → Docker Containers → MCP Tools
                            ↓
                    Web Management Interface
```

## Contributing

Areas for contribution:

- Oauth review and additional provider support
- Container efficiency and latency
- Improve tests
- Documentation



## Configuration

### Required Environment Variables
```bash
SECRET_KEY                  # Session encryption key
ANTHROPIC_API_KEY          # Claude API key for repository analysis
```

### Optional Environment Variables
```bash
JWT_SECRET_KEY             # JWT token signing key (defaults to SECRET_KEY)
WEB_PORT                   # Web interface port (default: 8000)
DATA_DIR                   # Data storage directory (default: .data)
DOCKER_TIMEOUT             # Container operation timeout in seconds (default: 300)
LOG_LEVEL                  # Logging level (default: INFO)
GITHUB_TOKEN               # GitHub token for private repository access
```

## Development

### Development Setup
```bash
# Install development dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=mcp_anywhere
```

### Debug Mode
```bash
LOG_LEVEL=DEBUG mcp-anywhere serve http
```

### Data Reset
```bash
mcp-anywhere reset --confirm
```

## Support

- [GitHub Issues](https://github.com/locomotive-agency/mcp-anywhere/issues)
- [GitHub Discussions](https://github.com/locomotive-agency/mcp-anywhere/discussions)

## License

See [LICENSE](LICENSE)