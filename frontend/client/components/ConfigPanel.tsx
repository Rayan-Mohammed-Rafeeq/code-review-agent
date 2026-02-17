import * as React from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface ConfigPanelProps {
  language: string;
  setLanguage: (val: string) => void;
  strict: boolean;
  setStrict: (val: boolean) => void;
  checks: {
    security: boolean;
    style: boolean;
    performance: boolean;
  };
  setChecks: (checks: any) => void;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({ 
  language,
  setLanguage,
  strict,
  setStrict, 
  checks, 
  setChecks 
}) => {
  const toggleCheck = (key: keyof typeof checks) => {
    setChecks({ ...checks, [key]: !checks[key] });
  };

  return (
    <div className="bg-card p-6 rounded-xl border border-border flex flex-col gap-6">
      <div className="space-y-2">
        <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Language</Label>
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select language" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="python">Python</SelectItem>
            <SelectItem value="javascript">JavaScript</SelectItem>
            <SelectItem value="typescript">TypeScript</SelectItem>
            <SelectItem value="java">Java</SelectItem>
            <SelectItem value="csharp">C#</SelectItem>
            <SelectItem value="go">Go</SelectItem>
            <SelectItem value="rust">Rust</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">Select the language for syntax highlighting and review rules.</p>
      </div>

      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label htmlFor="strict-mode" className="text-base font-bold">Strict Mode</Label>
          <p className="text-xs text-muted-foreground">Enforce rigorous coding standards</p>
        </div>
        <Switch 
          id="strict-mode" 
          checked={strict} 
          onCheckedChange={setStrict} 
        />
      </div>

      <div className="border-t border-border pt-4 space-y-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Enabled Checks</h4>
        
        <div className="flex items-center justify-between">
          <Label htmlFor="security-check" className="text-sm">Security Vulnerabilities</Label>
          <Switch 
            id="security-check" 
            checked={checks.security} 
            onCheckedChange={() => toggleCheck('security')} 
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="style-check" className="text-sm">Style & Formatting</Label>
          <Switch 
            id="style-check" 
            checked={checks.style} 
            onCheckedChange={() => toggleCheck('style')} 
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="performance-check" className="text-sm">Performance Optimization</Label>
          <Switch 
            id="performance-check" 
            checked={checks.performance} 
            onCheckedChange={() => toggleCheck('performance')} 
          />
        </div>
      </div>
    </div>
  );
};
