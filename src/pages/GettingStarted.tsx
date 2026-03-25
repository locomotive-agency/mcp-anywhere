import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Container } from '../components/Container';
import { CodeBlock } from '../components/CodeBlock';
import { ChevronRight, Info, Terminal, Server, Shield, Wrench, BookOpen, AlertCircle } from 'lucide-react';

/* ─── Small reusable doc primitives ─── */

const Breadcrumb = () => (
  <nav className="mb-8 flex items-center gap-1.5 text-sm text-neutral-500">
    <Link to="/" className="hover:text-brand-600 transition-colors">Docs</Link>
    <ChevronRight size={14} className="text-neutral-300" />
    <span className="text-neutral-900 font-medium">Getting Started</span>
  </nav>
);

const SectionHeading = ({ id, icon: Icon, children }: { id: string; icon: React.ElementType; children: React.ReactNode }) => (
  <h2 id={id} className="mb-10 flex scroll-mt-40 items-center gap-3 text-2xl font-bold text-neutral-900">
    <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-100 text-brand-700 flex-shrink-0">
      <Icon size={16} />
    </span>
    {children}
  </h2>
);

const Callout = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={`my-6 flex gap-3 rounded-xl border border-brand-200 bg-brand-50 p-4 ${className}`}>
    <Info size={16} className="text-brand-600 flex-shrink-0 mt-0.5" />
    <p className="text-sm text-brand-900 leading-relaxed">{children}</p>
  </div>
);

const InlineCode = ({ children }: { children: React.ReactNode }) => (
  <code className="font-mono text-sm bg-neutral-100 text-neutral-800 px-1.5 py-0.5 rounded border border-neutral-200">
    {children}
  </code>
);

const DocSection = ({ first = false, children }: { first?: boolean; children: React.ReactNode }) => (
  <section className={first ? '' : 'border-t border-neutral-100 pt-16'}>
    {children}
  </section>
);

const Subheading = ({ children }: { children: React.ReactNode }) => (
  <h3 className="mt-8 mb-3 text-lg font-semibold text-neutral-900">
    {children}
  </h3>
);

const CodeLabel = ({ children }: { children: React.ReactNode }) => (
  <p className="mt-6 mb-4 text-base leading-relaxed text-neutral-600">
    {children}
  </p>
);

const StepItem = ({ number, title, last = false, children, className }: {
  number: number; title: string; last?: boolean; children: React.ReactNode; className?: string;
}) => (
  <div className={`relative flex gap-4 ${className} mb-12`}>
    <div className="flex flex-col items-center flex-shrink-0">
      <div className="w-8 h-8 rounded-full bg-brand-500 text-neutral-900 font-bold text-sm flex items-center justify-center z-10 shadow-sm flex-shrink-0">
        {number}
      </div>
      {!last && <div className="w-px flex-1 bg-neutral-200 mt-2"></div>}
    </div>
    <div className={`flex-1 min-w-0 ${last ? 'pb-0' : 'pb-16'}`}>
      <h3 className="mt-1 text-xl font-semibold text-neutral-900">{title}</h3>
      <div className="space-y-5 mt-4">{children}</div>
    </div>
  </div>
);

/* ─── Sidebar TOC ─── */

const tocLinks = [
  { href: '#prerequisites', label: 'Prerequisites' },
  {
    href: '#installation', label: 'Installation', children: [
      { href: '#clone-install', label: 'Clone & Install' },
      { href: '#configure-env', label: 'Configure Environment' },
      { href: '#start-server', label: 'Start MCP Anywhere' },
    ]
  },
  { href: '#adding-servers', label: 'Adding MCP Servers' },
  { href: '#managing-servers', label: 'Managing Servers' },
  { href: '#secret-files', label: 'Secret File Management' },
  { href: '#claude-desktop', label: 'Connect Claude Desktop' },
  { href: '#cli', label: 'CLI Reference' },
  { href: '#troubleshooting', label: 'Troubleshooting' },
  { href: '#popular-servers', label: 'Popular Servers' },
];

const Sidebar = () => {
  const [activeId, setActiveId] = useState<string | null>(null);
  const topOffsetPx = 144; // matches the fixed header / scroll offset behavior

  const tocIds = useMemo(() => {
    const stripHash = (href: string) => href.replace(/^#/, '');
    return tocLinks.flatMap(link => [
      stripHash(link.href),
      ...(link.children ? link.children.map(c => stripHash(c.href)) : [])
    ]);
  }, []);

  useEffect(() => {
    const stripHash = (href: string) => href.replace(/^#/, '');

    const updateActive = () => {
      // If user navigated via hash, prefer that initially.
      const hashId = stripHash(window.location.hash || '');
      if (hashId) setActiveId(hashId);

      const targets = tocIds
        .map(id => document.getElementById(id))
        .filter((el): el is HTMLElement => Boolean(el));

      if (!targets.length) return;

      const tolerance = 24;
      const candidates = targets
        .map(el => ({ id: el.id, top: el.getBoundingClientRect().top }))
        .filter(c => c.top <= topOffsetPx + tolerance)
        .sort((a, b) => b.top - a.top);

      if (candidates[0]?.id) setActiveId(candidates[0].id);
    };

    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = window.requestAnimationFrame(() => {
        raf = 0;
        updateActive();
      });
    };

    updateActive();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);

    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, [tocIds]);

  const stripHash = (href: string) => href.replace(/^#/, '');

  const isActiveHref = (href: string) => activeId === stripHash(href);
  const isActiveGroup = (link: (typeof tocLinks)[number]) => {
    if (isActiveHref(link.href)) return true;
    return Boolean(link.children?.some(child => isActiveHref(child.href)));
  };

  return (
    <aside className="hidden lg:block w-56 shrink-0">
      <div className="toc-sticky">
        <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">On this page</p>
        <nav className="space-y-1 gap-4">
          {tocLinks.map(link => {
            const activeParent = isActiveGroup(link);
            return (
              <div key={link.href}>
                <a
                  href={link.href}
                  className={[
                    'block text-sm transition-colors font-medium py-2',
                    activeParent
                      ? 'text-brand-600 bg-brand-50 rounded-md'
                      : 'text-neutral-600 hover:text-brand-600'
                  ].join(' ')}
                >
                  {link.label}
                </a>
                {link.children && (
                  <div className="border-l-4 border-neutral-100 space-y-0.5">
                    {link.children.map(child => {
                      const activeChild = isActiveHref(child.href);
                      return (
                        <a
                          key={child.href}
                          href={child.href}
                          className={[
                            'block text-sm transition-colors py-2 px-2',
                            activeChild
                              ? 'text-brand-600 bg-brand-50 rounded-md'
                              : 'text-neutral-500 hover:text-brand-600'
                          ].join(' ')}
                        >
                          {child.label}
                        </a>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="mt-8 pt-6 border-t border-neutral-200">
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Next</p>
          <Link
            to="/deployment"
            className="block text-sm text-neutral-600 hover:text-brand-600 transition-colors font-medium"
          >
            Deployment →
          </Link>
        </div>
      </div>
    </aside>
  );
};

/* ─── Page ─── */

export const GettingStarted: React.FC = () => {
  return (
    <div className="min-h-screen bg-white pt-28">

      {/* Page hero */}
      <div className="border-b border-neutral-200 bg-neutral-50">
        <Container className="pt-32 mb-12">
          <Breadcrumb />
          <div className="flex items-start justify-between gap-6">
            <div>
              <h1 className="mb-4 text-4xl font-bold text-neutral-900">Getting Started</h1>
              <p className="max-w-2xl text-lg leading-relaxed text-neutral-600">
                Get up and running with MCP Anywhere — from clone to Claude Desktop in minutes.
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 bg-brand-100 text-brand-800 text-xs font-semibold px-3 py-1.5 rounded-full border border-brand-200 flex-shrink-0 mt-1">
              <span className="w-1.5 h-1.5 bg-brand-500 rounded-full"></span>
              ~5 min setup
            </div>
          </div>
        </Container>
      </div>

      {/* Body */}
      <Container className="py-20">
        <div className="flex gap-16 max-w-6xl">

          <Sidebar />

          <main className="flex-1 min-w-0 max-w-3xl space-y-0">

            {/* Prerequisites */}
            <DocSection first>
              <SectionHeading id="prerequisites" icon={BookOpen}>Prerequisites</SectionHeading>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: 'Python 3.11+', detail: 'Runtime' },
                  { label: 'Docker Desktop', detail: 'For MCP containers' },
                  { label: 'Anthropic API key', detail: 'For auto-configuration' },
                ].map(item => (
                  <div key={item.label} className="border border-neutral-200 rounded-xl p-4 bg-neutral-50">
                    <p className="font-semibold text-neutral-900 text-sm">{item.label}</p>
                    <p className="text-xs text-neutral-500 mt-0.5">{item.detail}</p>
                  </div>
                ))}
              </div>
            </DocSection>

            {/* Installation */}
            <DocSection>
              <SectionHeading id="installation" icon={Terminal}>Installation</SectionHeading>
              <div className="space-y-0">
                <span id="clone-install" className="block scroll-mt-40"></span>
                <StepItem number={1} title="Clone and Install">
                  <CodeBlock code={`git clone https://github.com/locomotive-agency/mcp-anywhere.git
cd mcp-anywhere

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .`} />
                </StepItem>

                <span id="configure-env" className="block scroll-mt-40"></span>
                <StepItem number={2} title="Configure Environment">
                  <CodeBlock code={`cp env.example .env`} />

                  <div className="space-y-4 mt-4">
                    <CodeLabel>Edit <InlineCode>.env</InlineCode> with your values:</CodeLabel>
                    <CodeBlock code={`# Required
SECRET_KEY=your-secure-random-key-here
JWT_SECRET_KEY=your-secure-random-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional
WEB_PORT=8000
LOG_LEVEL=INFO`} />
                  </div>

                  <div className="space-y-4 mt-4">
                    <CodeLabel>Generate secure keys:</CodeLabel>
                    <CodeBlock code={`python -c "import secrets; print(secrets.token_urlsafe(32))"`} />
                  </div>
                </StepItem>

                <span id="start-server" className="block scroll-mt-40"></span>
                <StepItem number={3} title="Start MCP Anywhere" last>
                  <CodeLabel>Using uv:</CodeLabel>
                  <CodeBlock code={`# HTTP server (includes web UI)
uv run mcp-anywhere serve http

# Or STDIO mode (for local Claude Desktop)
uv run mcp-anywhere serve stdio`} />
                  <div className="space-y-4 mt-4">
                    <CodeLabel>Or activate your venv first:</CodeLabel>
                  <CodeBlock code={`source .venv/bin/activate
mcp-anywhere serve http`} />
                  </div>
                  <div className="space-y-4 mt-4">
                    <Callout>
                      The web UI is available at <strong>http://localhost:8000</strong> once the server starts.
                    </Callout>
                  </div>
                </StepItem>
              </div>
            </DocSection>

            {/* Adding MCP Servers */}
            <DocSection>
              <SectionHeading id="adding-servers" icon={Server}>Adding Your First MCP Server</SectionHeading>
              <div className="space-y-0">

                <StepItem number={1} title="Access the Dashboard">
                  <p className="text-base leading-relaxed text-neutral-600">
                    Open <a href="http://localhost:8000" className="text-brand-600 hover:underline font-medium">http://localhost:8000</a> in your browser.
                  </p>
                </StepItem>

                <StepItem number={2} title="Add a New Server">
                  <p className="text-base leading-relaxed text-neutral-600">
                    Click <strong>"Add Server"</strong> in the top right corner.
                  </p>
                </StepItem>

                <StepItem number={3} title="Paste a GitHub URL">
                  <div className="space-y-4 mt-4">
                    <CodeLabel>Provide the GitHub URL of any public MCP server:</CodeLabel>
                    <CodeBlock code={`https://github.com/ahrefs/ahrefs-mcp-server`} />
                  </div>
                  <div className="space-y-4 mt-4">
                    <Callout>
                      Claude AI automatically analyzes the repository and fills in the configuration for you — runtime type, install commands, start command, and environment variables.
                    </Callout>
                  </div>
                  <div className="space-y-4 mt-4">
                    <p className="mt-6 mb-3 text-base font-medium text-neutral-700">Configuration fields:</p>
                  </div>
                  <div className="space-y-2">
                    {[
                      ['Name', 'Unique name for the server'],
                      ['Runtime Type', 'Docker (recommended), npx (Node.js), or uvx (Python)'],
                      ['Install Command', 'Dependency installation command (leave empty if none)'],
                      ['Start Command', 'Command to start the MCP server'],
                      ['Environment Variables', 'API keys and config the server needs'],
                    ].map(([field, desc]) => (
                      <div key={field} className="flex gap-3 text-sm mt-2">
                        <span className="font-mono text-xs bg-neutral-100 border border-neutral-200 text-neutral-700 px-2 py-0.5 rounded flex-shrink-0 self-start mt-0.5">{field}</span>
                        <span className="text-neutral-600">{desc}</span>
                      </div>
                    ))}
                  </div>
                </StepItem>

                <StepItem number={4} title="Complete Setup" last>
                  <p className="text-base leading-relaxed text-neutral-600">
                    Click <strong>"Add Server"</strong> to confirm. MCP Anywhere will build the container and add it to your dashboard.
                  </p>
                </StepItem>

              </div>
            </DocSection>

            {/* Managing Servers */}
            <DocSection>
              <SectionHeading id="managing-servers" icon={Wrench}>Managing Your Servers</SectionHeading>
              <div className="space-y-8">

                <div>
                  <Subheading>Server Dashboard</Subheading>
                  <div className="border border-neutral-200 rounded-xl overflow-hidden">
                    {[
                      ['Server Status', 'Active / inactive indicator'],
                      ['Available Tools', 'The tools provided by the server'],
                      ['Configuration Details', 'Runtime type, GitHub URL, and other attributes'],
                    ].map(([label, desc], i) => (
                      <div key={label} className={`flex gap-4 p-2 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-neutral-50'}`}>
                        <span className="font-medium text-neutral-800 w-44 flex-shrink-0">{label}</span>
                        <span className="text-neutral-500">{desc}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <Subheading>Tool Management</Subheading>
                  <p className="mb-4 text-base leading-relaxed text-neutral-600">
                    Click any server to open detailed management. Each tool can be toggled on/off independently.
                  </p>
                  <div className="border border-neutral-200 rounded-xl overflow-hidden">
                    {[
                      ['Individual Control', 'Toggle each tool on/off independently'],
                      ['Tool Prefixes', <>Each server gets a unique prefix, e.g. <InlineCode>0123abcd</InlineCode></>],
                      ['Tool Naming', <>Prefixed as <InlineCode>0123abcd_tool_name</InlineCode> to prevent conflicts</>],
                    ].map(([label, desc], i) => (
                      <div key={String(label)} className={`flex gap-4 p-2 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-neutral-50'}`}>
                        <span className="font-medium text-neutral-800 w-44 flex-shrink-0">{label}</span>
                        <span className="text-neutral-500">{desc}</span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </DocSection>

            {/* Secret File Management */}
            <DocSection>
              <SectionHeading id="secret-files" icon={Shield}>Secret File Management</SectionHeading>
              <p className="-mt-2 mb-8 text-base leading-relaxed text-neutral-600">
                Securely upload credential files for MCP servers that require file-based authentication.
              </p>

              <div className="space-y-8">
                <div>
                  <Subheading>Supported File Types</Subheading>
                  <div className="flex flex-wrap gap-2">
                    {['.json', '.pem', '.key', '.crt', '.p12', '.pfx', '.jks', '.yaml', '.yml', '.xml'].map(ext => (
                      <span key={ext} className="font-mono text-xs bg-neutral-100 border border-neutral-200 text-neutral-700 px-3 py-1 rounded-full">
                        {ext}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mb-6">
                  <Subheading>Upload Process</Subheading>
                  <ol className="space-y-2 text-sm text-neutral-600">
                    {[
                      'Navigate to the server detail page',
                      'Use the "Upload Secret File" form',
                      <>Specify an environment variable name, e.g. <InlineCode>GOOGLE_APPLICATION_CREDENTIALS</InlineCode></>,
                      'Upload the credential file',
                      'The file mounts automatically when the container starts',
                    ].map((step, i) => (
                      <li key={i} className="flex gap-3">
                        <span className="w-6 h-6 mt-4 rounded-full bg-neutral-100 border border-neutral-200 text-neutral-500 font-semibold text-xs flex items-center justify-center flex-shrink-0 mt-1">
                          {i + 1}
                        </span>
                        <span className="text-neutral-600 mt-4">{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                <Callout className="mb-16">
                  Files are encrypted at rest (AES-128), capped at 10MB, mounted read-only inside containers, and automatically cleaned up when a server is deleted.
                </Callout>
              </div>
            </DocSection>

            {/* Connecting Claude Desktop */}
            <DocSection>
              <SectionHeading id="claude-desktop" icon={BookOpen}>Connecting Claude Desktop</SectionHeading>
              <div className="space-y-0">

                <StepItem number={1} title="Find your uv binary path">
                  <CodeBlock code={`which uv
# Example output: /Users/yourname/.local/bin/uv`} />
                </StepItem>

                <StepItem number={2} title="Edit claude_desktop_config.json">
                  <p className="mb-3 text-base leading-relaxed text-neutral-600">
                    macOS: <InlineCode>~/Library/Application Support/Claude/claude_desktop_config.json</InlineCode><br />
                    Windows: <InlineCode>%APPDATA%\Claude\claude_desktop_config.json</InlineCode>
                  </p>
                  <CodeBlock language="json" filename="claude_desktop_config.json" code={`{
  "mcpServers": {
    "mcp-anywhere": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/path/to/mcp-anywhere",
        "mcp-anywhere",
        "connect"
      ]
    }
  }
}`} />
                </StepItem>

                <StepItem number={3} title="Start MCP Anywhere in STDIO mode">
                  <CodeBlock code={`uv run mcp-anywhere serve stdio`} />
                </StepItem>

                <StepItem number={4} title="Restart Claude Desktop" last>
                  <p className="text-base leading-relaxed text-neutral-600">
                    Quit and reopen Claude Desktop. Ask <em>"What MCP tools do I have available?"</em> — Claude should list all enabled tools with their unique prefixes.
                  </p>
                </StepItem>

              </div>
            </DocSection>

            {/* CLI Reference */}
            <DocSection>
              <SectionHeading id="cli" icon={Terminal}>CLI Reference</SectionHeading>
              <div className="space-y-6 mb-16">
                {[
                  {
                    label: 'Server commands',
                    code: `# HTTP server with web UI
mcp-anywhere serve http

# STDIO server for Claude Desktop
mcp-anywhere serve stdio

# Custom host and port
mcp-anywhere serve http --host 0.0.0.0 --port 8080`,
                  },
                  {
                    label: 'Client commands',
                    code: `# Connect as MCP client
mcp-anywhere connect`,
                  },
                  {
                    label: 'Data management',
                    code: `# Reset all data (database, containers, etc.)
mcp-anywhere reset --confirm`,
                  },
                ].map(({ label, code }) => (
                  <div key={label} className="mb-6">
                    <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2">{label}</p>
                    <CodeBlock code={code} />
                  </div>
                ))}
              </div>
            </DocSection>

            {/* Troubleshooting */}
            <DocSection>
              <SectionHeading id="troubleshooting" icon={AlertCircle}>Troubleshooting</SectionHeading>
              <div className="space-y-8 mb-16">
                {[
                  {
                    issue: 'Docker not running',
                    fix: 'Start Docker Desktop and verify with:',
                    code: `docker info`,
                  },
                  {
                    issue: 'Port already in use',
                    fix: 'Use a different port:',
                    code: `mcp-anywhere serve http --port 8080`,
                  },
                  {
                    issue: 'API key issues',
                    fix: `Verify ANTHROPIC_API_KEY is set in .env and has available credits.`,
                  },
                  {
                    issue: 'Tools not showing in Claude Desktop',
                    fix: 'Restart Claude Desktop, then verify MCP Anywhere is running:',
                    code: `curl http://localhost:8000/health`,
                  },
                ].map(({ issue, fix, code }) => (
                  <div key={issue} className="border border-neutral-200 rounded-xl overflow-hidden mb-6">
                    <div className="flex items-center gap-2 bg-neutral-50 border-b border-neutral-200 px-4 py-3">
                      <div className="w-2 h-2 rounded-full bg-red-400"></div>
                      <span className="text-sm font-semibold text-neutral-800 p-2">{issue}</span>
                    </div>
                    <div className="space-y-4 px-4 py-5">
                      <p className="text-base leading-relaxed text-neutral-600 p-2">{fix}</p>
                      {code && <div className="mb-4"><CodeBlock code={code} /></div>}
                    </div>
                  </div>
                ))}
              </div>
            </DocSection>

            {/* Popular MCP Servers */}
            <DocSection>
              <SectionHeading id="popular-servers" icon={Server}>Popular MCP Servers to Try</SectionHeading>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  {
                    name: 'Official MCP Servers',
                    desc: 'Collection of official MCP tools and implementations.',
                    href: 'https://github.com/modelcontextprotocol/servers',
                    tag: 'Official',
                  },
                  {
                    name: 'Python Interpreter',
                    desc: 'Execute Python code safely within your context.',
                    href: 'https://github.com/yzfly/mcp-python-interpreter',
                    tag: 'Community',
                  },
                ].map(({ name, desc, href, tag }) => (
                  <a
                    key={name}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group block p-6 border border-neutral-200 rounded-xl hover:border-brand-400 hover:shadow-md transition-all"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-semibold text-neutral-900 group-hover:text-brand-700 transition-colors">{name}</h3>
                      <span className="text-xs bg-neutral-100 text-neutral-500 px-2 py-0.5 rounded-full flex-shrink-0">{tag}</span>
                    </div>
                    <p className="text-base leading-relaxed text-neutral-600">{desc}</p>
                  </a>
                ))}
              </div>
            </DocSection>

          </main>
        </div>
      </Container>
    </div>
  );
};
