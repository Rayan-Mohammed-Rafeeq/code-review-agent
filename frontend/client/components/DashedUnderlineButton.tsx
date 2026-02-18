import * as React from "react";

import { cn } from "@/lib/utils";

export type DashedUnderlineButtonProps =
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    label: React.ReactNode;
  };

/**
 * Premium AI-product style button:
 * - Emerald gradient background
 * - Subtle glow
 * - Animated dashed underline on hover/focus
 */
export const DashedUnderlineButton = React.forwardRef<
  HTMLButtonElement,
  DashedUnderlineButtonProps
>(({ className, label, ...props }, ref) => {
  return (
    <button
      ref={ref}
      {...props}
      className={cn(
        "group relative inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold tracking-tight text-emerald-950",
        "bg-gradient-to-r from-emerald-300 via-emerald-400 to-emerald-200",
        "shadow-[0_8px_22px_-10px_rgba(16,185,129,0.65)]",
        "transition-all duration-300",
        "hover:brightness-[1.05] hover:shadow-[0_14px_34px_-16px_rgba(16,185,129,0.9)]",
        "active:scale-[0.98]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:opacity-60 disabled:pointer-events-none",
        className,
      )}
    >
      {/* Soft glow blob */}
      <span
        aria-hidden="true"
        className={cn(
          "pointer-events-none absolute inset-0 -z-10 rounded-xl opacity-0 blur-xl",
          "bg-[radial-gradient(circle_at_30%_30%,rgba(16,185,129,0.55),transparent_55%),radial-gradient(circle_at_70%_60%,rgba(52,211,153,0.45),transparent_50%)]",
          "transition-opacity duration-300 group-hover:opacity-100",
        )}
      />

      <span className="relative">{label}</span>

      {/* Animated dashed underline */}
      <span
        aria-hidden="true"
        className={cn(
          "pointer-events-none absolute left-4 right-4 -bottom-1.5",
          "h-[2px] border-t border-dashed border-emerald-100/70",
          "opacity-60",
          "[background-size:14px_2px]",
          // use background-image so we can animate the dash offset
          "bg-[linear-gradient(90deg,rgba(236,253,245,0.0),rgba(236,253,245,0.85),rgba(236,253,245,0.0))]",
          "bg-repeat-x",
          "transition-all duration-300",
          "group-hover:opacity-100 group-hover:translate-y-0.5",
          "group-hover:animate-[dash_0.9s_linear_infinite]",
          "group-focus-visible:opacity-100 group-focus-visible:animate-[dash_0.9s_linear_infinite]",
        )}
      />
    </button>
  );
});

DashedUnderlineButton.displayName = "DashedUnderlineButton";

