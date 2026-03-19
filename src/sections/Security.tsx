import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { ShieldCheck, Check } from 'lucide-react';

export const Security: React.FC = () => {
  return (
    <Section className="py-24 bg-surface relative overflow-hidden">
      <Container>
        <div className="flex flex-col lg:flex-row items-center gap-16">
          <div className="flex-1">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-100 text-black text-xs font-bold uppercase tracking-wider mb-6 border border-brand-500">
              <ShieldCheck size={14} />
              Enterprise Security
            </div>
            <h2 className="text-3xl md:text-4xl font-bold mb-6 text-neutral-900">
              Your data never leaves your infrastructure
            </h2>
            <p className="text-lg text-neutral-600 mb-8">
              MCP Anywhere runs entirely on your own infrastructure. Your tool calls, credentials, and model context never touch an external service.
            </p>

            <ul className="space-y-4 mb-8">
              {[
                "Docker container isolation for each MCP server",
                "Credentials encrypted at rest (AES-128)",
                "Granular API key management per server",
                "Google OAuth with domain-based access control"
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-3 text-neutral-700">
                  <div className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 flex-shrink-0">
                    <Check size={14} strokeWidth={3} />
                  </div>
                  {item}
                </li>
              ))}
            </ul>

            {/* <Button variant="outline">Read Security Whitepaper</Button> */}
          </div>

          <div className="flex-1 w-full max-w-lg">
            <div className="bg-white rounded-2xl shadow-2xl p-8 border border-neutral-100 relative">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <ShieldCheck size={120} />
              </div>
              
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-neutral-100">
                  <div className="font-mono text-sm text-neutral-500">connection_log.txt</div>
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-red-400"></div>
                    <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
                    <div className="w-2 h-2 rounded-full bg-green-400"></div>
                  </div>
                </div>
                
                <div className="space-y-3 font-mono text-xs">
                  <div className="text-green-600">
                    <span className="text-neutral-400">[10:42:01]</span> Starting MCP Anywhere...
                  </div>
                  <div className="text-green-600">
                    <span className="text-neutral-400">[10:42:01]</span> Secrets loaded (AES-128 encrypted)
                  </div>
                  <div className="text-green-600">
                    <span className="text-neutral-400">[10:42:02]</span> Container: ahrefs-mcp → isolated ✓
                  </div>
                  <div className="p-3 bg-neutral-50 rounded text-neutral-600 border border-neutral-200">
                    Auth: <span className="text-purple-600">Google OAuth enabled</span><br/>
                    Access: <span className="text-blue-600">@yourcompany.com only</span>
                  </div>
                  <div className="text-green-600">
                    <span className="text-neutral-400">[10:42:03]</span> Ready at http://localhost:8000
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Container>
    </Section>
  );
};
