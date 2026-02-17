import * as React from 'react';
import { useState, useRef } from 'react';
import { CodeEditor } from '@/components/Editor';
import { ScoreCard } from '@/components/ScoreCard';
import { SeverityBreakdown } from '@/components/SeverityBreakdown';
import { IssueTable } from '@/components/IssueTable';
import { ConfigPanel } from '@/components/ConfigPanel';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Button } from '@/components/ui/button';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { reviewCode } from '@/services/api';
import { ReviewResponse } from '@shared/api';
import { Loader2, Play, Search, Zap } from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_CODE = ``;

const ReviewPage = () => {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [language, setLanguage] = useState('python');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReviewResponse | null>(null);
  const [strict, setStrict] = useState(false);
  const [checks, setChecks] = useState({
    security: true,
    style: true,
    performance: true,
  });
  
  const editorRef = useRef<any>(null);

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

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="min-h-screen w-full bg-background text-foreground flex flex-col">
        {/* Header */}
        <header className="w-full border-b border-border bg-card/70 backdrop-blur-md sticky top-0 z-50">
          <div className="w-full px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 flex items-center justify-center overflow-hidden rounded-md bg-muted/40">
                <img
                  src="/logo.png"
                  alt="Code Review Agent Logo"
                  className="w-full h-full object-contain"
                />
              </div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight uppercase bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent truncate">
                Code Review Agent
              </h1>
            </div>
            <div className="flex items-center gap-2 sm:gap-4">
              <Button variant="ghost" size="sm" className="hover:bg-accent/60">Docs</Button>
              <Button variant="ghost" size="sm" className="hover:bg-accent/60">History</Button>
              <ThemeToggle />
            </div>
          </div>
        </header>

        <SidebarInset className="flex-1">
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
                    onChange={(val) => setCode(val || '')}
                    editorRef={editorRef}
                  />

                  <div className="flex justify-end pt-2">
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
      </div>
    </SidebarProvider>
  );
};

export default ReviewPage;
