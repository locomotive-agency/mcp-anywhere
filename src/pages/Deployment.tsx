import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Container } from '../components/Container';
import { CodeBlock } from '../components/CodeBlock';
import { ChevronRight, Info, Terminal, Globe, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';

/* ─── Primitives (same pattern as GettingStarted) ─── */

const Breadcrumb = () => (
  <nav className="mb-8 flex items-center gap-1.5 text-sm text-neutral-500">
    <Link to="/" className="hover:text-brand-600 transition-colors">Docs</Link>
    <ChevronRight size={14} className="text-neutral-300" />
    <span className="text-neutral-900 font-medium">Deployment</span>
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

const DocSection = ({ first = false, children }: { first?: boolean; children: React.ReactNode }) => (
  <section className={first ? '' : 'border-t border-neutral-100 pt-16'}>
    {children}
  </section>
);

const CodeLabel = ({ children }: { children: React.ReactNode }) => (
  <p className="mt-5 mb-3 text-base leading-relaxed text-neutral-600">
    {children}
  </p>
);

const StepItem = ({ number, title, last = false, children }: {
  number: number; title: string; last?: boolean; children: React.ReactNode;
}) => (
  <div className="relative flex gap-6">
    <div className="flex flex-col items-center flex-shrink-0">
      <div className="w-8 h-8 rounded-full bg-brand-500 text-neutral-900 font-bold text-sm flex items-center justify-center z-10 shadow-sm flex-shrink-0">
        {number}
      </div>
      {!last && <div className="w-px flex-1 bg-neutral-200 mt-2"></div>}
    </div>
    <div className={`flex-1 min-w-0 ${last ? 'pb-0' : 'pb-16'}`}>
      <h3 className="mt-1 mb-5 text-xl font-semibold text-neutral-900">{title}</h3>
      <div className="space-y-5">{children}</div>
    </div>
  </div>
);

/* ─── Sidebar TOC ─── */

const tocLinks = [
  { href: '#why-flyio', label: 'Why Fly.io?' },
  { href: '#prerequisites', label: 'Prerequisites' },
  {
    href: '#installation', label: 'Installation', children: [
      { href: '#install-cli', label: 'Install Fly CLI' },
      { href: '#authenticate', label: 'Authenticate' },
    ]
  },
  {
    href: '#deploy', label: 'Deployment', children: [
      { href: '#init-app', label: 'Initialize App' },
      { href: '#set-secrets', label: 'Set Secrets' },
      { href: '#storage', label: 'Persistent Storage' },
      { href: '#deploy-app', label: 'Deploy' },
      { href: '#verify', label: 'Verify' },
    ]
  },
  { href: '#monitoring', label: 'Monitoring' },
  { href: '#updating', label: 'Updating' },
  { href: '#troubleshooting', label: 'Troubleshooting' },
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
        <nav className="space-y-1">
          {tocLinks.map(link => {
            const activeParent = isActiveGroup(link);
            return (
              <div key={link.href}>
                <a
                  href={link.href}
                  className={[
                    'block text-sm transition-colors font-medium p-2',
                    activeParent
                      ? 'text-brand-600 rounded-md'
                      : 'text-neutral-600 hover:text-brand-600'
                  ].join(' ')}
                >
                  {link.label}
                </a>
                {link.children && (
                  <div className="pl-3 border-l-2 border-neutral-100 ml-1 mb-1 space-y-0.5">
                    {link.children.map(child => {
                      const activeChild = isActiveHref(child.href);
                      return (
                        <a
                          key={child.href}
                          href={child.href}
                          className={[
                            'block text-sm transition-colors py-2 px-4',
                            activeChild
                              ? 'text-brand-600 rounded-md'
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
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Previous</p>
          <Link
            to="/getting-started"
            className="block text-sm text-neutral-600 hover:text-brand-600 transition-colors font-medium"
          >
            ← Getting Started
          </Link>
        </div>
      </div>
    </aside>
  );
};

/* ─── Page ─── */

export const Deployment: React.FC = () => {
  return (
    <div className="min-h-screen bg-white pt-28">

      {/* Page hero */}
      <div className="border-b border-neutral-200 bg-neutral-50">
        <Container className="pt-32 mb-12">
          <Breadcrumb />
          <div className="flex items-start justify-between gap-6">
            <div>
              <h1 className="mb-4 text-4xl font-bold text-neutral-900">Deployment</h1>
              <p className="max-w-2xl text-lg leading-relaxed text-neutral-600">
                Deploy MCP Anywhere to Fly.io for a production-ready instance with automatic SSL and global availability.
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 bg-brand-100 text-brand-800 text-xs font-semibold px-3 py-1.5 rounded-full border border-brand-200 flex-shrink-0 mt-1">
              <Globe size={11} />
              Fly.io
            </div>
          </div>
        </Container>
      </div>

      {/* Body */}
      <Container className="py-20">
        <div className="flex gap-16 max-w-6xl">

          <Sidebar />

          <main className="flex-1 min-w-0 max-w-3xl space-y-0">

            {/* Why Fly.io */}
            <DocSection first>
              <SectionHeading id="why-flyio" icon={Globe}>Why Fly.io?</SectionHeading>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  ['Global edge deployment', 'Run close to your users worldwide'],
                  ['Automatic SSL certificates', 'HTTPS out of the box'],
                  ['Built-in persistent storage', 'Volumes for database and secrets'],
                  ['Free tier available', 'No cost to get started'],
                ].map(([title, desc]) => (
                  <div key={title} className="flex gap-3 border border-neutral-200 rounded-xl p-4 bg-neutral-50">
                    <CheckCircle size={16} className="text-brand-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-semibold text-neutral-800">{title}</p>
                      <p className="text-xs text-neutral-500 mt-0.5">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </DocSection>

            {/* Prerequisites */}
            <DocSection>
              <SectionHeading id="prerequisites" icon={CheckCircle}>Prerequisites</SectionHeading>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: 'Fly.io account', detail: 'Sign up free at fly.io', href: 'https://fly.io' },
                  { label: 'Repo cloned locally', detail: 'See Getting Started' },
                  { label: 'Docker running', detail: 'Required for local build' },
                ].map(item => (
                  <div key={item.label} className="border border-neutral-200 rounded-xl p-4 bg-neutral-50">
                    {item.href ? (
                      <a href={item.href} target="_blank" rel="noopener noreferrer" className="font-semibold text-brand-600 hover:underline text-sm">
                        {item.label}
                      </a>
                    ) : (
                      <p className="font-semibold text-neutral-900 text-sm">{item.label}</p>
                    )}
                    <p className="text-xs text-neutral-500 mt-0.5">{item.detail}</p>
                  </div>
                ))}
              </div>
            </DocSection>

            {/* Installation */}
            <DocSection>
              <SectionHeading id="installation" icon={Terminal}>Installation</SectionHeading>
              <div className="space-y-0">

                <span id="install-cli" className="block scroll-mt-40"></span>
                <StepItem number={1} title="Install Fly CLI">
                  <div className="space-y-5 mb-8">
                    <div className='mb-6'>
                      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-400">macOS</p>
                      <CodeBlock code={`brew install flyctl`} />
                    </div>
                    <div className='mb-6'>
                      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-400">Linux / WSL</p>
                      <CodeBlock code={`curl -L https://fly.io/install.sh | sh`} />
                    </div>
                    <div className='mb-6'>
                      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-400">Windows (PowerShell)</p>
                      <CodeBlock code={`iwr https://fly.io/install.ps1 -useb | iex`} />
                    </div>
                  </div>
                </StepItem>

                <span id="authenticate" className="block scroll-mt-40"></span>
                <StepItem number={2} title="Authenticate" last>
                  <div className='mb-16 mt-4'>
                    <CodeBlock code={`fly auth login`} />
                  </div>
                </StepItem>

              </div>
            </DocSection>

            {/* Deployment */}
            <DocSection>
              <SectionHeading id="deploy" icon={Globe}>Deployment</SectionHeading>
              <div className="space-y-0">

                <span id="init-app" className="block scroll-mt-40"></span>
                <StepItem number={1} title="Initialize Your App">
                  <div className='mb-6 mt-4'>
                    <CodeBlock code={`cd mcp-anywhere
fly launch`} />
                  </div>
                  <Callout className='mb-8'>
                    When prompted: choose an app name, select a region close to you, skip PostgreSQL and Redis, and confirm creating the app.
                  </Callout>
                </StepItem>

                <span id="set-secrets" className="block scroll-mt-40"></span>
                <StepItem number={2} title="Configure Environment Variables">
                  <div className='mb-6 mt-4'>
                    <CodeLabel>Generate secure keys first:</CodeLabel>
                    <CodeBlock code={`python -c "import secrets; print(secrets.token_urlsafe(32))"`} />
                  </div>
                  <div className='mb-8'>
                    <CodeLabel>Then set all required secrets:</CodeLabel>
                    <CodeBlock code={`fly secrets set SECRET_KEY="your-secret-key-here"
fly secrets set JWT_SECRET_KEY="your-jwt-secret-here"
fly secrets set ANTHROPIC_API_KEY="your-anthropic-api-key-here"`} />
                  </div>
                </StepItem>

                <span id="storage" className="block scroll-mt-40"></span>
                <StepItem number={3} title="Create Persistent Storage">
                  <div className='mb-6 mt-4'>
                    <CodeLabel>MCP Anywhere needs a volume for its database and secrets:</CodeLabel>
                    <CodeBlock code={`fly volumes create mcp_data --size 10`} />
                  </div>
                </StepItem>

                <span id="deploy-app" className="block scroll-mt-40"></span>
                <StepItem number={4} title="Deploy">
                  <div className='mb-6 mt-4'>
                    <CodeBlock code={`fly deploy`} />
                  </div>
                  <p className="text-base leading-relaxed text-neutral-600 mb-8">This builds the Docker image, pushes to Fly's registry, and starts the app in your chosen region.</p>
                </StepItem>

                <span id="verify" className="block scroll-mt-40"></span>
                <StepItem number={5} title="Verify Deployment" last>
                  <div className='mb-6 mt-4'>
                    <CodeBlock code={`# Check status
fly status

# View logs
fly logs

# Open in browser
fly open`} />
                  </div>
                  <Callout className='mb-16'>
                    Your instance is live at <strong>https://your-app-name.fly.dev</strong>
                  </Callout>
                </StepItem>

              </div>
            </DocSection>

            {/* Monitoring */}
            <DocSection>
              <SectionHeading id="monitoring" icon={Terminal}>Monitoring</SectionHeading>
              <div className="grid sm:grid-cols-2 gap-6 mb-16">
                {[
                  {
                    title: 'View Logs',
                    desc: 'Stream real-time application logs.',
                    code: `# Live stream
fly logs -f

# Last 100 lines
fly logs -n 100`,
                  },
                  {
                    title: 'Metrics',
                    desc: 'Open the Fly.io metrics dashboard.',
                    code: `fly dashboard metrics`,
                  },
                ].map(({ title, desc, code }) => (
                  <div key={title} className="border border-neutral-200 rounded-xl overflow-hidden">
                    <div className="px-5 py-4 border-b border-neutral-100">
                      <p className="font-semibold text-neutral-900 text-sm px-2">{title}</p>
                      <p className="text-xs text-neutral-500 mt-0.5 px-2">{desc}</p>
                    </div>
                    <div className="p-6">
                      <CodeBlock code={code} />
                    </div>
                  </div>
                ))}
              </div>
            </DocSection>

            {/* Updating */}
            <DocSection>
              <SectionHeading id="updating" icon={RefreshCw}>Updating</SectionHeading>
              <p className="-mt-2 mb-6 text-base leading-relaxed text-neutral-600">To deploy a new version of MCP Anywhere:</p>
              <CodeBlock code={`# Pull latest changes
git pull origin main

# Deploy updates
fly deploy`} />
            </DocSection>

            {/* Troubleshooting */}
            <DocSection>
              <SectionHeading id="troubleshooting" icon={AlertCircle}>Troubleshooting</SectionHeading>
              <div className="space-y-6">

                <div className="border border-neutral-200 rounded-xl overflow-hidden mb-8">
                  <div className="flex items-center gap-2 bg-neutral-50 border-b border-neutral-200 p-2">
                    <div className="w-2 h-2 rounded-full bg-red-400"></div>
                    <span className="text-sm font-semibold text-neutral-800">App Won't Start</span>
                  </div>
                  <div className="space-y-4 p-6">
                    <CodeBlock code={`# Check logs for errors
fly logs -n 200

# Common causes:
# - Missing environment variables
# - Docker build failures
# - Port binding issues`} />
                  </div>
                </div>

                <div className="border border-neutral-200 rounded-xl overflow-hidden">
                  <div className="flex items-center gap-2 bg-neutral-50 border-b border-neutral-200 p-2">
                    <div className="w-2 h-2 rounded-full bg-amber-400"></div>
                    <span className="text-sm font-semibold text-neutral-800">Emergency Reset</span>
                  </div>

                  <div className="space-y-4 p-6">
                    <p className="text-base leading-relaxed text-neutral-600 mb-4">If you need to wipe the database and start fresh:</p>
                    <CodeBlock code={`# SSH into your instance
fly ssh console

# Run the reset command
/app/venv/bin/python -m mcp_anywhere reset --confirm`} />
                  </div>
                </div>

              </div>
            </DocSection>

          </main>
        </div>
      </Container>
    </div>
  );
};
