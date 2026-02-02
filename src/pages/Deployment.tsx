import React from 'react';
import { Container } from '../components/Container';
import { Section } from '../components/Section';
import { CodeBlock } from '../components/CodeBlock';

export const Deployment: React.FC = () => {
  return (
    <div className="pt-20 min-h-screen bg-neutral-50">
      <Section className="bg-white border-b border-neutral-200 pb-8 pt-20">
        <Container>
          <h1 className="text-4xl font-bold text-neutral-900 mb-4">Deployment</h1>
          <p className="text-xl text-neutral-600 max-w-2xl">
            Get your MCP Anywhere instance running in production with our step-by-step guides.
          </p>
        </Container>
      </Section>

      <Container className="py-12">
        <div className="mx-auto space-y-24">

          <section className="scroll-mt-24 pt-16">
            <div className="prose max-w-none">
              <h2 className="text-3xl font-bold text-neutral-900 mb-4 flex items-center gap-3">
                <span
                  className="flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold"
                  style={{ backgroundColor: 'var(--color-brand-100)', color: 'var(--color-brand-700)' }}
                >1</span>
                Deploy to Fly.io
              </h2>
              <p className="text-lg text-neutral-600 mb-10 leading-relaxed">
                Fly.io is our recommended platform for hosting MCP Anywhere. It offers excellent global distribution, native Docker support, and a generous free tier.
              </p>

              <div className="space-y-12 grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="bg-white p-8 rounded-2xl border border-neutral-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                  <h3 className="text-xl font-semibold text-neutral-900 mb-4">1. Install Fly CLI</h3>
                  <p className="text-neutral-600 mb-6">First, you'll need the Fly.io command line tool installed on your machine.</p>
                  <CodeBlock code={`brew install flyctl # macOS
# or
curl -L https://fly.io/install.sh | sh # Linux/WSL`} language="bash" />
                </div>

                <div className="bg-white p-8 rounded-2xl border border-neutral-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                  <h3 className="text-xl font-semibold text-neutral-900 mb-4">2. Launch App</h3>
                  <p className="text-neutral-600 mb-6">Initialize your app. This will generate a <code className="text-sm bg-neutral-100 px-1.5 py-0.5 rounded text-neutral-800">fly.toml</code> configuration file.</p>
                  <CodeBlock code={`fly launch`} language="bash" />
                  <p className="text-neutral-600 mt-8 text-sm">
                    <strong>Note:</strong> Follow the interactive prompts to configure your app name and region.
                  </p>
                </div>

                <div className="bg-white p-8 rounded-2xl border border-neutral-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                  <h3 className="text-xl font-semibold text-neutral-900 mb-4">3. Set Secrets</h3>
                  <p className="text-neutral-600 mb-6">Configure your environment variables securely.</p>
                  <CodeBlock
                    code={`fly secrets set SECRET_KEY=your_secret_key \\
  JWT_SECRET_KEY=your_jwt_secret \\
  ANTHROPIC_API_KEY=sk-...`}
                    language="bash"
                  />
                </div>

                <div className="bg-white p-8 rounded-2xl border border-neutral-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                  <h3 className="text-xl font-semibold text-neutral-900 mb-4">4. Deploy</h3>
                  <p className="text-neutral-600 mb-6">Push your application to the cloud.</p>
                  <CodeBlock code={`fly deploy`} language="bash" />
                </div>
              </div>
            </div>
          </section>

          <section className="scroll-mt-24 pt-16">
            <div className="prose max-w-none">
              <h2 className="text-3xl font-bold text-neutral-900 mb-4 flex items-center gap-3">
                <span
                  className="flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold"
                  style={{ backgroundColor: 'var(--color-brand-100)', color: 'var(--color-brand-700)' }}
                >2</span>
                Monitoring
              </h2>
              <p className="text-lg text-neutral-600 mb-10">
                Keep track of your application's health and performance.
              </p>

              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-white p-8 rounded-2xl border border-neutral-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                  <h3 className="text-lg font-semibold text-neutral-900 mb-4">View Logs</h3>
                  <p className="text-neutral-600 mb-6 text-sm">Stream real-time application logs.</p>
                  <CodeBlock code={`fly logs -f`} language="bash" />
                </div>
                <div className="bg-white p-8 rounded-2xl border border-neutral-200 shadow-sm hover:shadow-md transition-shadow duration-200">
                  <h3 className="text-lg font-semibold text-neutral-900 mb-4">Metrics</h3>
                  <p className="text-neutral-600 mb-6 text-sm">Open the metrics dashboard.</p>
                  <CodeBlock code={`fly dashboard metrics`} language="bash" />
                </div>
              </div>
            </div>
          </section>

          <section className="scroll-mt-24 pt-16">
            <div className="prose max-w-none">
              <h2 className="text-3xl font-bold text-neutral-900 mb-8 flex items-center gap-3">
                <span
                  className="flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold"
                  style={{ backgroundColor: 'var(--color-brand-100)', color: 'var(--color-brand-700)' }}
                >3</span>
                Troubleshooting
              </h2>

              <div className="bg-white rounded-2xl border border-neutral-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow duration-200">
                <div className="p-8 border-b border-neutral-200">
                  <h3 className="text-xl font-semibold text-neutral-900 mb-6">Common Issues</h3>
                  <div className="space-y-6">
                    <div className="flex gap-4 items-start">
                      <div className="w-8 h-8 rounded-full bg-red-100 text-red-600 flex items-center justify-center flex-shrink-0 mt-0.5 font-bold">!</div>
                      <div>
                        <h4 className="font-medium text-neutral-900 text-lg">App Won't Start</h4>
                        <ul className="mt-3 space-y-2 text-neutral-600 list-disc list-inside">
                          <li>Check logs with <code>fly logs</code></li>
                          <li>Verify all environment variables are set</li>
                          <li>Ensure Docker build completed successfully</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-8 bg-neutral-50">
                  <h3 className="text-lg font-semibold text-neutral-900 mb-4">Emergency Reset</h3>
                  <p className="text-neutral-600 mb-6">
                    If you need to completely reset the database and start fresh:
                  </p>
                  <CodeBlock code={`fly ssh console
/app/venv/bin/python -m mcp_anywhere reset --confirm`} language="bash" />
                </div>
              </div>
            </div>
          </section>

        </div>
      </Container>
    </div>
  );
};
