import * as React from 'react';
import Editor from '@monaco-editor/react';
import { useTheme } from '@/hooks/use-theme';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Check, Clipboard, Eraser, Pencil, Plus, X } from 'lucide-react';

export type EditorTab = {
  id: string;
  name: string;
  language: string;
  isDirty?: boolean;
};

interface CodeEditorProps {
  code: string;
  language: string;
  onChange: (value: string | undefined) => void;
  editorRef: React.MutableRefObject<any>;
  onClear?: () => void;

  /** Optional: show VS Code-like file tabs in the header */
  tabs?: EditorTab[];
  activeTabId?: string;
  onTabChange?: (tabId: string) => void;
  onTabRename?: (tabId: string, newName: string) => void;
  onTabClose?: (tabId: string) => void;
  onNewTab?: () => void;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  code,
  language,
  onChange,
  editorRef,
  onClear,
  tabs,
  activeTabId,
  onTabChange,
  onTabRename,
  onTabClose,
  onNewTab,
}) => {
  const { theme } = useTheme();
  const [isFocused, setIsFocused] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [renamingId, setRenamingId] = React.useState<string | null>(null);
  const renameInputRef = React.useRef<HTMLInputElement | null>(null);

  const activeTab = React.useMemo(() => {
    if (!tabs || tabs.length === 0) return null;
    return tabs.find((t) => t.id === activeTabId) ?? tabs[0];
  }, [tabs, activeTabId]);

  const effectiveLanguage = activeTab?.language ?? language;

  const resolvedLanguage = React.useMemo(() => {
    const lang = (effectiveLanguage || '').toLowerCase();
    if (lang === 'csharp') return 'csharp';
    return lang || 'plaintext';
  }, [effectiveLanguage]);

  const canAct = (code || '').trim().length > 0;

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;

    // Keep Monaco theme aligned with Tailwind's theme.
    // (We still use vs/vs-dark, but set some cosmetic editor colors.)
    try {
      const isDark = theme === 'dark';
      monaco?.editor?.defineTheme('premium-vs', {
        base: 'vs',
        inherit: true,
        rules: [],
        colors: {
          'editor.background': '#F6F7F9',
          'editorLineNumber.foreground': '#9AA4B2',
          'editorLineNumber.activeForeground': '#475569',
          'editorCursor.foreground': '#0EA5E9',
          'editor.selectionBackground': '#BAE6FD',
          'editor.inactiveSelectionBackground': '#E0F2FE',
        },
      });
      monaco?.editor?.defineTheme('premium-vs-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [],
        colors: {
          'editor.background': '#0B1220',
          'editorLineNumber.foreground': '#5B6B86',
          'editorLineNumber.activeForeground': '#E2E8F0',
          'editorCursor.foreground': '#22C55E',
          'editor.selectionBackground': '#0F2A3F',
          'editor.inactiveSelectionBackground': '#0D2234',
        },
      });

      monaco?.editor?.setTheme(isDark ? 'premium-vs-dark' : 'premium-vs');
    } catch {
      // ignore
    }

    editor.onDidFocusEditorText(() => setIsFocused(true));
    editor.onDidBlurEditorText(() => setIsFocused(false));
  };

  React.useEffect(() => {
    try {
      const anyWindow = window as any;
      const monaco = anyWindow?.monaco;
      if (monaco?.editor?.setTheme) {
        monaco.editor.setTheme(theme === 'dark' ? 'premium-vs-dark' : 'premium-vs');
      }
    } catch {
      // ignore
    }
  }, [theme]);

  React.useEffect(() => {
    if (!renamingId) return;
    window.setTimeout(() => renameInputRef.current?.focus(), 0);
  }, [renamingId]);

  const handleCopy = async () => {
    if (!canAct) return;
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 900);
    } catch {
      // ignore
    }
  };

  const activeId = activeTab?.id;

  const submitRename = (tabId: string, raw: string) => {
    const next = raw.trim();
    setRenamingId(null);
    if (!next) return;
    onTabRename?.(tabId, next);
  };

  return (
    <TooltipProvider>
      <div
        className={
          "group w-full overflow-hidden rounded-2xl border bg-card/40 backdrop-blur transition-all duration-300 " +
          "border-border/70 " +
          "shadow-[0_20px_45px_-35px_rgba(2,8,23,0.35)] dark:shadow-none " +
          "dark:bg-[#0B1220]/65 dark:border-emerald-500/10 " +
          (isFocused
            ? " ring-2 ring-ring/40 dark:ring-2 dark:ring-emerald-400/25 "
            : "") +
          " dark:shadow-[0_0_0_1px_rgba(16,185,129,0.15),0_30px_80px_-60px_rgba(16,185,129,0.35)]"
        }
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-3 sm:px-4 py-2.5 border-b border-border/60 dark:border-emerald-500/10 bg-muted/30 dark:bg-[#0A1020]/70 transition-colors">
          <div className="flex items-center gap-3 min-w-0">
            {/* Mac-style window dots */}
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="h-2.5 w-2.5 rounded-full bg-[#FF5F57] shadow-[0_0_0_1px_rgba(0,0,0,0.08)]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#FFBD2E] shadow-[0_0_0_1px_rgba(0,0,0,0.08)]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#28C840] shadow-[0_0_0_1px_rgba(0,0,0,0.08)]" />
            </div>

            {/* Tabs */}
            {tabs && tabs.length > 0 ? (
              <div className="min-w-0 flex items-center gap-1 overflow-x-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
                {tabs.map((t) => {
                  const isActive = t.id === activeId;
                  const isRenaming = renamingId === t.id;
                  const isDirty = Boolean(t.isDirty);
                  return (
                    <div
                      key={t.id}
                      className={
                        "relative flex items-center gap-2 rounded-md px-2.5 py-1 text-xs sm:text-sm transition-colors cursor-pointer select-none " +
                        (isActive
                          ? "bg-background/70 text-foreground shadow-sm dark:bg-white/5"
                          : "text-muted-foreground hover:bg-background/40 dark:hover:bg-white/5")
                      }
                      onClick={() => onTabChange?.(t.id)}
                      onDoubleClick={() => (onTabRename ? setRenamingId(t.id) : null)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') onTabChange?.(t.id);
                        if (e.key === 'F2' && onTabRename) setRenamingId(t.id);
                      }}
                    >
                      {/* Dirty dot */}
                      <span
                        className={
                          "h-1.5 w-1.5 rounded-full transition-opacity " +
                          (isDirty ? "opacity-100 bg-foreground/70 dark:bg-emerald-300/80" : "opacity-0")
                        }
                        aria-hidden="true"
                      />

                      {isRenaming ? (
                        <input
                          ref={renameInputRef}
                          defaultValue={t.name}
                          className="w-28 sm:w-40 bg-transparent border border-border/60 dark:border-emerald-500/10 rounded px-1.5 py-0.5 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-ring/40 dark:focus:ring-emerald-400/25"
                          onBlur={(e) => submitRename(t.id, e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') submitRename(t.id, (e.target as HTMLInputElement).value);
                            if (e.key === 'Escape') setRenamingId(null);
                          }}
                        />
                      ) : (
                        <span className="max-w-[9rem] sm:max-w-[14rem] truncate font-medium">{t.name}</span>
                      )}

                      {isActive && (
                        <Badge
                          variant="secondary"
                          className="hidden sm:inline-flex rounded-md px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide text-muted-foreground bg-background/60 dark:bg-white/5 dark:text-slate-200/80 border border-border/50"
                        >
                          {resolvedLanguage}
                        </Badge>
                      )}

                      {onTabRename && !isRenaming && isActive && (
                        <button
                          type="button"
                          className="ml-0.5 inline-flex items-center justify-center text-muted-foreground/70 hover:text-foreground transition-colors"
                          onClick={(e) => {
                            e.stopPropagation();
                            setRenamingId(t.id);
                          }}
                          aria-label="Rename tab"
                        >
                          <Pencil className="size-3.5" />
                        </button>
                      )}

                      {onTabClose && (
                        <button
                          type="button"
                          className={
                            "ml-0.5 inline-flex items-center justify-center rounded-sm p-0.5 transition-colors " +
                            "text-muted-foreground/70 hover:text-foreground hover:bg-background/40 dark:hover:bg-white/5"
                          }
                          onClick={(e) => {
                            e.stopPropagation();
                            onTabClose(t.id);
                          }}
                          aria-label={`Close ${t.name}`}
                        >
                          <X className="size-3.5" />
                        </button>
                      )}
                    </div>
                  );
                })}

                {onNewTab && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={onNewTab}
                        className="h-7 w-7 rounded-md text-muted-foreground hover:text-foreground hover:bg-background/40 dark:hover:bg-white/5"
                        aria-label="New tab"
                      >
                        <Plus className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>New tab</TooltipContent>
                  </Tooltip>
                )}
              </div>
            ) : (
              // Fallback: single-file header
              <div className="min-w-0 flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground/90 truncate">Untitled</span>
                <Badge
                  variant="secondary"
                  className="rounded-md px-2 py-0.5 text-[10px] font-mono uppercase tracking-wide text-muted-foreground bg-background/60 dark:bg-white/5 dark:text-slate-200/80 border border-border/50"
                >
                  {resolvedLanguage}
                </Badge>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  disabled={!canAct}
                  className="h-9 px-2.5 rounded-md transition-colors"
                >
                  {copied ? <Check className="size-4" /> : <Clipboard className="size-4" />}
                  <span className="hidden sm:inline text-xs">Copy</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Copy to clipboard</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={onClear}
                  disabled={!canAct || !onClear}
                  className="h-9 px-2.5 rounded-md transition-colors"
                >
                  <Eraser className="size-4" />
                  <span className="hidden sm:inline text-xs">Clear</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Clear editor</TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Editor Body */}
        <div className="relative w-full h-[350px] md:h-[500px]">
          <Editor
            height="100%"
            defaultLanguage={resolvedLanguage}
            language={resolvedLanguage}
            theme={theme === 'dark' ? 'premium-vs-dark' : 'premium-vs'}
            value={code}
            onChange={onChange}
            onMount={handleEditorDidMount}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineHeight: 22,
              fontFamily:
                'JetBrains Mono, Fira Code, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace',
              fontLigatures: true,
              lineNumbers: 'on',
              lineNumbersMinChars: 4,
              renderLineHighlight: 'line',
              cursorBlinking: 'smooth',
              cursorSmoothCaretAnimation: 'on',
              smoothScrolling: true,
              scrollBeyondLastLine: false,
              automaticLayout: true,
              padding: { top: 16, bottom: 16 },
              scrollbar: {
                verticalScrollbarSize: 10,
                horizontalScrollbarSize: 10,
              },
              overviewRulerBorder: false,
              hideCursorInOverviewRuler: true,
              renderValidationDecorations: 'on',
              guides: {
                indentation: true,
              },
            }}
          />
        </div>
      </div>
    </TooltipProvider>
  );
};
