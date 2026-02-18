import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AppFooter } from "@/components/AppFooter";
import { NavUnderline } from "@/components/NavUnderline";
import { ArrowLeft, ArrowUp, Copy, ExternalLink, Link as LinkIcon, Menu, Sparkles } from "lucide-react";
import * as React from "react";
import { useNavigate, useLocation } from "react-router-dom";

const FRONTEND_URL = "https://coderagent.vercel.app/";
const BACKEND_URL = "https://code-review-agent-api.onrender.com/";

const navButtonClassName =
  "gap-2 transition-all duration-200 hover:bg-accent/60 hover:shadow-sm active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-primary/60";

type CopyButtonProps = {
  value: string;
  label: string;
};

const CopyButton = ({ value, label }: CopyButtonProps) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      onClick={handleCopy}
      className="h-8 px-2 text-xs gap-1.5 hover:brightness-110 active:scale-[0.98]"
      aria-label={`Copy ${label}`}
      title={`Copy ${label}`}
    >
      <Copy className="h-3.5 w-3.5" />
      {copied ? "Copied" : "Copy"}
    </Button>
  );
};

type DocSection = {
  id: string;
  title: string;
};

const SECTIONS: DocSection[] = [
  { id: "overview", title: "Overview" },
  { id: "features", title: "Features" },
  { id: "supported-languages", title: "Supported Languages" },
  { id: "how-it-works", title: "How It Works" },
  { id: "architecture", title: "High-Level Architecture" },
  { id: "live-links", title: "Live Deployment Links" },
  { id: "api-quick-start", title: "API Quick Start" },
  { id: "request-format", title: "Request Format" },
  { id: "response-format", title: "Response Format" },
  { id: "severity-levels", title: "Severity Levels" },
  { id: "error-handling", title: "Error Handling" },
  { id: "configuration", title: "Configuration & Environment Variables" },
  { id: "offline-mode", title: "Offline Mode (No LLM)" },
  { id: "limits", title: "Limits & Constraints" },
  { id: "security-privacy", title: "Security & Privacy" },
  { id: "roadmap", title: "Roadmap" },
  { id: "versioning", title: "Versioning & Changelog" },
  { id: "contributing", title: "Contribution Guide" },
];

function CodeBlock({ title, value, label }: { title: string; value: string; label?: string }) {
  return (
    <div className="rounded-2xl border bg-card p-4 sm:p-5 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold truncate">{title}</p>
          {label ? <p className="text-[11px] text-muted-foreground mt-0.5 font-mono uppercase tracking-wide">{label}</p> : null}
        </div>
        <CopyButton value={value} label={title} />
      </div>
      <pre className="text-xs sm:text-sm overflow-auto whitespace-pre rounded-lg bg-muted/40 p-3 border font-mono leading-relaxed">
        {value}
      </pre>
    </div>
  );
}

function Section({
  id,
  title,
  children,
}: React.PropsWithChildren<{ id: string; title: string }>) {
  const copyLink = async () => {
    const url = `${window.location.origin}${window.location.pathname}#${id}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // ignore
    }
  };

  return (
    <section id={id} className="scroll-mt-24 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-2xl font-black tracking-tight">{title}</h2>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={copyLink}
          className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
          aria-label={`Copy link to ${title}`}
          title="Copy link"
        >
          <LinkIcon className="h-4 w-4" />
        </Button>
      </div>
      {children}
    </section>
  );
}

function Toc({
  activeId,
  onNavigate,
}: {
  activeId: string | null;
  onNavigate?: () => void;
}) {
  return (
    <nav className="space-y-1" aria-label="Table of contents">
      {SECTIONS.map((s) => {
        const isActive = s.id === activeId;
        return (
          <a
            key={s.id}
            href={`#${s.id}`}
            onClick={() => onNavigate?.()}
            className={
              "block rounded-md px-2 py-1 text-sm transition-colors " +
              (isActive
                ? "bg-muted/50 text-foreground ring-1 ring-border/60"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40")
            }
          >
            {s.title}
          </a>
        );
      })}
    </nav>
  );
}

const DocsPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const goHomeOrTop = React.useCallback(() => {
    if (location.pathname === "/") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    navigate("/");
  }, [location.pathname, navigate]);

  const [activeId, setActiveId] = React.useState<string | null>(SECTIONS[0]?.id ?? null);
  const [mobileTocOpen, setMobileTocOpen] = React.useState(false);
  const [showTop, setShowTop] = React.useState(false);

  const healthCurl = `curl ${BACKEND_URL}healthz`;
  const reviewCurl = `curl -X POST ${BACKEND_URL}v2/review/file \\\n  -H "Content-Type: application/json" \\\n  -d '{"filename":"input.py","code":"def add(a,b):\\n    return a+b\\n","language":"python","enabled_checks":{"security":true,"style":true,"performance":true}}'`;

  const requestExample = `{
  "filename": "input.py",
  "code": "def add(a, b):\n    return a + b\n",
  "language": "python",
  "enabled_checks": {
    "security": true,
    "style": true,
    "performance": true
  }
}`;

  const responseExample = `{
  "issues": [
    {
      "file": "input.py",
      "line": 12,
      "category": "security",
      "severity": "high",
      "description": "User-controlled input is used in SQL query",
      "suggestion": "Use parameterized queries / prepared statements",
      "source": "bandit"
    }
  ],
  "score": {
    "score": 92,
    "counts_by_severity": { "critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0 }
  },
  "static_analysis": {
    "flake8": { "issues": [] },
    "bandit": { "result": { "results": [] } }
  }
}`;

  React.useEffect(() => {
    // Active section highlighting
    const ids = SECTIONS.map((s) => s.id);
    const els = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => Boolean(el));

    if (els.length === 0) return;

    const obs = new IntersectionObserver(
      (entries) => {
        // pick the most visible entry
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => (b.intersectionRatio ?? 0) - (a.intersectionRatio ?? 0));
        if (visible[0]?.target?.id) setActiveId(visible[0].target.id);
      },
      {
        root: null,
        // header height + a bit of breathing room
        rootMargin: "-96px 0px -70% 0px",
        threshold: [0.05, 0.15, 0.25, 0.35, 0.5],
      },
    );

    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  React.useEffect(() => {
    const onScroll = () => setShowTop(window.scrollY > 500);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true } as any);
    return () => window.removeEventListener('scroll', onScroll as any);
  }, []);

  return (
    <div className="min-h-screen w-full bg-background text-foreground flex flex-col">
      <header className="w-full sticky top-0 z-50 bg-header-bg text-header-fg">
        <div className="border-b border-header-border">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-header-accent-blue/45 to-transparent" />
          <div className="w-full px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <button
                type="button"
                onClick={goHomeOrTop}
                className="group inline-flex items-center gap-3 min-w-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-header-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-header-bg"
                aria-label="Go to home"
                title="Home"
              >
                <img
                  src="/logo.png"
                  alt="CRA Logo"
                  width={40}
                  height={40}
                  className="h-10 w-10 object-contain"
                />
                <h1 className="text-2xl sm:text-3xl font-black tracking-tight uppercase bg-gradient-to-r from-header-accent-blue to-header-accent-emerald bg-clip-text text-transparent truncate">
                  CRA
                </h1>
              </button>
              <span className="hidden sm:inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-xs text-header-muted">
                Docs
              </span>
            </div>
            <div className="flex items-center gap-2 sm:gap-4">
              <Button
                variant="ghost"
                size="sm"
                className={
                  navButtonClassName +
                  " group relative text-header-muted hover:text-header-fg focus-visible:ring-header-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-header-bg"
                }
                onClick={() => navigate("/")}
              >
                <ArrowLeft className="h-4 w-4" />
                Back
                <NavUnderline />
              </Button>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      <main className="w-full flex-1 px-4 pt-8 pb-16">
        <div className="container mx-auto max-w-6xl">
          {/* Hero */}
          <section className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-primary/8 via-background to-accent/10 p-6 sm:p-10">
            <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl" />
            <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-accent/10 blur-3xl" />

            <div className="relative space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full border bg-card/60 px-3 py-1 text-xs text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5" />
                AI + Static analysis
              </div>
              <h2 className="text-3xl sm:text-4xl font-black tracking-tight">Documentation</h2>
              <p className="text-sm sm:text-base text-muted-foreground leading-relaxed max-w-3xl">
                Everything you need to understand how CRA works, how to call the API, and how the results are structured.
              </p>
            </div>
          </section>

          {/* Mobile TOC */}
          <div className="mt-6 lg:hidden">
            <div className="rounded-2xl border bg-card p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold">On this page</p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setMobileTocOpen((v) => !v)}
                  className="h-8 px-2 text-xs gap-1.5"
                  aria-expanded={mobileTocOpen}
                  aria-controls="docs-mobile-toc"
                >
                  <Menu className="h-4 w-4" />
                  {mobileTocOpen ? "Hide" : "Show"}
                </Button>
              </div>
              {mobileTocOpen ? (
                <div id="docs-mobile-toc" className="mt-3">
                  <Toc activeId={activeId} onNavigate={() => setMobileTocOpen(false)} />
                </div>
              ) : null}
            </div>
          </div>

          <div className="mt-10 grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-8">
            {/* Table of contents */}
            <aside className="hidden lg:block lg:sticky lg:top-24 h-fit space-y-4">
              <div className="rounded-2xl border bg-card p-5">
                <p className="text-sm font-bold mb-3">On this page</p>
                <Toc activeId={activeId} />
              </div>

              <div className="rounded-2xl border bg-card p-5 space-y-2">
                <p className="text-sm font-bold">Live links</p>
                <a
                  className="underline underline-offset-4 hover:text-primary inline-flex items-center gap-1 text-sm"
                  href={FRONTEND_URL}
                  target="_blank"
                  rel="noreferrer"
                >
                  Frontend
                  <ExternalLink className="h-4 w-4" />
                </a>
                <a
                  className="underline underline-offset-4 hover:text-primary inline-flex items-center gap-1 text-sm"
                  href={BACKEND_URL}
                  target="_blank"
                  rel="noreferrer"
                >
                  Backend API
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            </aside>

            {/* Content */}
            <div className="space-y-10">
              <Section id="overview" title="Overview">
                <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
                  CRA is a modular FastAPI service with a modern React UI. It combines deterministic static analysis with optional LLM-generated suggestions and returns structured, ranked findings.
                </p>
              </Section>

              <Section id="features" title="Features">
                <ul className="list-disc pl-5 text-sm sm:text-base text-muted-foreground space-y-2">
                  <li>FastAPI backend with versioned endpoints under <code>/v2</code> (and mirrored under <code>/api/v2</code>).</li>
                  <li>Static checks (flake8 + bandit), custom rules, and ranked issues with severity + category.</li>
                  <li>Optional prompt compression via ScaleDown and optional LLM provider integration (OpenAI-compatible API).</li>
                  <li>Offline mode: disable LLM calls entirely for deterministic evaluation.</li>
                  <li>Modern, VS Code-like editor UI with tabs (new tab, close, rename, persistence).</li>
                </ul>
              </Section>

              <Section id="supported-languages" title="Supported Languages">
                <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
                  The UI supports these languages for editor highlighting and backend analysis where tools are available:
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {["Python", "JavaScript", "TypeScript", "Java", "C#", "Go", "Rust"].map((l) => (
                    <div key={l} className="rounded-xl border bg-card px-4 py-3 text-sm font-semibold">
                      {l}
                    </div>
                  ))}
                </div>
              </Section>

              <Section id="how-it-works" title="How It Works">
                <ol className="list-decimal pl-5 text-sm sm:text-base text-muted-foreground space-y-2">
                  <li>Accept code (and filename/language) from the UI or API.</li>
                  <li>Compress context to keep prompts small and relevant.</li>
                  <li>Run static analysis where applicable.</li>
                  <li>Build a structured prompt and optionally compress it via ScaleDown.</li>
                  <li>Call the LLM provider (unless offline mode), validate output, dedupe, rank, and score issues.</li>
                </ol>
              </Section>

              <Section id="architecture" title="High-Level Architecture">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  High-level pipeline overview:
                </p>
                <div className="rounded-2xl border bg-card p-4 sm:p-6">
                  <img
                    src="/architecture.png"
                    alt="CRA high-level architecture"
                    className="w-full h-auto rounded-xl border border-border/60"
                    loading="lazy"
                  />
                </div>
              </Section>

              <Section id="live-links" title="Live Deployment Links">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="rounded-2xl border bg-card p-6 space-y-2">
                    <h3 className="text-lg font-bold">Frontend (Vercel)</h3>
                    <a
                      className="underline underline-offset-4 hover:text-primary inline-flex items-center gap-1 text-sm"
                      href={FRONTEND_URL}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {FRONTEND_URL}
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>

                  <div className="rounded-2xl border bg-card p-6 space-y-2">
                    <h3 className="text-lg font-bold">Backend (Render)</h3>
                    <a
                      className="underline underline-offset-4 hover:text-primary inline-flex items-center gap-1 text-sm"
                      href={BACKEND_URL}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {BACKEND_URL}
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              </Section>

              <Section id="api-quick-start" title="API Quick Start">
                <div className="grid grid-cols-1 gap-6">
                  <CodeBlock title="Health check" value={healthCurl} label="bash" />
                  <CodeBlock title="Review code (v2 JSON)" value={reviewCurl} label="bash" />
                </div>
              </Section>

              <Section id="request-format" title="Request Format">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  The recommended endpoint for the frontend is <code>POST /v2/review/file</code>.
                </p>
                <div className="rounded-2xl border bg-card p-4 sm:p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold">Example request body</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5 font-mono uppercase tracking-wide">json</p>
                    </div>
                    <CopyButton value={requestExample} label="request json" />
                  </div>
                  <pre className="text-xs sm:text-sm overflow-auto whitespace-pre rounded-lg bg-muted/40 p-3 border font-mono leading-relaxed">
                    {requestExample}
                  </pre>
                </div>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li><code>filename</code>: used for language inference and display.</li>
                  <li><code>language</code>: language identifier (python, javascript, typescript, ...).</li>
                  <li><code>enabled_checks</code>: optional toggles (security/style/performance).</li>
                </ul>
              </Section>

              <Section id="response-format" title="Response Format">
                <div className="rounded-2xl border bg-card p-4 sm:p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold">Example response</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5 font-mono uppercase tracking-wide">json</p>
                    </div>
                    <CopyButton value={responseExample} label="response json" />
                  </div>
                  <pre className="text-xs sm:text-sm overflow-auto whitespace-pre rounded-lg bg-muted/40 p-3 border font-mono leading-relaxed">
                    {responseExample}
                  </pre>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Response includes: <code>issues[]</code>, <code>score</code> breakdown, and <code>static_analysis</code>.
                </p>
              </Section>

              <Section id="severity-levels" title="Severity Levels">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Severities are normalized to: <code>critical</code>, <code>high</code>, <code>medium</code>, <code>low</code>, <code>info</code>.
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {["critical", "high", "medium", "low", "info"].map((s) => (
                    <div key={s} className="rounded-xl border bg-card px-4 py-3 text-sm font-semibold uppercase">
                      {s}
                    </div>
                  ))}
                </div>
              </Section>

              <Section id="error-handling" title="Error Handling">
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-2">
                  <li><code>400</code> — invalid input (missing code, invalid URL, etc.).</li>
                  <li><code>422</code> — validation error from request parsing.</li>
                  <li><code>502</code> — upstream issues (LLM provider/network/runtime errors).</li>
                </ul>
              </Section>

              <Section id="configuration" title="Configuration & Environment Variables">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="rounded-2xl border bg-card p-6 space-y-3">
                    <h3 className="text-lg font-bold">Backend</h3>
                    <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                      <li><code>CODE_REVIEW_CORS_ORIGINS</code> (and optional <code>CODE_REVIEW_CORS_ORIGIN_REGEX</code>)</li>
                      <li><code>LLM_PROVIDER</code> (set <code>none</code> for offline mode)</li>
                      <li><code>LLM_API_KEY</code>, <code>LLM_BASE_URL</code>, <code>LLM_MODEL</code></li>
                      <li><code>SCALEDOWN_API_KEY</code> (optional)</li>
                    </ul>
                  </div>

                  <div className="rounded-2xl border bg-card p-6 space-y-3">
                    <h3 className="text-lg font-bold">Frontend</h3>
                    <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                      <li><code>VITE_API_BASE_URL</code> (or similar) — points to backend</li>
                    </ul>
                  </div>
                </div>
              </Section>

              <Section id="offline-mode" title="Offline Mode (No LLM)">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Set <code>LLM_PROVIDER=none</code>. The backend will still run compression + static analysis, but will not call any external LLM.
                </p>
              </Section>

              <Section id="limits" title="Limits & Constraints">
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-2">
                  <li>Large files may be truncated/compressed to fit prompt limits.</li>
                  <li>Some language-specific tools depend on the server runtime (availability varies by deployment).</li>
                  <li>Network-dependent features are disabled in offline mode.</li>
                </ul>
              </Section>

              <Section id="security-privacy" title="Security & Privacy">
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-2">
                  <li>Do not send secrets in code samples.</li>
                  <li>Never commit API keys; use environment variables.</li>
                  <li><code>/configz</code> is sanitized and never returns key values.</li>
                </ul>
              </Section>

              <Section id="roadmap" title="Roadmap">
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-2">
                  <li>Better language-specific analysis (eslint, typecheck, linters per language).</li>
                  <li>Project-level review from the UI (multi-file submissions).</li>
                  <li>Improved formatting support and editor integrations.</li>
                </ul>
              </Section>

              <Section id="versioning" title="Versioning & Changelog">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  API routes are versioned under <code>/v2</code>. The app version is exposed via the backend <code>/healthz</code> endpoint (<code>version</code> field).
                </p>
              </Section>

              <Section id="contributing" title="Contribution Guide">
                <div className="rounded-2xl border bg-card p-6 space-y-3">
                  <ol className="list-decimal pl-5 text-sm text-muted-foreground space-y-2">
                    <li>Fork the repo and create a feature branch.</li>
                    <li>Run backend tests (<code>pytest</code>) and frontend build checks.</li>
                    <li>Open a PR describing the change and how you validated it.</li>
                  </ol>
                </div>
              </Section>
            </div>
          </div>
        </div>

        {/* Back to top */}
        {showTop ? (
          <div className="fixed bottom-6 right-6 z-50">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="h-10 w-10 p-0 rounded-full shadow-lg shadow-black/5 border"
              aria-label="Back to top"
              title="Back to top"
            >
              <ArrowUp className="h-4 w-4" />
              <span className="sr-only">Back to top</span>
            </Button>
          </div>
        ) : null}
      </main>

      <AppFooter />
    </div>
  );
};

export default DocsPage;

