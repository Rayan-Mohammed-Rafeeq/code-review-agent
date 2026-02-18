import {
  APP_NAME,
  APP_TAGLINE,
  APP_VERSION,
  DEFAULT_GITHUB_URL,
  DEFAULT_LINKEDIN_URL,
  DEVELOPER_AVATAR_SRC,
  DEVELOPER_NAME,
} from "@/config/appInfo";
import * as React from "react";
import { useLocation, useNavigate } from "react-router-dom";

type AppFooterProps = {
  githubUrl?: string;
  linkedinUrl?: string;
};

const linkClassName =
  "text-sm text-footer-muted hover:text-footer-fg underline-offset-4 hover:underline transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-footer-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-footer-bg rounded-sm";

const iconLinkClassName =
  "btn-shine group inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-footer-muted hover:text-footer-fg bg-white/0 hover:bg-accent/60 transition-all duration-200 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-footer-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-footer-bg";

const iconWrapClassName =
  "grid place-items-center h-9 w-9 rounded-lg border border-footer-border bg-white/5 text-footer-muted group-hover:text-footer-fg group-hover:border-white/20 transition-colors";

const GitHubMark = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className="h-4 w-4"
    fill="currentColor"
  >
    <path d="M12 .5C5.73.5.75 5.62.75 12c0 5.1 3.29 9.42 7.86 10.95.58.11.79-.26.79-.57v-2.09c-3.2.71-3.87-1.58-3.87-1.58-.52-1.36-1.28-1.73-1.28-1.73-1.04-.73.08-.72.08-.72 1.15.08 1.75 1.21 1.75 1.21 1.02 1.77 2.67 1.26 3.32.96.1-.76.4-1.26.72-1.55-2.55-.3-5.24-1.3-5.24-5.78 0-1.28.45-2.33 1.19-3.15-.12-.3-.52-1.52.11-3.17 0 0 .97-.32 3.18 1.2a10.8 10.8 0 0 1 2.9-.4c.98 0 1.97.14 2.9.4 2.21-1.52 3.18-1.2 3.18-1.2.63 1.65.23 2.87.11 3.17.74.82 1.19 1.87 1.19 3.15 0 4.49-2.7 5.48-5.27 5.77.41.36.78 1.08.78 2.17v3.22c0 .31.21.69.79.57A11.28 11.28 0 0 0 23.25 12C23.25 5.62 18.27.5 12 .5Z" />
  </svg>
);

const LinkedInMark = () => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className="h-4 w-4"
    fill="currentColor"
  >
    <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.95v5.66H9.35V9h3.41v1.56h.05c.48-.9 1.66-1.85 3.41-1.85 3.64 0 4.31 2.4 4.31 5.51v6.23ZM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12ZM7.12 20.45H3.56V9h3.56v11.45Z" />
  </svg>
);

export const AppFooter = ({
  githubUrl = DEFAULT_GITHUB_URL,
  linkedinUrl = DEFAULT_LINKEDIN_URL,
}: AppFooterProps) => {
  const navigate = useNavigate();
  const location = useLocation();

  const goHomeOrTop = React.useCallback(() => {
    if (location.pathname === "/") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    navigate("/");
  }, [location.pathname, navigate]);

  return (
    <footer className="relative z-10 w-full bg-footer-bg text-footer-fg">
      {/* smooth transition from page content */}
      <div className="pointer-events-none absolute inset-x-0 -top-6 h-6 bg-gradient-to-b from-background/0 via-footer-bg/40 to-footer-bg" />

      <div className="border-t border-footer-border">
        {/* subtle brand accent line */}
        <div className="h-px w-full bg-gradient-to-r from-transparent via-footer-accent-blue/50 to-transparent" />

        <div className="container mx-auto max-w-6xl px-4 py-10">
          <div className="grid grid-cols-1 gap-10 md:grid-cols-3">
            {/* Column 1: Brand */}
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={goHomeOrTop}
                  className="group inline-flex items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-footer-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-footer-bg"
                  aria-label="Go to home"
                  title="Home"
                >
                  <img
                    src="/logo.png"
                    alt="CRA Logo"
                    width={32}
                    height={32}
                    loading="lazy"
                    className="h-8 w-8 object-contain"
                  />
                </button>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold tracking-tight">
                    {APP_NAME}
                  </p>
                  <p className="text-xs text-footer-muted">
                    v{APP_VERSION}
                  </p>
                </div>
              </div>

              <p className="max-w-sm text-sm leading-relaxed text-footer-muted">
                {APP_TAGLINE}
              </p>

              <p className="text-xs text-footer-muted">
                © {new Date().getFullYear()} · Built with FastAPI + React
              </p>
            </div>

            {/* Column 2: Product */}
            <div className="space-y-3">
              <p className="text-sm font-semibold">Product</p>
              <ul className="space-y-2">
                <li>
                  <a href="/" className={linkClassName}>
                    Code Review
                  </a>
                </li>
                <li>
                  <a href="/docs" className={linkClassName}>
                    Documentation
                  </a>
                </li>
                <li>
                  <a
                    href="https://code-review-agent-api.onrender.com/docs"
                    target="_blank"
                    rel="noreferrer"
                    className={linkClassName}
                  >
                    API Swagger
                  </a>
                </li>
              </ul>
            </div>

            {/* Column 3: Social */}
            <div className="space-y-4 md:justify-self-end">
              <div className="space-y-3">
                <p className="text-sm font-semibold">Connect</p>

                <div className="flex flex-wrap gap-2">
                  <a
                    href={githubUrl}
                    target="_blank"
                    rel="noreferrer"
                    className={iconLinkClassName}
                  >
                    <span className={iconWrapClassName}>
                      <GitHubMark />
                    </span>
                    <span>GitHub</span>
                  </a>

                  <a
                    href={linkedinUrl}
                    target="_blank"
                    rel="noreferrer"
                    className={iconLinkClassName}
                  >
                    <span className={iconWrapClassName}>
                      <LinkedInMark />
                    </span>
                    <span>LinkedIn</span>
                  </a>
                </div>
              </div>

              {/* Developer card */}
              <div className="flex items-center gap-3 rounded-2xl border border-footer-border bg-white/5 px-4 py-3">
                <img
                  src={DEVELOPER_AVATAR_SRC}
                  alt={DEVELOPER_NAME}
                  width={36}
                  height={36}
                  loading="lazy"
                  className="h-9 w-9 rounded-full border border-white/10 bg-white/5 object-cover"
                />
                <div className="leading-tight">
                  <p className="text-sm font-medium">{DEVELOPER_NAME}</p>
                  <p className="text-xs text-footer-muted">Developer</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
