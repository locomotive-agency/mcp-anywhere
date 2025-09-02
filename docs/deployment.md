# Deploy to Fly.io

Deploy MCP Anywhere to Fly.io for a production-ready, cloud-hosted instance with automatic SSL certificates and global availability.

## Why Fly.io?

- Global edge deployment
- Automatic SSL certificates  
- Built-in persistent storage
- Simple deployment process
- Free tier available

## Prerequisites

- Fly.io account ([sign up free](https://fly.io))
- MCP Anywhere repository cloned locally
- Docker running locally

## Installation

### 1. Install Fly CLI

=== "macOS/Linux"
    ```bash
    curl -L https://fly.io/install.sh | sh
    ```

=== "Windows"
    ```powershell
    iwr https://fly.io/install.ps1 -useb | iex
    ```

### 2. Authenticate

```bash
fly auth login
```

## Deployment

### 1. Initialize Your App

```bash
cd mcp-anywhere
fly launch
```

When prompted:
- Choose an app name (e.g., `my-mcp-anywhere`)
- Select a region close to you
- **Don't** create PostgreSQL or Redis databases
- **Yes** to create the app

### 2. Configure Environment Variables

Set required secrets:

```bash
# Generate secure keys
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Set secrets
fly secrets set SECRET_KEY="$SECRET_KEY"
fly secrets set ANTHROPIC_API_KEY="your-anthropic-api-key-here"

# Optional: for private GitHub repositories
fly secrets set GITHUB_TOKEN="your-github-token"
```

### 3. Create Persistent Storage

MCP Anywhere needs persistent storage for data:

```bash
# Create a 10GB volume 
fly volumes create mcp_data --size 10
```

### 4. Deploy

```bash
fly deploy
```

The deployment will:
1. Build the Docker image
2. Push to Fly's registry
3. Deploy to your selected region
4. Start the application

### 5. Verify Deployment

```bash
# Check status
fly status

# View logs
fly logs

# Open in browser
fly open
```

Your MCP Anywhere instance is now live at `https://your-app-name.fly.dev`

## Custom Domain Setup

### 1. Add Your Domain

```bash
fly certs add mcpanywhere.com
```

### 2. Configure DNS

Add these DNS records to your domain:

| Type | Name | Value |
|------|------|-------|
| A | @ | Fly IPv4 (from `fly certs show mcpanywhere.com`) |
| AAAA | @ | Fly IPv6 (from `fly certs show mcpanywhere.com`) |

### 3. Verify SSL

Wait 5-30 minutes for DNS propagation, then:

```bash
fly certs show mcpanywhere.com
```

Your site will be available at `https://mcpanywhere.com`

## Scaling

### Add More Regions

```bash
# Add regions for global availability
fly regions add lhr ams sin
```

### Scale Resources

```bash
# Scale to higher CPU/memory
fly scale vm shared-cpu-2x --memory 1024

# Scale to multiple instances
fly scale count 2
```

## Monitoring

### View Logs

```bash
# Live logs
fly logs -f

# Recent logs
fly logs -n 100
```

### Metrics

```bash
# Open metrics dashboard
fly dashboard metrics
```

## Updating

To deploy updates:

```bash
# Pull latest changes
git pull origin main

# Deploy updates
fly deploy
```

## Backup & Maintenance

### Backup Data

```bash
# SSH into instance
fly ssh console

# Create backup
tar -czf /tmp/backup.tar.gz /data

# Download backup (from local machine)
fly ssh sftp get /tmp/backup.tar.gz ./backup.tar.gz
```

### Reset Data

If you need to reset your instance:

```bash
# SSH into instance
fly ssh console

# Run reset command
/app/venv/bin/python -m mcp_anywhere reset --confirm
```

## Cost Optimization

### Free Tier
Fly.io free tier includes:
- 3 shared-cpu-1x VMs
- 3GB persistent storage
- 160GB outbound transfer

### Tips
- Use `fly scale count 0` to stop during development
- Monitor usage: `fly billing`
- Clean up unused volumes: `fly volumes list`

## Troubleshooting

### App Won't Start

```bash
# Check logs for errors
fly logs -n 200

# Common issues:
# - Missing environment variables
# - Docker build failures
# - Port binding issues
```

### Volume Issues

```bash
# Check volume status
fly volumes list

# If needed, create new volume
fly volumes create mcp_data_new --size 10
fly deploy
```

### SSL Certificate Issues

```bash
# Check certificate
fly certs check mcpanywhere.com

# Re-issue if needed
fly certs remove mcpanywhere.com
fly certs add mcpanywhere.com
```

## Security Best Practices

1. **Use strong secrets**: Generate cryptographically secure keys
2. **Rotate secrets regularly**: Update API keys and passwords periodically
3. **Monitor access logs**: Review application logs for suspicious activity
4. **Keep updated**: Deploy security updates promptly

---

Your MCP Anywhere instance is now running in production! 🎉

Users can now access your instance at your custom domain and add MCP servers through the web interface. The system will handle Docker container management, API key storage, and tool discovery automatically.