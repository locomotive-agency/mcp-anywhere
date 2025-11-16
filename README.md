# MCP Anywhere

A unified gateway for Model Context Protocol (MCP) servers that enables discovery, configuration, and access to tools from GitHub repositories through a single endpoint.



https://github.com/user-attachments/assets/f011f8bf-6c99-4a8a-8236-f8eb0a3fb9e4



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

- [Getting Started](https://mcpanywhere.com/getting-started/) - Quick start guide and installation
- [Deployment Guide](https://mcpanywhere.com/deployment/) - Deploy to production with Fly.io

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
fly secrets set GOOGLE_OAUTH_CLIENT_ID=<google-oauth-client-id>
fly secrets set GOOGLE_OAUTH_CLIENT_SECRET=<google-oauth-client-secret>
fly deploy

# Application available at https://your-app.fly.dev
```

### Docker

Deploying the application as a docker container using docker compose.

```bash
# Configure environment
cp env.example .env
# Edit .env with required values:
# SECRET_KEY=<secure-random-key>
# ANTHROPIC_API_KEY=<your-api-key>
```

Build and Deploy the application

```bash
$ docker compose -f docker-compose.native.yml up -d --build
```

View logs to see status

```bash
$ docker logs mcp-anywhere-app
```

Navigate to `http://<DOCKER-HOST>:8000/` to use the application

## Usage

### Adding Tools from GitHub

Use the web interface to add MCP server repositories:
- Official MCP servers: `https://github.com/modelcontextprotocol/servers`
- Python interpreter: `https://github.com/yzfly/mcp-python-interpreter`
- Any compatible MCP repository

The system uses Claude AI to automatically analyze and configure repositories.

### Configuration

- **API Keys**: Centralized credential storage
- **Secret Files**: Secure upload and management of credential files (JSON, PEM, certificates)
- **Tool Management**: Enable or disable specific tools
- **Container Settings**: Automatic Docker containerization

### Secret File Management

MCP Anywhere supports secure upload and management of credential files for MCP servers:

**Supported File Types:**
- JSON credential files (.json)
- PEM certificates and keys (.pem, .key, .crt, .cert)
- PKCS12/PFX certificates (.p12, .pfx)
- Java KeyStores (.jks, .keystore)
- Configuration files (.yaml, .yml, .xml, .txt)

**Features:**
- Files are encrypted at rest using AES-128 (Fernet)
- Maximum file size: 10MB
- Files are mounted as read-only volumes in containers
- Environment variables automatically set with file paths
- Automatic cleanup when servers are deleted

**Usage via Web Interface:**
1. Navigate to the server detail page
2. Use the "Upload Secret File" form
3. Specify an environment variable name (e.g., `GOOGLE_APPLICATION_CREDENTIALS`)
4. Upload the credential file
5. The file will be automatically mounted when the container starts

**Security Considerations:**
- Files are stored encrypted in `DATA_DIR/secrets/<server_id>/`
- Each server has isolated secret storage
- Files are only decrypted when mounting to containers
- Container access is read-only

### Client Integration

**Claude Desktop Configuration:**

First run `which uv`, which will print out a path to the uv binary. For example on macOS:

```
/Users/yourname/.local/bin/uv
```

You can then use that in the start command. Change the `--directory` path to your MCP Anywhere clone path.

```json
{
  "mcpServers": {
    "mcp-anywhere": {
      "command": "/Users/yourname/.local/bin/uv",
      "args": ["run", "--directory", "/Users/yourname/Projects/mcp-anywhere", "mcp-anywhere", "connect"]
    }
  }
}
```

Lastly, set up the MCP Anywhere application before starting Claude Desktop:

```bash
uv run mcp-anywhere serve stdio
```

**Authentication Options:**

For Google OAuth (recommended for teams):
1. Set up Google OAuth credentials in Google Cloud Console
2. Configure environment variables:
   ```bash
   GOOGLE_OAUTH_CLIENT_ID=your-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   GOOGLE_OAUTH_REDIRECT_URI=/auth/callback
   OAUTH_USER_ALLOWED_DOMAIN=company.com  # Optional: restrict to your domain
   ```
3. Users can sign in with Google at `/auth/login`

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

### Authentication & Access Control
- Google OAuth integration - Sign in with Google for simplified authentication
- Domain-based access control - Restrict access to users from specific domains (e.g., @company.com)
- Session-based web authentication with secure cookie management
- JWT tokens for API access with proper scope validation

### Tool Discovery and Management
- Automatic repository analysis using Claude AI
- Container health monitoring with intelligent remounting
- Support for npx, uvx, and Docker runtimes
- Selective tool enablement with per-server controls
- Enhanced server management - Start, stop, and restart servers through web interface
- Pre-configured Python interpreter with sandbox isolation

### Security and Authentication
- Google OAuth integration for simplified user authentication
- Domain-based access control for organizational security
- OAuth 2.0/2.1 with PKCE support (MCP SDK implementation)
- JWT-based API authentication
- Docker container isolation for tool execution
- Session-based authentication for web interface
- Encrypted secret file storage (AES-128 with Fernet)

### Production Architecture
- Asynchronous architecture (Starlette/FastAPI)
- Health monitoring with automatic recovery
- Flexible container management with configurable startup/shutdown behavior
- Enhanced server lifecycle management with start/stop/restart controls
- Streamlined deployment process with GitHub Actions CI
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

# Container Management
CLEANUP_CONTAINERS_ON_SHUTDOWN    # Clean up containers on app shutdown (default: false)
REBUILD_CONTAINERS_ON_STARTUP     # Rebuild containers on startup (default: true)

# Google OAuth (optional - enables Google authentication)
GOOGLE_OAUTH_CLIENT_ID            # Google OAuth client ID
GOOGLE_OAUTH_CLIENT_SECRET        # Google OAuth client secret  
GOOGLE_OAUTH_REDIRECT_URI         # OAuth redirect URI (e.g., /auth/callback)
OAUTH_USER_ALLOWED_DOMAIN         # Restrict access to specific domain (e.g., company.com)
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
