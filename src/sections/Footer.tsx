import React from 'react';
import { Container } from '../components/Container';
import { Github, Twitter, Heart } from 'lucide-react';
import logo from '../assets/images/logo.png';

export const Footer: React.FC = () => {
  return (
    <footer className="pt-16 pb-8 border-t border-neutral-200 bg-neutral-50 text-neutral-600">
      <Container>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
          {/* Logo & Description */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <img 
                src={logo} 
                alt="MCP Anywhere" 
                className="h-8 w-auto"
              />
              <span className="font-bold text-lg text-neutral-900">
                MCP Anywhere
              </span>
            </div>
            <p className="text-sm leading-relaxed max-w-xs">
              A unified gateway for Model Context Protocol. 
              Secure, scalable, and open source.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-bold text-sm text-neutral-900 uppercase tracking-wider mb-4">
              Quick Links
            </h4>
            <div className="flex flex-col gap-3">
              {[
                { label: 'Features', href: '#features' },
                { label: 'How it Works', href: '#how-it-works' },
                { label: 'Security', href: '#security' },
                { label: 'FAQ', href: '#faq' }
              ].map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="text-sm hover:text-brand-600 transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-bold text-sm text-neutral-900 uppercase tracking-wider mb-4">
              Resources
            </h4>
            <div className="flex flex-col gap-3">
              {[
                { label: 'GitHub', href: 'https://github.com/locomotive-agency/mcp-anywhere' },
                { label: 'Documentation', href: '#' },
                { label: 'MCP Spec', href: 'https://modelcontextprotocol.io' },
                { label: 'Community', href: '#' }
              ].map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target={link.href.startsWith('http') ? '_blank' : undefined}
                  rel={link.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                  className="text-sm hover:text-brand-600 transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-neutral-200 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-sm text-neutral-500 flex items-center gap-2 flex-wrap justify-center md:justify-start mt-8">
            © {new Date().getFullYear()} MCP Anywhere. 
            <span className="inline-flex items-center gap-1">
              Built with <Heart size={14} className="text-red-500 fill-current" /> by Locomotive Agency
            </span>
          </p>
          
          <div className="flex items-center gap-4 mt-8">
            <a 
              href="https://github.com/locomotive-agency/mcp-anywhere"
              target="_blank"
              rel="noopener noreferrer"
              className="w-8 h-8 rounded-full border border-neutral-200 flex items-center justify-center hover:border-brand-500 hover:text-brand-600 hover:bg-brand-50 transition-all"
              aria-label="GitHub"
            >
              <Github size={20} />
            </a>
          </div>
        </div>
      </Container>
    </footer>
  );
};
