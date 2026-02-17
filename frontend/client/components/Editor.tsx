import * as React from 'react';
import Editor from '@monaco-editor/react';
import { useTheme } from '@/hooks/use-theme';

interface CodeEditorProps {
  code: string;
  language: string;
  onChange: (value: string | undefined) => void;
  editorRef: React.MutableRefObject<any>;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({ code, language, onChange, editorRef }) => {
  const { theme } = useTheme();

  const resolvedLanguage = React.useMemo(() => {
    const lang = (language || '').toLowerCase();
    if (lang === 'csharp') return 'csharp';
    return lang || 'plaintext';
  }, [language]);

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor;
  };

  return (
    <div className="w-full h-[350px] md:h-[500px] border border-primary/20 rounded-xl overflow-hidden shadow-2xl shadow-primary/5">
      <Editor
        height="100%"
        defaultLanguage={resolvedLanguage}
        language={resolvedLanguage}
        theme={theme === "dark" ? "vs-dark" : "vs"}
        value={code}
        onChange={onChange}
        onMount={handleEditorDidMount}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          padding: { top: 16, bottom: 16 },
        }}
      />
    </div>
  );
};
