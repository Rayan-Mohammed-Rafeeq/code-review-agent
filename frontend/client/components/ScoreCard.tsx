import * as React from 'react';
import { cn } from '@/lib/utils';

interface ScoreCardProps {
  score: number;
}

export const ScoreCard: React.FC<ScoreCardProps> = ({ score }) => {
  const getScoreColor = (s: number) => {
    if (s >= 80) return 'text-score-green border-score-green';
    if (s >= 50) return 'text-score-yellow border-score-yellow';
    return 'text-score-red border-score-red';
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-card rounded-xl border border-border h-full">
      <h3 className="text-muted-foreground text-sm font-semibold mb-2 uppercase tracking-wider">Code Quality Score</h3>
      <div className={cn(
        "text-6xl font-extrabold flex items-center justify-center rounded-full border-4 w-32 h-32",
        getScoreColor(score)
      )}>
        {score}
      </div>
    </div>
  );
};
