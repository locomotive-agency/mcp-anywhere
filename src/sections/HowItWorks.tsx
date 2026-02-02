import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { Download, Globe, CheckCircle } from 'lucide-react';

export const HowItWorks: React.FC = () => {
  return (
    <Section className="py-24 bg-surface">
      <Container>
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="w-auto mx-auto px-3 py-1 mb-4 text-xs font-semibold tracking-wider text-brand-600 uppercase bg-brand-50 rounded-full">
            Workflow
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-neutral-900">
            Connect in minutes, not days
          </h2>
          <p className="text-lg text-neutral-600">
            No complex VPNs or firewall configurations. MCP Anywhere just works.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          {/* Connector Line (Desktop) */}
          <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-neutral-200 -z-10"></div>

          {[
            {
              icon: <Download className="w-6 h-6 text-white" />,
              title: "1. Install CLI",
              desc: "Run a simple command to install the MCP Anywhere agent on your server or local machine.",
              color: "bg-blue-500"
            },
            {
              icon: <Globe className="w-6 h-6 text-white" />,
              title: "2. Expose Service",
              desc: "Select which MCP servers you want to expose securely to the internet.",
              color: "bg-purple-500"
            },
            {
              icon: <CheckCircle className="w-6 h-6 text-white" />,
              title: "3. Connect Client",
              desc: "Use the generated secure URL in Claude Desktop or any MCP-compatible client.",
              color: "bg-brand-500"
            }
          ].map((step, i) => (
            <div key={i} className="flex flex-col items-center text-center group">
              <div 
                className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-6 shadow-lg transform transition-transform group-hover:scale-110 ${step.color}`}
              >
                {step.icon}
              </div>
              <h3 className="text-xl font-bold mb-3 text-neutral-900">{step.title}</h3>
              <p className="text-neutral-600 leading-relaxed max-w-xs">{step.desc}</p>
            </div>
          ))}
        </div>
      </Container>
    </Section>
  );
};
