# MCP Anywhere

<div class="hero">
  <h1>MCP Anywhere</h1>
  <p>A unified gateway for Model Context Protocol servers</p>
  <p>Discover, configure, and access MCP tools from any GitHub repository through a single endpoint</p>
  <div class="hero-buttons">
    <a href="getting-started/" class="md-button">Get Started</a>
    <a href="https://github.com/locomotive-agency/mcp-anywhere" class="md-button md-button--secondary">View on GitHub</a>
  </div>
</div>

## What is MCP Anywhere?

MCP Anywhere acts as an all-in-one solution for accessing the MCP servers your team needs. It eliminates the complexity of managing multiple MCP server connections by providing a unified gateway with centralized configuration and security.

### Purpose

MCP Anywhere acts as an **all-in-one area for accessing the MCP servers that your team needs**. Instead of managing connections to multiple MCP servers separately, you get:

- **Centralized API Key Management**: Securely connect your API keys to one service, instead of multiple servers
- **Simplified Setup**: Removes the hassle of separately connecting every MCP server to Claude, OpenAI, your local Python tools, etc.
- **Selective Tool Access**: Limit what tools you want available from each MCP server
- **Unified Interface**: Single endpoint for all your MCP tools

<div class="feature-grid">
  <div class="feature-card">
    <h3>AI-Powered Discovery</h3>
    <p>Claude AI automatically analyzes GitHub repositories to determine setup requirements, runtime types, and configuration needs</p>
  </div>
  <div class="feature-card">
    <h3>Centralized Security</h3>
    <p>Store all API keys and credentials in one secure location with encrypted storage and proper access controls</p>
  </div>
  <div class="feature-card">
    <h3>Secret File Management</h3>
    <p>Upload and manage credential files (JSON, PEM, certificates) with AES-128 encryption and automatic container mounting</p>
  </div>
  <div class="feature-card">
    <h3>Granular Control</h3>
    <p>Enable or disable individual tools from each server. Each tool gets a unique prefix to prevent naming conflicts</p>
  </div>
  <div class="feature-card">
    <h3>Docker Isolation</h3>
    <p>Every MCP server runs in its own isolated Docker container for maximum security and reliability</p>
  </div>
  <div class="feature-card">
    <h3>Multi-Runtime Support</h3>
    <p>Supports Docker, Node.js (npx), and Python (uvx) runtime environments with automatic detection</p>
  </div>
  <div class="feature-card">
    <h3>Universal Integration</h3>
    <p>Connect to Claude Desktop, OpenAI, custom applications, or any MCP-compatible client through a single endpoint</p>
  </div>
</div>

## How It Works

### 1. Add a Server
Simply provide a GitHub URL to any MCP server repository:

```
https://github.com/modelcontextprotocol/servers
```

MCP Anywhere will:
1. Analyze the repository using Claude AI
2. Detect runtime requirements (Node.js, Python, Docker) 
3. Configure environment variables and API keys
4. Make tools available through a unified endpoint

### 2. Manage Tools
- View all available tools from your servers
- Enable/disable tools individually
- Each tool gets a unique prefix (e.g., `abc123_web_search`)
- Configure API keys centrally

### 3. Connect Your Client
Use the unified endpoint with any MCP client:

=== "Claude Desktop"
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

=== "Command Line"
    ```bash
    # Start the server
    mcp-anywhere serve http
    
    # Connect as client
    mcp-anywhere connect
    ```

## Quick Start

Ready to get started? Follow our simple setup guide:

<div class="hero-buttons" style="margin-top: 2rem;">
  <a href="getting-started/" class="md-button">Installation & Setup</a>
  <a href="deployment/" class="md-button">Deploy to Fly.io</a>
</div>

---

**Current Version**: 0.8.0 (Beta)  
**License**: See [LICENSE](https://github.com/locomotive-agency/mcp-anywhere/blob/main/LICENSE)