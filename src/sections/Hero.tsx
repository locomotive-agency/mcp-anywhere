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
              Open source & self-hosted
            </div>
            
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 tracking-tight text-neutral-900 animate-fade-in delay-100">
              The Unified Gateway for <br className="hidden lg:block"/>
              <span className="text-gradient">Model Context Protocol</span>
            </h1>
            
            <p className="text-xl text-neutral-600 mb-8 max-w-2xl mx-auto lg:mx-0 animate-fade-in delay-200">
              Route MCP-compatible clients to your servers through one gateway you run yourself. 
              Repo-driven configuration, Docker-isolated MCP processes, keys and traffic on your infrastructure.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start animate-fade-in delay-300">
              <Button size="lg" href="#get-started">
                Quick start <ArrowRight size={18} />
              </Button>
              <Button size="lg" variant="outline" href="https://github.com/locomotive-agency/mcp-anywhere" target="_blank">
                <Github size={18} /> Star on GitHub
              </Button>
            </div>

            <div className="mt-10 flex items-center justify-center lg:justify-start gap-8 text-sm text-neutral-500 animate-fade-in delay-300">
              <div className="flex items-center gap-2">
                <Zap size={16} className="text-brand-500" /> CLI-first
              </div>
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-brand-500" /> Secure by Default
              </div>
              <div className="flex items-center gap-2">
                <Globe size={16} className="text-brand-500" /> Open Source
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
                <div className="flex items-center justify-between gap-3 py-2">
                  {/* Left: Multiple MCP Servers */}
                  <div className="flex flex-col gap-2 flex-1">
                    {['Ahrefs MCP', 'GitHub MCP', 'Python MCP'].map((name, i) => (
                      <div key={i} className="bg-neutral-50 px-3 py-2 rounded-lg border border-neutral-200 text-center">
                        <div className="font-semibold text-xs text-neutral-700">{name}</div>
                      </div>
                    ))}
                  </div>

                  {/* Arrows → Gateway */}
                  <div className="flex flex-col items-center justify-center gap-1 flex-shrink-0">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-6 h-0.5 bg-brand-300 relative overflow-hidden rounded-full">
                        <div className="absolute top-0 left-0 h-full w-2 bg-brand-500 animate-shimmer"></div>
                      </div>
                    ))}
                  </div>

                  {/* Center: MCP Anywhere Gateway */}
                  <div className="bg-brand-50 p-3 rounded-xl border border-brand-300 text-center flex-shrink-0">
                    <div className="w-8 h-8 mx-auto bg-brand-500 text-white rounded-lg flex items-center justify-center mb-1">
                      <Zap size={16} />
                    </div>
                    <div className="font-bold text-xs text-brand-700">MCP Anywhere</div>
                    <div className="text-xs text-brand-500">Gateway</div>
                  </div>

                  {/* Arrow → Claude Desktop */}
                  <div className="flex flex-col items-center justify-center flex-shrink-0">
                    <div className="w-6 h-0.5 bg-brand-300 relative overflow-hidden rounded-full">
                      <div className="absolute top-0 left-0 h-full w-2 bg-brand-500 animate-shimmer"></div>
                    </div>
                    <div className="text-xs text-brand-500 font-mono mt-1">1×</div>
                  </div>

                  {/* Right: Claude Desktop */}
                  <div className="bg-neutral-50 p-3 rounded-xl border border-neutral-200 text-center flex-1">
                    <div className="w-8 h-8 mx-auto bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-1">
                      <Shield size={16} />
                    </div>
                    <div className="font-semibold text-xs">Claude Desktop</div>
                    <div className="text-xs text-neutral-400">1 connection</div>
                  </div>
                </div>

                {/* Code Snippet */}
                <div className="bg-neutral-900 rounded-lg p-4 font-mono text-xs text-neutral-300">
                  <div className="flex gap-2 mb-2">
                    <span className="text-green-400">$</span>
                    <span>mcp-anywhere serve http</span>
                  </div>
                  <div className="text-neutral-500">Starting MCP Anywhere gateway...</div>
                  <div className="text-green-400">✓ 3 MCP servers connected</div>
                  <div className="text-green-400">✓ Listening on http://localhost:8000</div>
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
