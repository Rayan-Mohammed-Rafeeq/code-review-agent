import * as React from 'react';
import { ReviewResponse } from '@shared/api';

interface SeverityBreakdownProps {
  breakdown: ReviewResponse['severityBreakdown'];
}

export const SeverityBreakdown: React.FC<SeverityBreakdownProps> = ({ breakdown }) => {
  const severities = [
    { label: 'Critical', value: breakdown.Critical, color: 'bg-score-red' },
    { label: 'High', value: breakdown.High, color: 'bg-orange-500' },
    { label: 'Medium', value: breakdown.Medium, color: 'bg-score-yellow' },
    { label: 'Low', value: breakdown.Low, color: 'bg-primary' },
    { label: 'Info', value: breakdown.Info, color: 'bg-slate-500' },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 bg-card p-6 rounded-xl border border-border">
      {severities.map((sev) => (
        <div key={sev.label} className="flex flex-col items-center">
          <span className="text-xs text-muted-foreground font-medium mb-1 uppercase">{sev.label}</span>
          <span className="text-2xl font-bold">{sev.value}</span>
          <div className={`h-1.5 w-full mt-2 rounded-full ${sev.color}`} />
        </div>
      ))}
    </div>
  );
};
