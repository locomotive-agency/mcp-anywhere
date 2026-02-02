import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';

export const SocialProof: React.FC = () => {
  return (
    <Section className="py-12 border-b border-neutral-100 bg-white">
      <Container>
        <p className="text-center text-sm font-semibold text-neutral-500 uppercase tracking-wider mb-8">
          Trusted by developers at innovative companies
        </p>
        <div className="flex flex-wrap justify-center gap-12 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
          {/* Logo Placeholders using Text for now, would be SVGs in production */}
          {['Acme Corp', 'GlobalTech', 'Nebula AI', 'DataFlow', 'StackSystems'].map((company, i) => (
            <div key={i} className="text-xl font-bold text-neutral-400 flex items-center gap-2">
              <div className="w-6 h-6 bg-neutral-200 rounded-md"></div>
              {company}
            </div>
          ))}
        </div>
      </Container>
    </Section>
  );
};
