/**
 * Shared code between client and server
 * Useful to share types between client and server
 * and/or small pure JS functions that can be used on both client and server
 */

export type BackendSeverity = 'Critical' | 'High' | 'Medium' | 'Low' | 'Info';
export type BackendCategory = string;

export interface BackendIssue {
  // v2 pipeline shape
  file?: string;
  line?: number;
  source?: string;

  // normalized/classic fields
  severity: BackendSeverity;
  category: BackendCategory;
  description: string;
  suggestion: string;

  // backend may include a string location instead of line
  location?: string | null;
  metadata?: Record<string, unknown>;
}

export interface BackendReviewRequest {
  code: string;
  language?: string;
  filename?: string;
  strict?: boolean;

  // UI configuration gets mapped to v2 enabled_checks
  checks?: Record<string, boolean>;
}

export interface SeverityBreakdown {
  Critical: number;
  High: number;
  Medium: number;
  Low: number;
  Info: number;
}

export interface BackendReviewResponse {
  // fields returned by the Python backend (v1)
  compressed_context?: string;
  static_analysis?: Record<string, unknown>;
  strict_findings?: string | null;

  // fields used by the React UI (v2 adapter)
  score: number;
  severityBreakdown: SeverityBreakdown;
  issues: BackendIssue[];
}

// Public aliases used throughout the app.
export type Issue = BackendIssue;
export type ReviewRequest = BackendReviewRequest;
export type ReviewResponse = BackendReviewResponse;

// NOTE: The aliases above are referenced from both client and server layers.
