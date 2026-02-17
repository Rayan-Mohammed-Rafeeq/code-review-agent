import * as React from 'react';
import { Issue } from '@shared/api';
import { cn } from '@/lib/utils';

interface IssueTableProps {
  issues: Issue[];
  onIssueClick: (line: number) => void;
}

export const IssueTable: React.FC<IssueTableProps> = ({ issues, onIssueClick }) => {
  const getSeverityStyles = (severity: Issue['severity']) => {
    switch (severity) {
      case 'Critical': return 'bg-score-red/20 text-score-red border-score-red/30';
      case 'High': return 'bg-orange-500/20 text-orange-500 border-orange-500/30';
      case 'Medium': return 'bg-score-yellow/20 text-score-yellow border-score-yellow/30';
      case 'Low': return 'bg-blue-500/20 text-blue-500 border-blue-500/30';
      case 'Info': return 'bg-slate-500/20 text-slate-500 border-slate-500/30';
      default: return '';
    }
  };

  return (
    <div className="w-full overflow-x-auto bg-card rounded-xl border border-border">
      <table className="w-full text-left border-collapse table-fixed">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="p-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap w-[72px]">Line</th>
            <th className="p-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap w-[160px]">Category</th>
            <th className="p-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap w-[120px]">Severity</th>
            <th className="p-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap">Description</th>
            <th className="p-4 text-xs font-semibold uppercase tracking-wider whitespace-nowrap">Suggestion</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {issues.length === 0 ? (
            <tr>
              <td colSpan={5} className="p-8 text-center text-muted-foreground italic">
                No issues found. Great job!
              </td>
            </tr>
          ) : (
            issues.map((issue, idx) => (
              <tr 
                key={idx} 
                className="hover:bg-muted/50 transition-colors cursor-pointer group"
                onClick={() => onIssueClick(issue.line)}
              >
                <td className="p-4 align-top font-mono text-sm text-muted-foreground group-hover:text-primary whitespace-nowrap">{issue.line}</td>
                <td className="p-4 align-top text-sm font-medium break-words">{issue.category}</td>
                <td className="p-4 align-top">
                  <span
                    className={cn(
                      "inline-flex items-center justify-center whitespace-nowrap",
                      "px-2.5 py-1 rounded-full border",
                      "text-[10px] font-bold uppercase leading-none",
                      getSeverityStyles(issue.severity),
                    )}
                  >
                    {issue.severity}
                  </span>
                </td>
                <td className="p-4 align-top text-sm break-words">{issue.description}</td>
                <td className="p-4 align-top text-sm text-muted-foreground italic break-words">{issue.suggestion}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};
