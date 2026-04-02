import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { CodeBlock } from '../components/CodeBlock';

export const QuickStart: React.FC = () => {
  return (
    <Section className="py-24 bg-neutral-900 text-white overflow-hidden relative">
      <div className="absolute top-0 right-0 w-1/3 h-full bg-brand-900 opacity-20 filter blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-1/3 h-full bg-blue-900 opacity-20 filter blur-3xl pointer-events-none"></div>

      <Container className="relative z-10">
        <div className="flex flex-col lg:flex-row gap-12 items-center">
          <div className="flex-1">
            <h2 className="text-3xl md:text-4xl font-bold mb-6 text-white">
              Clone, run, connect
            </h2>
            <p className="text-white text-lg mb-8 text-white">
              Pull the project from GitHub, start the bundled web UI and gateway, then add one Claude Desktop entry for every tool behind it.
            </p>

            <div className="space-y-6">
              <div className="flex gap-4 mb-4">
                <div className="w-8 h-8 rounded-full bg-brand-500 text-neutral-900 flex items-center justify-center font-bold">1</div>
                <div>
                  <h4 className="font-bold mb-1 text-neutral-400">Clone & Install</h4>
                  <p className="text-neutral-400 text-sm">Python package installed with uv or pip. Requires Python 3.11+ and Docker Desktop.</p>
                </div>
              </div>
              <div className="flex gap-4 mb-4">
                <div className="w-8 h-8 rounded-full bg-neutral-700 text-white flex items-center justify-center font-bold">2</div>
                <div>
                  <h4 className="font-bold mb-1 text-neutral-400">Add MCP Servers</h4>
                  <p className="text-neutral-400 text-sm">In the web UI, paste a GitHub MCP server repo URL; the project’s helpers generate the config.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-neutral-700 text-white flex items-center justify-center font-bold">3</div>
                <div>
                  <h4 className="font-bold mb-1 text-neutral-400">Connect Claude Desktop</h4>
                  <p className="text-neutral-400 text-sm">Add one entry to claude_desktop_config.json — all your MCP tools become available instantly.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1 w-full max-w-xl">
            <CodeBlock
              language="bash"
              code={`# Clone and install
git clone https://github.com/locomotive-agency/mcp-anywhere.git
cd mcp-anywhere && uv sync

# Start the gateway (includes web UI)
mcp-anywhere serve http

# > Starting MCP Anywhere...
# > Web UI available at http://localhost:8000

# Add MCP servers via the web UI, then connect Claude Desktop
mcp-anywhere connect

# > Connected to MCP Anywhere
# > 3 MCP servers · 12 tools available`}
            />
          </div>
        </div>
      </Container>
    </Section>
  );
};
