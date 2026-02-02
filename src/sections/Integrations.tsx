import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';

export const Integrations: React.FC = () => {
  return (
    <Section className="py-24 bg-white border-t border-neutral-100">
      <Container>
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-2 text-neutral-900">
            Works with your favorite tools
          </h2>
          <p className="text-lg text-neutral-600">
            MCP Anywhere is designed to be compatible with the entire Model Context Protocol ecosystem.
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            "Claude Desktop",
            "Cursor",
            "Zed",
            "VS Code",
            "Linear",
            "GitHub",
            "Postgres",
            "Notion"
          ].map((tool, i) => (
            <div
              key={i}
              className="flex items-center justify-center p-8 bg-neutral-50 rounded-xl border border-neutral-100 hover:border-brand-200 hover:shadow-lg transition-all"
            >
              <span className="font-semibold text-neutral-700">{tool}</span>
            </div>
          ))}
        </div>
      </Container>
    </Section>
  );
};
