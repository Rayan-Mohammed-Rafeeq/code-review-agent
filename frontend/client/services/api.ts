import axios from 'axios';
import { ReviewRequest, ReviewResponse } from '@shared/api';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

type V2Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

type V2Issue = {
  file: string;
  line: number;
  category: string;
  severity: V2Severity;
  description: string;
  suggestion: string;
  source: string;
};

type V2ReviewResult = {
  issues: V2Issue[];
  score: {
    score: number;
    counts_by_severity: Record<V2Severity, number>;
  };
  static_analysis: Record<string, unknown>;
};

function toUiSeverity(sev: V2Severity): ReviewResponse['issues'][number]['severity'] {
  if (sev === 'critical') return 'Critical';
  if (sev === 'high') return 'High';
  if (sev === 'medium') return 'Medium';
  if (sev === 'info') return 'Info';
  return 'Low';
}

function breakdownFromCounts(counts: Record<string, number> | undefined): ReviewResponse['severityBreakdown'] {
  return {
    Critical: counts?.critical ?? 0,
    High: counts?.high ?? 0,
    Medium: counts?.medium ?? 0,
    Low: counts?.low ?? 0,
    Info: counts?.info ?? 0,
  };
}

export const reviewCode = async (data: ReviewRequest): Promise<ReviewResponse> => {
  // Map the UI request to v2 backend request.
  const lang = data.language;
  const extByLang: Record<string, string> = {
    python: 'py',
    javascript: 'js',
    typescript: 'ts',
    java: 'java',
    csharp: 'cs',
    'c#': 'cs',
    go: 'go',
    rust: 'rs',
  };

  const ext = extByLang[lang] ?? lang;
  const filename = lang === 'python' ? 'input.py' : `input.${ext}`;

  const response = await apiClient.post<V2ReviewResult>(
    '/v2/review/file',
    {
      filename,
      code: data.code,
      language: data.language,
      enabled_checks: data.checks,
    },
    {
      params: { strict: Boolean(data.strict) },
    },
  );

  const backend = response.data;

  return {
    score: backend.score?.score ?? 0,
    severityBreakdown: breakdownFromCounts(backend.score?.counts_by_severity),
    issues: (backend.issues || []).map((it) => ({
      line: it.line,
      category: it.category,
      severity: toUiSeverity(it.severity),
      description: it.description,
      suggestion: it.suggestion,
    })),
  };
};

export type FormatResponse = {
  code: string;
  formatter: string;
  changed: boolean;
};

export const formatCode = async (params: {
  code: string;
  language?: string;
  filename?: string;
}): Promise<FormatResponse> => {
  const response = await apiClient.post<FormatResponse>('/v2/format', {
    code: params.code,
    language: params.language,
    filename: params.filename,
  });
  return response.data;
};
