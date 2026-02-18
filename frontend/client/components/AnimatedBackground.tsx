import * as React from "react";

import { cn } from "@/lib/utils";

type AnimatedBackgroundProps = {
  className?: string;
};

/**
 * Subtle premium animated background:
 * - gradient glow blobs
 * - animated grid drift
 * - optional noise overlay
 *
 * Designed to be low-contrast and not fight content readability.
 */
export const AnimatedBackground = ({ className }: AnimatedBackgroundProps) => {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden",
        // Fade the effect near the bottom so footer stays crisp
        "[mask-image:linear-gradient(to_bottom,black_0%,black_78%,transparent_100%)]",
        className,
      )}
    >
      {/* Glow blobs */}
      <div className="absolute -top-40 -right-40 h-[520px] w-[520px] rounded-full bg-emerald-400/10 blur-3xl animate-[float_10s_ease-in-out_infinite]" />
      <div className="absolute -bottom-48 -left-48 h-[620px] w-[620px] rounded-full bg-cyan-400/10 blur-3xl animate-[float_12s_ease-in-out_infinite_reverse]" />
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 h-[520px] w-[520px] rounded-full bg-blue-400/6 blur-3xl animate-[float_14s_ease-in-out_infinite]" />

      {/* Grid */}
      <div
        className={cn(
          "absolute inset-0 opacity-25",
          "bg-[linear-gradient(to_right,rgba(148,163,184,0.14)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.14)_1px,transparent_1px)]",
          "[background-size:64px_64px]",
          "mask-image:radial-gradient(ellipse_at_center,black_55%,transparent_75%)",
          "animate-[grid-drift_18s_linear_infinite]",
        )}
      />

      {/* Noise overlay */}
      <div className="absolute inset-0 opacity-[0.06] mix-blend-overlay bg-[url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22400%22%3E%3Cfilter id=%22n%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22400%22 height=%22400%22 filter=%22url(%23n)%22 opacity=%220.25%22/%3E%3C/svg%3E')]" />

      {/* Vignette */}
      <div className="absolute inset-0 bg-gradient-to-b from-background/40 via-transparent to-background" />
    </div>
  );
};

