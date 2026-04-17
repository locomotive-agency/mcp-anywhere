import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { Card } from '../components/Card';
import { Shield, Zap, Lock, Globe, Server, Terminal } from 'lucide-react';

export const Features: React.FC = () => {
  const features = [
    {
      icon: <Shield className="w-6 h-6 text-brand-600" />,
      title: "Self-Hosted & Private",
      desc: "Runs entirely on your own infrastructure. Your tool calls, API keys, and model context never leave your environment."
    },
    {
      icon: <Zap className="w-6 h-6 text-brand-600" />,
      title: "Auto-Configuration",
      desc: "Paste a GitHub MCP server URL; the setup flow reads the repo and generates the server entry for your gateway."
    },
    {
      icon: <Lock className="w-6 h-6 text-brand-600" />,
      title: "Access Control",
      desc: "Manage API keys and permissions for each server independently."
    },
    {
      icon: <Globe className="w-6 h-6 text-brand-600" />,
      title: "Work from Anywhere",
      desc: "Access your local dev tools from a coffee shop, or your production DB from home."
    },
    {
      icon: <Server className="w-6 h-6 text-brand-600" />,
      title: "Multi-Server Support",
      desc: "Expose multiple MCP servers through a single gateway connection."
    },
    {
      icon: <Terminal className="w-6 h-6 text-brand-600" />,
      title: "Developer First",
      desc: "Powerful CLI for management, logging, and debugging your connections."
    }
  ];

  return (
    <Section className="py-24 bg-white" id="features">
      <Container>
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-2 text-neutral-900">
            One gateway, many MCP servers
          </h2>
          <p className="text-lg text-neutral-600">
            For anyone wiring local tools, internal APIs, and data into MCP without shipping context to a vendor.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, i) => (
            <Card key={i} className="h-full border border-neutral-100 shadow-sm hover:shadow-xl transition-shadow bg-neutral-50/50">
              <div className="w-12 h-12 rounded-lg bg-brand-100 flex items-center justify-center mb-6">
                {feature.icon}
              </div>
              <h3 className="text-xl font-bold mb-3 text-neutral-900">{feature.title}</h3>
              <p className="text-neutral-600">{feature.desc}</p>
            </Card>
          ))}
        </div>
      </Container>
    </Section>
  );
};
