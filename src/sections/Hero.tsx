import React from 'react';
import { Container } from '../components/Container';
import { Button } from '../components/Button';
import { Section } from '../components/Section';
import { ArrowRight, Github, Zap, Shield, Globe } from 'lucide-react';

export const Hero: React.FC = () => {
  return (
    <Section className="relative overflow-hidden pt-32 pb-20 lg:pt-48 lg:pb-32">
      {/* Background Decor */}
      <div className="absolute top-0 right-0 -z-10 w-1/2 h-full opacity-10 pointer-events-none overflow-hidden">
        <div 
          style={{
            position: 'absolute',
            top: '-20%',
            right: '-10%',
            width: '800px',
            height: '800px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, var(--brand-primary) 0%, transparent 70%)',
            filter: 'blur(80px)'
          }} 
        />
      </div>

      <Container>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          <div className="text-center lg:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 border border-brand-200 text-brand-700 text-sm font-semibold mb-6 animate-fade-in">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
              </span>
              Now Available for Everyone
            </div>
            
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 tracking-tight text-neutral-900 animate-fade-in delay-100">
              The Unified Gateway for <br className="hidden lg:block"/>
              <span className="text-gradient">Model Context Protocol</span>
            </h1>
            
            <p className="text-xl text-neutral-600 mb-8 max-w-2xl mx-auto lg:mx-0 animate-fade-in delay-200">
              Connect any AI client to any MCP server instantly. 
              Enterprise-grade security, centralized management, and zero friction.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start animate-fade-in delay-300">
              <Button size="lg" href="#get-started">
                Get Started Free <ArrowRight size={18} />
              </Button>
              <Button size="lg" variant="outline" href="https://github.com/locomotive-agency/mcp-anywhere" target="_blank">
                <Github size={18} /> Star on GitHub
              </Button>
            </div>

            <div className="mt-10 flex items-center justify-center lg:justify-start gap-8 text-sm text-neutral-500 animate-fade-in delay-300">
              <div className="flex items-center gap-2">
                <Zap size={16} className="text-brand-500" /> Instant Setup
              </div>
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-brand-500" /> Secure by Default
              </div>
              <div className="flex items-center gap-2">
                <Globe size={16} className="text-brand-500" /> Global Edge
              </div>
            </div>
          </div>

          <div className="relative animate-fade-in-up delay-300">
            {/* Abstract representation of Client <-> Server connection */}
            <div className="relative rounded-3xl bg-white border border-neutral-200 shadow-2xl p-6 sm:p-8 overflow-hidden transform rotate-1 hover:rotate-0 transition-transform duration-500">
              <div className="absolute top-0 left-0 w-full h-2 bg-brand-500"></div>
              
              <div className="flex flex-col gap-6">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-neutral-100 pb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-400"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                    <div className="w-3 h-3 rounded-full bg-green-400"></div>
                  </div>
                  <div className="text-xs font-mono text-neutral-400">mcp-anywhere.config</div>
                </div>

                {/* Connection Visual */}
                <div className="flex items-center justify-between gap-4 py-4">
                  <div className="bg-neutral-50 p-4 rounded-xl border border-neutral-200 text-center flex-1">
                    <div className="w-10 h-10 mx-auto bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-2">
                      <Zap size={20} />
                    </div>
                    <div className="font-semibold text-sm">Claude Desktop</div>
                    <div className="text-xs text-neutral-400">Client</div>
                  </div>

                  <div className="flex-1 flex flex-col items-center">
                    <div className="text-xs text-brand-600 font-mono mb-1 bg-brand-50 px-2 py-0.5 rounded-full">Secure Tunnel</div>
                    <div className="w-full h-0.5 bg-brand-200 relative">
                      <div className="absolute top-1/2 left-0 w-2 h-2 bg-brand-500 rounded-full -translate-y-1/2 animate-shimmer"></div>
                    </div>
                  </div>

                  <div className="bg-neutral-50 p-4 rounded-xl border border-neutral-200 text-center flex-1">
                    <div className="w-10 h-10 mx-auto bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-2">
                      <Shield size={20} />
                    </div>
                    <div className="font-semibold text-sm">Production DB</div>
                    <div className="text-xs text-neutral-400">Server</div>
                  </div>
                </div>

                {/* Code Snippet */}
                <div className="bg-neutral-900 rounded-lg p-4 font-mono text-xs text-neutral-300">
                  <div className="flex gap-2 mb-2">
                    <span className="text-green-400">$</span>
                    <span>npx mcp-anywhere connect</span>
                  </div>
                  <div className="text-neutral-500">Connecting to secure gateway...</div>
                  <div className="text-green-400">✓ Tunnel established: wss://api.mcp.run/v1/tunnel</div>
                </div>
              </div>
            </div>
            
            {/* Decor Elements */}
            <div className="absolute -bottom-6 -left-6 w-24 h-24 bg-brand-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
            <div className="absolute -top-6 -right-6 w-24 h-24 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
          </div>
        </div>
      </Container>
    </Section>
  );
};
