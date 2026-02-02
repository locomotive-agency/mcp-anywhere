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
            answer="Yes! The core client and server components are open source. We also offer a managed hosted version for teams who don't want to manage their own infrastructure." 
          />
          <FAQItem 
            question="Is it secure to expose my local database?" 
            answer="Absolutely. We use end-to-end encryption. The traffic is tunneled through our secure gateway, but the payload is encrypted with keys that only you possess. We cannot see your data." 
          />
          <FAQItem 
            question="Does it work with Claude Desktop?" 
            answer="Yes, MCP Anywhere is fully compatible with Claude Desktop and any other client that supports the Model Context Protocol (SSE transport)." 
          />
          <FAQItem 
            question="Is there a free tier?" 
            answer="Yes, we offer a generous free tier for individual developers. You can upgrade to a Pro plan for higher bandwidth limits and team management features." 
          />
        </div>
      </Container>
    </Section>
  );
};
