import React, { useState } from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { ChevronDown, ChevronUp } from 'lucide-react';

const FAQItem: React.FC<{ question: string; answer: string }> = ({ question, answer }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border-b border-neutral-200">
      <button 
        className="w-full py-6 flex items-center justify-between text-left focus:outline-none group bg-transparent border-none cursor-pointer"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="font-semibold text-lg text-neutral-900 group-hover:text-brand-600 transition-colors">{question}</span>
        {isOpen ? (
          <ChevronUp className="text-brand-500 flex-shrink-0 ml-4" /> 
        ) : (
          <ChevronDown className="text-neutral-400 group-hover:text-brand-500 transition-colors flex-shrink-0 ml-4" />
        )}
      </button>
      <div 
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isOpen ? 'max-h-96 opacity-100 mb-6' : 'max-h-0 opacity-0'
        }`}
      >
        <p className="text-neutral-600 leading-relaxed">{answer}</p>
      </div>
    </div>
  );
};

export const FAQ: React.FC = () => {
  return (
    <Section className="py-24 bg-white" id="faq">
      <Container>
        <div className="text-center max-w-3xl mx-auto mb-16">
        <h2 className="text-3xl md:text-4xl font-bold mb-2 text-neutral-900">
            Frequently Asked Questions
          </h2>
          <p className="text-lg text-neutral-600">
            Got questions about MCP Anywhere? We've got answers.
          </p>
        </div>

        <div className="max-w-2xl mx-auto">
          <FAQItem
            question="Is MCP Anywhere open source?"
            answer="Yes! MCP Anywhere is fully open source and self-hosted. You run it on your own machine or server — there is no managed cloud version."
          />
          <FAQItem
            question="Is it secure?"
            answer="Yes. Because MCP Anywhere runs entirely on your own infrastructure, your tool calls, API keys, and model context never leave your environment. Each MCP server runs in an isolated Docker container, and credentials are encrypted at rest."
          />
          <FAQItem
            question="Does it work with Claude Desktop?"
            answer="Yes, MCP Anywhere is fully compatible with Claude Desktop and any other client that supports the Model Context Protocol."
          />
          <FAQItem
            question="How much does it cost?"
            answer="Nothing. MCP Anywhere is completely free and open source. There are no tiers, no usage limits, and no subscription — just clone the repo and run it."
          />
        </div>
      </Container>
    </Section>
  );
};
