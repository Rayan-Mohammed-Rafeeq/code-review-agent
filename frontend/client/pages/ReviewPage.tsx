import * as React from 'react';
import { useState, useRef } from 'react';
import { CodeEditor, type EditorTab } from '@/components/Editor';
import { ScoreCard } from '@/components/ScoreCard';
import { SeverityBreakdown } from '@/components/SeverityBreakdown';
import { IssueTable } from '@/components/IssueTable';
import { ConfigPanel } from '@/components/ConfigPanel';
import { ThemeToggle } from '@/components/ThemeToggle';
import { AppFooter } from '@/components/AppFooter';
import { Button } from '@/components/ui/button';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { reviewCode } from '@/services/api';
import { ReviewResponse } from '@shared/api';
import { Loader2, Play, Search, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate, useLocation } from "react-router-dom";
import { NavUnderline } from "@/components/NavUnderline";
import { AnimatedBackground } from "@/components/AnimatedBackground";

const DEFAULT_CODE = ``;

type TabState = {
  id: string;
  name: string;
  language: string;
  code: string;
  initialCode?: string;
};

const STORAGE_KEY = 'cra.editor.tabs.v1';

function safeParseTabs(raw: string | null): { tabs: TabState[]; activeTabId: string } | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as any;
    if (!parsed || !Array.isArray(parsed.tabs) || typeof parsed.activeTabId !== 'string') return null;
    const tabs: TabState[] = parsed.tabs
      .filter((t: any) => t && typeof t.id === 'string' && typeof t.name === 'string')
      .map((t: any) => ({
        id: String(t.id),
        name: String(t.name),
        language: String(t.language || 'python'),
        code: String(t.code || ''),
        initialCode: String(t.initialCode ?? t.code ?? ''),
      }));
    if (tabs.length === 0) return null;
    const activeTabId = tabs.some((t) => t.id === parsed.activeTabId) ? parsed.activeTabId : tabs[0].id;
    return { tabs, activeTabId };
  } catch {
    return null;
  }
}

function languageFromFilename(name: string, fallback: string): string {
  const lower = (name || '').toLowerCase();
  if (lower.endsWith('.py')) return 'python';
  if (lower.endsWith('.js')) return 'javascript';
  if (lower.endsWith('.ts') || lower.endsWith('.tsx')) return 'typescript';
  if (lower.endsWith('.java')) return 'java';
  if (lower.endsWith('.cs')) return 'csharp';
  if (lower.endsWith('.go')) return 'go';
  if (lower.endsWith('.rs')) return 'rust';
  return fallback;
}

function newId() {
  return `tab-${Math.random().toString(16).slice(2)}-${Date.now().toString(16)}`;
}

const ReviewPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const goHomeOrTop = React.useCallback(() => {
    if (location.pathname === "/") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    navigate("/");
  }, [location.pathname, navigate]);

  const [tabs, setTabs] = useState<TabState[]>(() => {
    const stored = safeParseTabs(window.localStorage.getItem(STORAGE_KEY));
    if (stored) return stored.tabs;
    return [
      { id: 'tab-1', name: 'main.py', language: 'python', code: DEFAULT_CODE, initialCode: DEFAULT_CODE },
      { id: 'tab-2', name: 'utils.py', language: 'python', code: '', initialCode: '' },
    ];
  });

  const [activeTabId, setActiveTabId] = useState<string>(() => {
    const stored = safeParseTabs(window.localStorage.getItem(STORAGE_KEY));
    return stored?.activeTabId ?? 'tab-1';
  });

  // Persist tabs
  React.useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ tabs, activeTabId }));
    } catch {
      // ignore
    }
  }, [tabs, activeTabId]);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReviewResponse | null>(null);
  const [strict, setStrict] = useState(false);
  const [checks, setChecks] = useState({
    security: true,
    style: true,
    performance: true,
  });

  // Update language for the active tab (drives syntax highlighting + review request)
  const setLanguage = (nextLang: string) => {
    setTabs((prev) => prev.map((t) => (t.id === activeTabId ? { ...t, language: nextLang } : t)));
  };

  const editorRef = useRef<any>(null);

  const activeTab = React.useMemo(() => {
    return tabs.find((t) => t.id === activeTabId) ?? tabs[0];
  }, [tabs, activeTabId]);

  const code = activeTab?.code ?? '';
  const language = activeTab?.language ?? 'python';

  const updateActiveTabCode = (next: string) => {
    setTabs((prev) => prev.map((t) => (t.id === activeTabId ? { ...t, code: next } : t)));
  };

  const handleClearEditor = () => {
    updateActiveTabCode('');
    setResult(null);
    // Keep focus friendly
    try {
      editorRef.current?.focus?.();
    } catch {
      // ignore
    }
  };

  const handleReview = async () => {
    if (!code.trim()) {
      toast.error("Please enter some code to review.");
      return;
    }

    setLoading(true);
    setResult(null); // Clear previous result
    try {
      const data = await reviewCode({
        code,
        language,
        strict,
        checks,
      });
      setResult(data);
      toast.success("Code review completed successfully!");
    } catch (error) {
      console.error(error);
      toast.error("Failed to review code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleIssueClick = (line: number) => {
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(line);
      editorRef.current.setPosition({ lineNumber: line, column: 1 });
      editorRef.current.focus();
    }
  };

  const languageLabel = React.useMemo(() => {
    const map: Record<string, string> = {
      python: 'Python',
      javascript: 'JavaScript',
      typescript: 'TypeScript',
      java: 'Java',
      csharp: 'C#',
      go: 'Go',
      rust: 'Rust',
    };
    return map[(language || '').toLowerCase()] ?? (language || 'Code');
  }, [language]);

  const languageTag = React.useMemo(() => {
    const lang = (language || '').toLowerCase();
    if (lang === 'python') return 'python 3.x';
    if (lang === 'typescript') return 'ts';
    if (lang === 'javascript') return 'js';
    if (lang === 'csharp') return 'c#';
    return lang || 'code';
  }, [language]);

  const editorTabs: EditorTab[] = React.useMemo(
    () =>
      tabs.map(({ id, name, language, code, initialCode }) => ({
        id,
        name,
        language,
        isDirty: (code ?? '') !== (initialCode ?? ''),
      })),
    [tabs],
  );

  const onNewTab = () => {
    const id = newId();
    const baseLang = tabs.find((t) => t.id === activeTabId)?.language ?? 'python';
    const name = 'untitled.py';
    const language = languageFromFilename(name, baseLang);
    setTabs((prev) => [
      ...prev,
      {
        id,
        name,
        language,
        code: '',
        initialCode: '',
      },
    ]);
    setActiveTabId(id);
    setResult(null);
  };

  const onCloseTab = (id: string) => {
    setTabs((prev) => {
      if (prev.length <= 1) {
        // Keep at least one tab open
        return prev.map((t) => (t.id === id ? { ...t, code: '', initialCode: '' } : t));
      }

      const idx = prev.findIndex((t) => t.id === id);
      const nextTabs = prev.filter((t) => t.id !== id);

      if (activeTabId === id) {
        const nextActive = nextTabs[Math.max(0, idx - 1)]?.id ?? nextTabs[0].id;
        setActiveTabId(nextActive);
      }

      return nextTabs;
    });
    setResult(null);
  };

  const onRenameTab = (id: string, newName: string) => {
    setTabs((prev) =>
      prev.map((t) => {
        if (t.id !== id) return t;
        const nextLang = languageFromFilename(newName, t.language);
        return { ...t, name: newName, language: nextLang };
      }),
    );
  };

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="min-h-screen w-full bg-background text-foreground flex flex-col relative">
        <AnimatedBackground />
        {/* Header */}
        <header className="w-full sticky top-0 z-50 bg-header-bg text-header-fg">
          {/* subtle bottom border + accent fade to separate header from content */}
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
              </div>
              <div className="flex items-center gap-2 sm:gap-4">
                <Button
                  variant="ghost"
                  size="sm"
                  className="group relative text-header-muted hover:text-header-fg focus-visible:ring-2 focus-visible:ring-header-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-header-bg"
                  onClick={() => navigate("/docs")}
                >
                  Docs
                  <NavUnderline />
                </Button>
                <ThemeToggle />
              </div>
            </div>
          </div>
        </header>

        <SidebarInset className="flex-1 relative">
          <main className="w-full flex-1 px-4 pt-8 pb-20">
            <div className="container mx-auto max-w-7xl">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Left Column: Editor & Main Actions */}
                <div className="lg:col-span-3 space-y-6">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-4">
                      <h2 className="text-lg font-bold">{languageLabel} Source Code</h2>
                      <div className="flex gap-2">
                         <span className="px-2 py-0.5 bg-muted rounded text-[10px] font-mono text-muted-foreground uppercase">{languageTag}</span>
                         <span className="px-2 py-0.5 bg-muted rounded text-[10px] font-mono text-muted-foreground uppercase">utf-8</span>
                      </div>
                    </div>
                  </div>

                  <CodeEditor
                    code={code}
                    language={language}
                    onChange={(val) => updateActiveTabCode(val || '')}
                    editorRef={editorRef}
                    onClear={handleClearEditor}
                    tabs={editorTabs}
                    activeTabId={activeTabId}
                    onTabChange={(id) => setActiveTabId(id)}
                    onTabRename={onRenameTab}
                    onTabClose={onCloseTab}
                    onNewTab={onNewTab}
                  />

                  <div className="flex justify-end pt-2 gap-3 flex-wrap">
                    <Button
                      onClick={handleReview}
                      disabled={loading}
                      className="h-12 px-8 text-base font-black gap-2 shadow-xl shadow-primary/30 bg-gradient-to-r from-primary to-accent hover:brightness-110 border-0 transition-all active:scale-95"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Analyzing Code...
                        </>
                      ) : (
                        <>
                          <Play className="w-5 h-5 fill-current" />
                          Analyze Code
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Dashboard Section (after response) */}
                  {result ? (
                    <div className="pt-12 space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
                      <div className="space-y-4">
                        <h2 className="text-2xl font-bold flex items-center gap-2">
                          <Search className="w-6 h-6 text-primary" />
                          Review Analysis
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          <div className="md:col-span-1">
                            <ScoreCard score={result.score} />
                          </div>
                          <div className="md:col-span-2">
                            <SeverityBreakdown breakdown={result.severityBreakdown} />
                          </div>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h3 className="text-xl font-bold">Issues & Suggestions</h3>
                        <IssueTable issues={result.issues} onIssueClick={handleIssueClick} />
                      </div>
                    </div>
                  ) : !loading && (
                    <div className="pt-20 flex flex-col items-center justify-center text-center space-y-4 opacity-40">
                      <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center border-2 border-primary/20">
                        <Play className="w-10 h-10 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold">Ready for Analysis</h3>
                        <p className="text-sm">Click "Analyze Code" to start the AI-powered review.</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Column: Configuration */}
                <div className="space-y-6">
                  <h2 className="text-lg font-bold mb-2">Configuration</h2>
                  <ConfigPanel
                    language={language}
                    setLanguage={setLanguage}
                    strict={strict}
                    setStrict={setStrict}
                    checks={checks}
                    setChecks={setChecks}
                  />

                  <div className="bg-gradient-to-br from-primary/10 to-accent/10 border border-primary/20 p-6 rounded-xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-primary/10 rounded-full -mr-12 -mt-12 blur-2xl group-hover:bg-accent/20 transition-colors" />
                    <h4 className="font-bold text-sm mb-2 text-primary flex items-center gap-2">
                      <Zap className="w-4 h-4 fill-current" />
                      Pro Tip
                    </h4>
                    <p className="text-xs text-muted-foreground leading-relaxed relative z-10">
                      Enable "Strict Mode" to catch micro-optimizations and subtle edge cases that might affect long-term maintainability.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </main>
        </SidebarInset>

        <AppFooter />
      </div>
    </SidebarProvider>
  );
};

export default ReviewPage;
