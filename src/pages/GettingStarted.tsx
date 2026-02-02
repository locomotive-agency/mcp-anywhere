import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { CodeBlock } from '../components/CodeBlock';

export const GettingStarted: React.FC = () => {
  return (
    <div className="pt-20">
      <Section className="bg-neutral-50 border-b border-neutral-200 py-12">
        <Container>
          <h1 className="text-4xl font-bold text-neutral-900 mb-4">Getting Started</h1>
          <p className="text-xl text-neutral-600">
            Get up and running with MCP Anywhere in a few simple steps.
          </p>
        </Container>
      </Section>

      <Container className="py-12">
        <div className="prose max-w-4xl mx-auto space-y-12">
          
          <section>
            <h2 className="text-2xl font-bold text-neutral-900 mb-6">Prerequisites</h2>
            <ul className="list-disc pl-6 space-y-2 text-neutral-600">
              <li>Python 3.11 or higher</li>
              <li>Docker Desktop (for running MCP servers)</li>
              <li>An Anthropic API key for Claude AI (for auto-configuration)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-neutral-900 mb-6">Installation</h2>
            
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">1. Clone and Install</h3>
                <CodeBlock 
                  code={`# Clone repository
git clone https://github.com/locomotive-agency/mcp-anywhere.git
cd mcp-anywhere

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .`} 
                />
              </div>

              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">2. Configure Environment</h3>
                <CodeBlock code={`cp env.example .env`} />
                <p className="mt-3 text-neutral-600 mb-3">Edit <code>.env</code> with your configuration:</p>
                <CodeBlock 
                  code={`# Required
SECRET_KEY=your-secure-random-key-here
JWT_SECRET_KEY=your-secure-random-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional
WEB_PORT=8000
LOG_LEVEL=INFO`} 
                />
              </div>

              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">3. Start MCP Anywhere</h3>
                <CodeBlock 
                  code={`# Start HTTP server (includes web UI)
uv run mcp-anywhere serve http

# Or start STDIO server (for local Claude Desktop)
uv run mcp-anywhere serve stdio`} 
                />
                <p className="mt-3 text-neutral-600">
                  The web interface will be available at <a href="http://localhost:8000" className="text-brand-600 hover:underline">http://localhost:8000</a>
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-neutral-900 mb-6">Connecting Claude Desktop</h2>
            
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">1. Configure Claude Desktop</h3>
                <p className="text-neutral-600 mb-3">
                  Edit your config file at <code>~/Library/Application Support/Claude/claude_desktop_config.json</code> (macOS) 
                  or <code>%APPDATA%\Claude\claude_desktop_config.json</code> (Windows):
                </p>
                <CodeBlock 
                  language="json"
                  code={`{
  "mcpServers": {
    "mcp-anywhere": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/path/to/mcp-anywhere",
        "mcp-anywhere",
        "connect"
      ]
    }
  }
}`} 
                />
              </div>

              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">2. Restart Claude Desktop</h3>
                <p className="text-neutral-600">
                  Quit Claude Desktop completely and restart it. Ask <em>"What MCP tools do I have available?"</em> to verify the connection.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-neutral-900 mb-6">Popular MCP Servers to Try</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <a 
                href="https://github.com/modelcontextprotocol/servers"
                target="_blank"
                rel="noopener noreferrer" 
                className="block p-6 border border-neutral-200 rounded-xl hover:border-brand-500 transition-colors"
              >
                <h3 className="font-bold text-lg mb-2 text-neutral-900">Official MCP Servers</h3>
                <p className="text-neutral-600">Collection of official MCP tools and implementations.</p>
              </a>
              <a 
                href="https://github.com/yzfly/mcp-python-interpreter" 
                target="_blank"
                rel="noopener noreferrer"
                className="block p-6 border border-neutral-200 rounded-xl hover:border-brand-500 transition-colors"
              >
                <h3 className="font-bold text-lg mb-2 text-neutral-900">Python Interpreter</h3>
                <p className="text-neutral-600">Execute Python code safely within your context.</p>
              </a>
            </div>
          </section>

        </div>
      </Container>
    </div>
  );
};
