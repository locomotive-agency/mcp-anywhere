import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { Button } from '../components/Button';
import { ArrowRight } from 'lucide-react';

export const FinalCTA: React.FC = () => {
  return (
    <Section className="py-32 bg-surface relative overflow-hidden text-center" id="get-started">
      {/* Background Glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-200 rounded-full filter blur-[100px] opacity-30 pointer-events-none"
      />

      <Container className="relative z-10">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-2 text-neutral-900">
            Free, open source, and self-hosted.
          </h2>
          <p className="text-lg text-neutral-600">
            Clone the repo and have all your MCP servers running in minutes. No account, no credit card, no limits.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row justify-center gap-4 w-full max-w-md mx-auto">
          <Button size="lg" className="shadow-xl shadow-brand-200" href="https://github.com/locomotive-agency/mcp-anywhere" target="_blank">
            View on GitHub <ArrowRight size={18} />
          </Button>
          <Button size="lg" variant="outline" className="bg-white hover:bg-neutral-50" href="/getting-started">
            Read the Docs
          </Button>
        </div>
      </Container>
    </Section>
  );
};
