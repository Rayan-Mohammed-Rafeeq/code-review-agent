import * as React from "react";

import { cn } from "@/lib/utils";

export type NavUnderlineProps = {
  className?: string;
};

/**
 * Subtle dashed underline used for nav buttons.
 * Animates on hover/focus using the global `dash` keyframes.
 */
export const NavUnderline = ({ className }: NavUnderlineProps) => (
  <span
    aria-hidden="true"
    className={cn(
      "pointer-events-none absolute left-2 right-2 -bottom-1.5",
      "h-[2px] border-t border-dashed border-foreground/20",
      "opacity-0",
      "bg-[linear-gradient(90deg,transparent,theme(colors.header.accent-blue),theme(colors.header.accent-emerald),transparent)]",
      "bg-repeat-x [background-size:14px_2px]",
      "transition-all duration-200",
      "group-hover:opacity-100 group-hover:translate-y-0.5 group-hover:animate-[dash_0.9s_linear_infinite]",
      "group-focus-visible:opacity-100 group-focus-visible:translate-y-0.5 group-focus-visible:animate-[dash_0.9s_linear_infinite]",
      className,
    )}
  />
);
