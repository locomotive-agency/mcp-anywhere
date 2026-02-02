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
              Start building in seconds
            </h2>
            <p className="text-white text-lg mb-8 text-white">
              Install the CLI and expose your first local server to the world (securely) with a single command.
            </p>
            
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-brand-500 text-neutral-900 flex items-center justify-center font-bold">1</div>
                <div>
                  <h4 className="font-bold mb-1 text-neutral-400">Install the CLI</h4>
                  <p className="text-neutral-400 text-sm">Available via npm for Mac, Linux, and Windows.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-neutral-700 text-white flex items-center justify-center font-bold">2</div>
                <div>
                  <h4 className="font-bold mb-1 text-neutral-400">Connect a Server</h4>
                  <p className="text-neutral-400 text-sm">Point to your local MCP server implementation.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-neutral-700 text-white flex items-center justify-center font-bold">3</div>
                <div>
                  <h4 className="font-bold mb-1 text-neutral-400">Use Anywhere</h4>
                  <p className="text-neutral-400 text-sm">Paste the SSE URL into your client configuration.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1 w-full max-w-xl">
            <CodeBlock 
              language="bash"
              code={`# Install globally
npm install -g mcp-anywhere

# Login to your account
mcp-anywhere login

# Expose a local server (e.g. running on port 3000)
mcp-anywhere connect http://localhost:3000 --name "My Local DB"

# > Connection Established! 
# > Public URL: https://mcp.run/s/xyz-123-abc`}
            />
          </div>
        </div>
      </Container>
    </Section>
  );
};
