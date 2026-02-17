import { RequestHandler } from "express";
import { Issue, ReviewRequest, ReviewResponse } from "@shared/api";

export const handleReview: RequestHandler = (req, res) => {
  const { code, strict } = req.body as ReviewRequest;

  // Simple mock logic for demonstration
  let score = 92;
  const issues: Issue[] = [];

  if (code.includes('print')) {
    issues.push({
      line: code.split('\n').findIndex(l => l.includes('print')) + 1,
      category: 'Best Practice',
      severity: 'Info',
      description: 'The "print" function is used for debugging. Consider using a logging framework.',
      suggestion: 'Replace "print" with "logging.info()".'
    });
  }

  if (code.includes('/ len(')) {
    issues.push({
      line: code.split('\n').findIndex(l => l.includes('/ len(')) + 1,
      category: 'Security',
      severity: 'Critical',
      description: 'Potential division by zero if the list is empty.',
      suggestion: 'Check if the list is empty before dividing.'
    });
    score -= 15;
  }

  if (code.includes('calculate_average')) {
    issues.push({
      line: code.split('\n').findIndex(l => l.includes('def calculate_average')) + 1,
      category: 'Style',
      severity: 'Low',
      description: 'Function name is snake_case but lacks a docstring.',
      suggestion: 'Add a Google-style docstring explaining parameters and return value.'
    });
    score -= 5;
  }

  if (strict && !code.includes('typing')) {
    issues.push({
      line: 1,
      category: 'Typing',
      severity: 'Medium',
      description: 'Strict mode enabled: Type hints are missing.',
      suggestion: 'Add type hints to function signatures (e.g., numbers: list[int]).'
    });
    score -= 10;
  }

  const response: ReviewResponse = {
    score: Math.max(0, score),
    severityBreakdown: {
      Critical: issues.filter(i => i.severity === 'Critical').length,
      High: issues.filter(i => i.severity === 'High').length,
      Medium: issues.filter(i => i.severity === 'Medium').length,
      Low: issues.filter(i => i.severity === 'Low').length,
      Info: issues.filter(i => i.severity === 'Info').length,
    },
    issues,
  };

  // Simulate network delay
  res.json(response);
};
