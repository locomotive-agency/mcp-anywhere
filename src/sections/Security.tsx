import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { Button } from '../components/Button';
import { ShieldCheck, Check } from 'lucide-react';

export const Security: React.FC = () => {
  return (
    <Section className="py-24 bg-surface relative overflow-hidden">
      <Container>
        <div className="flex flex-col lg:flex-row items-center gap-16">
          <div className="flex-1">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-100 text-green-800 text-xs font-bold uppercase tracking-wider mb-6">
              <ShieldCheck size={14} />
              Enterprise Security
            </div>
            <h2 className="text-3xl md:text-4xl font-bold mb-6 text-neutral-900">
              Your data never leaves your infrastructure
            </h2>
            <p className="text-lg text-neutral-600 mb-8">
              MCP Anywhere creates a secure tunnel for control signals, but sensitive payloads remain encrypted. We prioritize security so you can focus on building.
            </p>

            <ul className="space-y-4 mb-8">
              {[
                "TLS 1.3 encryption for all connections",
                "No persistence of message payloads",
                "Granular API key management",
                "SOC 2 Type II compliant (Coming Soon)"
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
                    <span className="text-neutral-400">[10:42:01]</span> Handshake initiated...
                  </div>
                  <div className="text-green-600">
                    <span className="text-neutral-400">[10:42:02]</span> Verifying signature... OK
                  </div>
                  <div className="text-green-600">
                    <span className="text-neutral-400">[10:42:02]</span> Establishing E2EE tunnel...
                  </div>
                  <div className="p-3 bg-neutral-50 rounded text-neutral-600 border border-neutral-200">
                    Tunnel ID: <span className="text-purple-600">tun_8f92a3c1</span><br/>
                    Encryption: <span className="text-blue-600">AES-256-GCM</span>
                  </div>
                  <div className="text-green-600">
                    <span className="text-neutral-400">[10:42:03]</span> Connected securely.
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
