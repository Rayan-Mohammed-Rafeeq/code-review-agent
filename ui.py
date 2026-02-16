import os
import time
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st

st.set_page_config(page_title="Code Review Agent", layout="wide")

# --- Branding / Theme ---
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")


def _apply_theme(*, mode: str) -> None:
    # Minimal CSS overrides. Streamlit theming is limited, so we style only core surfaces.
    is_light = (mode or "dark").lower() == "light"
    if is_light:
        bg = "#F7FAFF"
        sidebar_bg = "#FFFFFF"
        text = "#0B1625"
        muted = "rgba(11, 22, 37, 0.72)"
        border = "rgba(31, 156, 255, 0.20)"
        input_bg = "rgba(235, 244, 255, 1.0)"
        input_text = "#0B1625"
        placeholder = "rgba(11, 22, 37, 0.45)"

        glass = "rgba(255, 255, 255, 0.62)"
        glass2 = "rgba(255, 255, 255, 0.45)"
        glow = "rgba(31, 156, 255, 0.22)"
        code_bg = "rgba(235, 244, 255, 0.90)"
    else:
        bg = "#070F1A"
        sidebar_bg = "#071528"
        text = "#EAF3FF"
        muted = "rgba(234, 243, 255, 0.75)"
        border = "rgba(31, 156, 255, 0.18)"
        input_bg = "rgba(8, 22, 38, 0.85)"
        input_text = "#EAF3FF"
        placeholder = "rgba(234, 243, 255, 0.55)"

        glass = "rgba(7, 21, 40, 0.62)"
        glass2 = "rgba(7, 21, 40, 0.42)"
        glow = "rgba(32, 208, 255, 0.16)"
        code_bg = "rgba(8, 22, 38, 0.78)"

    st.markdown(
        f"""
        <style>
          :root {{
            --cra-bg: {bg};
            --cra-text: {text};
            --cra-muted: {muted};
            --cra-border: {border};
            --cra-input-bg: {input_bg};
            --cra-input-text: {input_text};
            --cra-placeholder: {placeholder};
            --cra-glass: {glass};
            --cra-glass2: {glass2};
            --cra-glow: {glow};
            --cra-code-bg: {code_bg};
            --cra-radius: 16px;
          }}

          /* Remove ONLY the decorative rounded gradient bar at the very top.
             Streamlit 1.53.1 renders it as stDecoration or via a ::before pseudo-element. */
          div[data-testid="stDecoration"],
          div[data-testid="stDecoration"] * {{
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
          }}

          [data-testid="stAppViewContainer"]::before,
          [data-testid="stAppViewContainer"] > div::before,
          body::before {{
            content: none !important;
            display: none !important;
            height: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
          }}

          /* Remove Streamlit's default top chrome (header + toolbar containers). */
          header[data-testid="stHeader"],
          div[data-testid="stToolbar"],
          div[data-testid="stStatusWidget"],
          div[data-testid="stAppToolbar"] {{
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            margin: 0 !important;
            padding: 0 !important;
          }}

          /* Some Streamlit versions reserve space for the header; remove it. */
          [data-testid="stAppViewContainer"] > .main {{
            padding-top: 0 !important;
            margin-top: 0 !important;
          }}
          [data-testid="stAppViewContainer"] > .main > div {{
            padding-top: 0 !important;
          }}

          /* App background: subtle gradient + glow */
          .stApp {{ background: var(--cra-bg); color: var(--cra-text); }}
          [data-testid="stAppViewContainer"] {{
            background:
              radial-gradient(900px 450px at 12% 10%, rgba(31,156,255,0.18), rgba(0,0,0,0) 60%),
              radial-gradient(700px 400px at 82% 12%, rgba(57,229,140,0.14), rgba(0,0,0,0) 62%),
              linear-gradient(180deg, rgba(255,255,255,0.00), rgba(255,255,255,0.00));
          }}

          /* Avoid extra horizontal separators some Streamlit versions inject */
          hr {{
            border: 0 !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
          }}

          /* Make default blocks breathe a bit */
          main .block-container {{
            padding-top: 1.1rem;
            padding-bottom: 3rem;
            max-width: 1200px;
          }}

          /* Title + subtitle */
          .cra-title {{
            font-size: 2.1rem;
            font-weight: 900;
            letter-spacing: 0.2px;
            color: var(--cra-text);
            margin: 0;
            line-height: 1.05;
            text-shadow: 0 0 18px var(--cra-glow);
          }}
          .cra-subtitle {{
            color: var(--cra-muted);
            margin-top: 0.35rem;
            margin-bottom: 0.25rem;
          }}

          /* Glass utility containers */
          .cra-card {{
            background: var(--cra-glass);
            border: 1px solid var(--cra-border);
            border-radius: var(--cra-radius);
            box-shadow: 0 10px 30px rgba(0,0,0,0.16);
            padding: 0.95rem 1.05rem;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
          }}
          .cra-card + .cra-card {{ margin-top: 0.8rem; }}
          .cra-card-title {{
            font-weight: 900;
            letter-spacing: 0.25px;
            margin: 0 0 0.55rem 0;
          }}

    
          .cra-chip {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.20rem 0.55rem;
            border-radius: 999px;
            border: 1px solid var(--cra-border);
            background: var(--cra-glass2);
            color: var(--cra-text);
            font-size: 0.82rem;
            font-weight: 800;
            white-space: nowrap;
          }}
          .cra-dot {{
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: rgba(160,160,160,0.65);
            box-shadow: 0 0 12px rgba(160,160,160,0.25);
          }}
          .cra-dot-ok {{ background: #39E58C; box-shadow: 0 0 14px rgba(57,229,140,0.35); }}
          .cra-dot-bad {{ background: #FF4D6D; box-shadow: 0 0 14px rgba(255,77,109,0.35); }}
          .cra-dot-warn {{ background: #FFD166; box-shadow: 0 0 14px rgba(255,209,102,0.35); }}

          /* Sidebar surface */
          section[data-testid="stSidebar"] {{
            background: {sidebar_bg};
            border-right: 1px solid var(--cra-border);
          }}
          section[data-testid="stSidebar"] > div {{
            background: var(--cra-glass);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
          }}

          /* Force readable foreground colors across common text nodes.
             IMPORTANT: keep this scoped; overly-broad rules can break BaseWeb/Streamlit widgets
             (e.g., selectbox selected value text in light mode). */
          html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
            color: var(--cra-text);
          }}
          p, li, small {{ color: var(--cra-text); }}
          [data-testid="stCaptionContainer"], .stCaption, .stMarkdown small {{ color: var(--cra-muted) !important; }}

          /* Tabs + expanders */
          [data-testid="stTabs"] button {{ color: var(--cra-text) !important; }}
          [data-testid="stTabs"] [role="tablist"] {{
            border-radius: 999px;
            background: var(--cra-glass2);
            padding: 0.2rem;
            border: 1px solid var(--cra-border);
            box-shadow: none;
          }}
          [data-testid="stExpander"] {{
            border-radius: var(--cra-radius);
            border: 1px solid var(--cra-border);
            background: var(--cra-glass2);
          }}
          [data-testid="stExpander"] summary, [data-testid="stExpander"] summary span {{ color: var(--cra-text) !important; }}

          /* Inputs: background + text + placeholder */
          textarea, input,
          .stSelectbox div[data-baseweb="select"],
          .stTextInput div[data-baseweb="input"],
          .stTextArea div[data-baseweb="textarea"] {{
            background-color: var(--cra-input-bg) !important;
            color: var(--cra-input-text) !important;
            border-radius: 12px !important;
            border: 1px solid var(--cra-border) !important;
            box-shadow: 0 0 0 0 rgba(0,0,0,0) !important;
          }}
          textarea::placeholder, input::placeholder {{ color: var(--cra-placeholder) !important; }}

          /* BaseWeb select internals: set the selected value + placeholder explicitly.
             Streamlit uses BaseWeb; classnames are hashed, so we use "contains" selectors. */
          .stSelectbox div[data-baseweb="select"] [class*="SingleValue"],
          .stSelectbox div[data-baseweb="select"] [class*="ValueContainer"],
          .stSelectbox div[data-baseweb="select"] [class*="Input"],
          .stSelectbox div[data-baseweb="select"] input {{
            color: var(--cra-input-text) !important;
          }}
          .stSelectbox div[data-baseweb="select"] [class*="Placeholder"],
          .stSelectbox div[data-baseweb="select"] ::placeholder {{
            color: var(--cra-placeholder) !important;
          }}

          /* Dropdown menu surface + items */
          div[data-baseweb="menu"] {{
            background: var(--cra-input-bg) !important;
            border: 1px solid var(--cra-border) !important;
            border-radius: 12px !important;
          }}
          div[data-baseweb="menu"] * {{
            color: var(--cra-input-text) !important;
          }}

          /* Code blocks */
          pre, code {{
            background: var(--cra-code-bg) !important;
            border: 1px solid var(--cra-border) !important;
            border-radius: 12px !important;
          }}

          /* Metrics */
          [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ color: var(--cra-text) !important; }}

          /* Primary button */
          div.stButton > button {{
            background: linear-gradient(90deg, #1F9CFF 0%, #20D0FF 45%, #39E58C 100%);
            color: #04101C;
            border: 0;
            font-weight: 900;
            border-radius: 14px;
            padding: 0.55rem 1.05rem;
            box-shadow: 0 10px 26px rgba(0,0,0,0.20);
          }}
          div.stButton > button:hover {{ filter: brightness(1.06); transform: translateY(-1px); }}
          div.stButton > button:active {{ transform: translateY(0px); }}

          /* Respect reduced motion */
          @media (prefers-reduced-motion: reduce) {{
            * {{ transition: none !important; animation: none !important; }}
            div.stButton > button:hover {{ transform: none !important; }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_DEFAULT_API_CANDIDATES = [
    "https://code-review-agent-api.onrender.com",
    "http://127.0.0.1:8000",
]

API_BASE_URL = os.environ.get("CODE_REVIEW_API_URL")
if API_BASE_URL is None or not API_BASE_URL.strip():
    API_BASE_URL = _DEFAULT_API_CANDIDATES[0]
API_BASE_URL = API_BASE_URL.rstrip("/")


def _is_default_local_api(url: str) -> bool:
    u = (url or "").strip().lower().rstrip("/")
    return u in {"http://127.0.0.1:8000", "http://localhost:8000"}


def _healthcheck(base_url: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        resp = requests.get(f"{base_url}/healthz", timeout=2)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}", None
        try:
            payload = resp.json()
        except ValueError:
            payload = None
        return True, "Healthy", payload
    except requests.exceptions.RequestException as e:
        return False, f"Not reachable: {e.__class__.__name__}", None


def _get_configz(base_url: str) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(f"{base_url}/configz", timeout=2)
        if resp.status_code != 200:
            return None
        return resp.json()
    except requests.exceptions.RequestException:
        return None


def _firebase_error_from_response(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return "Firebase error: HTTP %s: %s" % (resp.status_code, resp.text)

    err = payload.get("error") if isinstance(payload, dict) else None
    msg = None
    if isinstance(err, dict):
        msg = err.get("message")

    if msg == "CONFIGURATION_NOT_FOUND":
        return (
            "Firebase error: CONFIGURATION_NOT_FOUND\n\n"
            "This means the Web API key is valid, but the Firebase Authentication configuration for this project isn't available.\n"
            "Fix (in the SAME Firebase project as this Web API key):\n"
            "1) Firebase Console → Authentication → Get started\n"
            "2) Authentication → Sign-in method → enable Email/Password\n\n"
            "If you enabled it already, double-check you're in the right project (top-left project picker) and try again after 1-2 minutes.\n\n"
            "Raw: %s" % payload
        )

    if isinstance(err, dict) and msg:
        # Include the raw payload to make API_KEY_INVALID obvious.
        return "Firebase error: %s\n\nRaw: %s" % (msg, payload)

    return "Firebase error: HTTP %s: %s" % (resp.status_code, payload)


def _firebase_preflight(*, api_key: str) -> Tuple[bool, str]:
    """Validate the API key is recognized by Identity Toolkit.

    This helps diagnose CONFIGURATION_NOT_FOUND vs API_KEY_INVALID.
    """
    api_key = (api_key or "").strip()
    if not api_key:
        return False, "FIREBASE_WEB_API_KEY is empty"

    url = "https://identitytoolkit.googleapis.com/v1/accounts:createAuthUri?key=%s" % api_key
    try:
        resp = requests.post(
            url, json={"identifier": "test@example.com", "continueUri": "http://localhost"}, timeout=10
        )
    except requests.exceptions.RequestException as e:
        return False, "Preflight failed: %s" % e.__class__.__name__

    if resp.status_code == 200:
        return True, "Firebase API key looks valid (Identity Toolkit reachable)"

    return False, _firebase_error_from_response(resp)


def _firebase_signup_email_password(*, api_key: str, email: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=%s" % api_key
    try:
        resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=15)
    except requests.exceptions.RequestException as e:
        return None, "Firebase request failed: %r" % (e,)
    if resp.status_code != 200:
        return None, _firebase_error_from_response(resp)
    try:
        return resp.json(), None
    except ValueError as e:
        return None, "Firebase invalid JSON: %s" % e


def _firebase_signin_email_password(*, api_key: str, email: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=%s" % api_key
    try:
        resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=15)
    except requests.exceptions.RequestException as e:
        return None, "Firebase request failed: %r" % (e,)
    if resp.status_code != 200:
        return None, _firebase_error_from_response(resp)
    try:
        return resp.json(), None
    except ValueError as e:
        return None, "Firebase invalid JSON: %s" % e


def _auth_headers() -> Dict[str, str]:
    """No auth headers.

    This UI runs without authentication.
    """

    return {}


def _get_rate(base_url: str) -> Optional[Dict[str, Any]]:
    """Rate-limit endpoint removed.

    The backend no longer exposes authentication or rate limiting endpoints.
    Keep this for backward compatibility with older deployed APIs.
    """

    return None


def _post_review(
    base_url: str, *, code: str, language: str = "python", filename: Optional[str] = None, strict: bool = False
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    # Prefer v2 structured pipeline for Python, since it includes custom logical rules + scoring.
    if (language or "python").lower().strip() == "python":
        v2_body: Dict[str, Any] = {"filename": filename or "input.py", "code": code}
        try:
            resp = requests.post(
                f"{base_url}/v2/review/file",
                json=v2_body,
                headers=_auth_headers(),
                timeout=60,
                params={"strict": bool(strict)},
            )
            if resp.status_code == 200:
                payload = resp.json()
                # Adapt v2 response into the v1 UI shape expected elsewhere in this file.
                issues = payload.get("issues") or []
                return {
                    "compressed_context": code,
                    "static_analysis": payload.get("static_analysis") or {},
                    "issues": issues,
                    "strict_findings": None,
                    "score": payload.get("score"),
                    "engine": "v2",
                }, None
        except requests.exceptions.RequestException:
            # Fall back to v1 below.
            pass
        except ValueError:
            # Invalid JSON; fall back to v1 below.
            pass

    # Fallback: v1 endpoint.
    body: Dict[str, Any] = {"code": code, "language": language, "strict": bool(strict)}
    if filename:
        body["filename"] = filename
    try:
        resp = requests.post(f"{base_url}/review", json=body, headers=_auth_headers(), timeout=60)
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {e!r}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text}"
    try:
        return resp.json(), None
    except ValueError as e:
        return None, f"Invalid JSON from server: {e}"


def _post_review_file(
    base_url: str, *, filename: str, content: bytes
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    files = {"file": (filename, content, "text/x-python")}
    try:
        resp = requests.post(f"{base_url}/review/file", files=files, headers=_auth_headers(), timeout=60)
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {e!r}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text}"
    try:
        return resp.json(), None
    except ValueError as e:
        return None, f"Invalid JSON from server: {e}"


def _post_review_github(
    base_url: str, *, repo_url: str, path: str, ref: str, strict: bool
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    body: Dict[str, Any] = {"repo_url": repo_url, "path": path, "ref": ref, "strict": bool(strict)}
    try:
        resp = requests.post(f"{base_url}/review/github", json=body, headers=_auth_headers(), timeout=60)
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {e!r}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text}"
    try:
        return resp.json(), None
    except ValueError as e:
        return None, f"Invalid JSON from server: {e}"


def _render_review_response(data: Dict[str, Any]) -> None:
    issues = (data or {}).get("issues", [])

    static = (data or {}).get("static_analysis") or {}
    flake8 = (static.get("flake8") or {}) if isinstance(static, dict) else {}
    bandit = (static.get("bandit") or {}) if isinstance(static, dict) else {}

    flake8_issues = (flake8.get("issues") or []) if isinstance(flake8, dict) else []
    bandit_results = []
    if isinstance(bandit, dict):
        bandit_results = (
            ((bandit.get("result") or {}).get("results") or []) if isinstance(bandit.get("result"), dict) else []
        )

    static_tool_failed = False
    if isinstance(flake8, dict) and flake8.get("tool_error"):
        static_tool_failed = True
    if isinstance(bandit, dict) and bandit.get("exit_code") not in (None, 0) and not bandit.get("result"):
        static_tool_failed = True

    static_findings_present = bool(flake8_issues) or bool(bandit_results)

    clean = (not issues) and (not static_findings_present) and (not static_tool_failed)

    if clean:
        st.success("No issues found. Code looks good ✅")
        return

    if static_tool_failed:
        st.warning(
            "LLM review returned no issues, but one or more static analysis tools failed to run. Open 'Raw JSON' for details."
        )

    # Tabs
    tabs = st.tabs(["Summary", "LLM Issues", "flake8", "bandit", "Strict", "Raw JSON"])
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        col1.metric("LLM issues", len(issues))
        col2.metric("flake8 findings", len(flake8_issues))
        col3.metric("bandit findings", len(bandit_results))

        rl = (data or {}).get("rate_limit")
        if isinstance(rl, dict):
            st.caption(
                f"Rate limit: {rl.get('remaining')}/{rl.get('limit')} remaining (reset in {rl.get('reset_seconds')}s)"
            )

    with tabs[1]:
        if not issues:
            st.info("No LLM issues.")
        else:
            sev_options = sorted(
                {(it or {}).get("severity") for it in issues if isinstance(it, dict) and (it or {}).get("severity")}
            )
            cat_options = sorted(
                {(it or {}).get("category") for it in issues if isinstance(it, dict) and (it or {}).get("category")}
            )
            fcol1, fcol2, fcol3 = st.columns([2, 2, 3])
            with fcol1:
                sev = st.multiselect("Severity", sev_options, default=sev_options)
            with fcol2:
                cat = st.multiselect("Category", cat_options, default=cat_options)
            with fcol3:
                q = st.text_input("Search", value="")

            def _match(it: Dict[str, Any]) -> bool:
                if sev and it.get("severity") not in sev:
                    return False
                if cat and it.get("category") not in cat:
                    return False
                if q.strip():
                    qq = q.strip().lower()
                    blob = (
                        "%s %s %s %s"
                        % (it.get("description"), it.get("suggestion"), it.get("location"), it.get("category"))
                    ).lower()
                    return qq in blob
                return True

            filtered = [it for it in issues if isinstance(it, dict) and _match(it)]
            st.caption(f"Showing {len(filtered)}/{len(issues)}")
            for i, issue in enumerate(filtered, 1):
                title = f"{issue.get('severity', 'unknown').upper()} · {issue.get('category', 'unknown')} · {issue.get('location') or 'location n/a'}"
                with st.expander(f"Issue {i}: {title}"):
                    st.write("**Problem:**", issue.get("description"))
                    st.write("**Suggestion:**", issue.get("suggestion"))
                    if issue.get("metadata"):
                        st.caption("metadata")
                        st.json(issue.get("metadata"))

    with tabs[2]:
        if not flake8_issues:
            st.info("No flake8 findings.")
        else:
            for j, it in enumerate(flake8_issues, 1):
                loc = f"{it.get('path', 'input.py')}:{it.get('row', '?')}:{it.get('col', '?')}"
                st.markdown(f"**{j}. {it.get('code', '')}** — {it.get('message', '')}")
                st.caption(loc)

    with tabs[3]:
        if not bandit_results:
            st.info("No bandit findings.")
        else:
            for j, it in enumerate(bandit_results, 1):
                test_id = it.get("test_id") or it.get("test_name") or "bandit"
                sev_b = it.get("issue_severity") or "unknown"
                conf = it.get("issue_confidence") or "unknown"
                text = it.get("issue_text") or it.get("issue") or ""
                fname = it.get("filename") or ""
                line = it.get("line_number") or it.get("line") or ""
                where = f"{fname}:{line}" if fname or line else ""

                st.markdown(f"**{j}. {test_id}** — severity={sev_b}, confidence={conf}")
                if text:
                    st.write(text)
                if where:
                    st.caption(where)

    with tabs[4]:
        strict_text = (data or {}).get("strict_findings")
        if strict_text:
            st.code(strict_text)
        else:
            st.info("Strict mode not enabled or no strict findings returned.")

    with tabs[5]:
        st.json(data)


def _fingerprint_secret(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "(empty)"
    if len(s) <= 8:
        return "*" * len(s)
    return "%s…%s" % (s[:4], s[-4:])


def _firebase_probe_api_key(*, api_key: str) -> Tuple[bool, str]:
    """Probe Firebase Identity Toolkit endpoint to validate the API key.

    Uses a deliberately invalid payload: if the key is valid, Firebase should return
    INVALID_EMAIL / MISSING_PASSWORD / etc. If the key is invalid, it returns
    API_KEY_INVALID.
    """
    api_key = (api_key or "").strip()
    if not api_key:
        return False, "FIREBASE_WEB_API_KEY is empty"

    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=%s" % api_key
    try:
        resp = requests.post(
            url, json={"email": "not-an-email", "password": "x", "returnSecureToken": True}, timeout=10
        )
    except requests.exceptions.RequestException as e:
        return False, "Probe failed: %s" % e.__class__.__name__

    if resp.status_code == 200:
        return True, "Key looks valid (endpoint accepted request)"

    # Parse firebase error message
    try:
        payload = resp.json()
    except ValueError:
        return False, "Probe: HTTP %s (non-JSON)" % resp.status_code

    msg = None
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            msg = err.get("message")

    if msg == "API_KEY_INVALID":
        return False, "API key is invalid (API_KEY_INVALID)"

    # Any other error implies the key is likely valid (but credentials are wrong)
    if msg:
        return True, "Key looks valid (Firebase responded: %s)" % msg

    return False, "Probe returned unexpected response"


# --- Session defaults ---
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

_apply_theme(mode=st.session_state["theme"])

# Header
col_logo, col_title, col_user = st.columns([1, 6, 3], vertical_alignment="center")
with col_logo:
    if os.path.exists(_LOGO_PATH):
        st.image(_LOGO_PATH, width=72)

with col_title:
    st.markdown('<div class="cra-title">Code Review Agent</div>', unsafe_allow_html=True)


with col_user:
    # Header chips (lightweight status at-a-glance)
    ok = st.session_state.get("health_ok")
    msg = st.session_state.get("health_msg")
    if ok is True:
        dot = "cra-dot cra-dot-ok"
        status = "Healthy"
    elif ok is False and msg:
        dot = "cra-dot cra-dot-bad"
        status = "Down"
    else:
        dot = "cra-dot cra-dot-warn"
        status = "Unknown"

    st.markdown(
        f"""
        <div style="display:flex; gap:0.4rem; justify-content:flex-end; align-items:center; flex-wrap:wrap;">
          <div class="cra-chip"><span class="{dot}"></span>API: {status}</div>
          <div class="cra-chip">Mode: {st.session_state.get('theme','dark')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Sidebar: navigation + auth + settings ---
with st.sidebar:
    st.markdown('<div class="cra-card">', unsafe_allow_html=True)
    st.markdown('<div class="cra-card-title">Workspace</div>', unsafe_allow_html=True)
    page = st.radio("Navigate", ["Review"], label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="cra-card">', unsafe_allow_html=True)
    st.markdown('<div class="cra-card-title">Theme</div>', unsafe_allow_html=True)
    theme = st.radio("Mode", ["dark", "light"], index=0 if st.session_state["theme"] == "dark" else 1, horizontal=True)
    if theme != st.session_state["theme"]:
        st.session_state["theme"] = theme
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="cra-card">', unsafe_allow_html=True)
    st.markdown('<div class="cra-card-title">Backend</div>', unsafe_allow_html=True)
    st.write("API:", API_BASE_URL)

    if _is_default_local_api(API_BASE_URL) and os.getenv("CODE_REVIEW_API_URL") is None:
        st.warning(
            "This UI is pointing at 127.0.0.1:8000. That only works on your own machine. "
            "In a deployed Streamlit app, set CODE_REVIEW_API_URL to your hosted API."
        )

    now = time.time()
    last_ts = st.session_state.get("health_ts", 0.0)
    if st.button("Refresh status") or (now - last_ts) > 3:
        ok, msg, payload = _healthcheck(API_BASE_URL)
        st.session_state["health_ok"] = ok
        st.session_state["health_msg"] = msg
        st.session_state["health_payload"] = payload
        st.session_state["health_ts"] = now

    ok = st.session_state.get("health_ok", False)
    msg = st.session_state.get("health_msg", "Unknown")
    payload = st.session_state.get("health_payload")

    if ok:
        st.success(f"Status: {msg}")
        if isinstance(payload, dict):
            st.caption(f"Service: {payload.get('service', 'unknown')} | Version: {payload.get('version', 'unknown')}")
            if payload.get("firebase_configured") is not None:
                st.caption(f"Firebase verify configured: {'yes' if payload.get('firebase_configured') else 'no'}")
        cfg = _get_configz(API_BASE_URL)
        if cfg:
            st.caption(f"LLM configured: {'yes' if cfg.get('llm_api_key_set') else 'no'}")
    else:
        st.error(f"Status: {msg}")
        st.caption("Start the API with: uvicorn app.main:app --reload")

    st.markdown("</div>", unsafe_allow_html=True)

# --- Main pages ---
if page == "Review":
    st.subheader("New review")

    input_mode = st.radio("Input", ["Paste", "Upload file", "GitHub repo"], horizontal=True)
    strict = st.toggle("Strict findings", value=False, help="Include strict_findings in the response")

    language = st.selectbox("Language", ["python"], disabled=False)

    if input_mode == "Paste":
        filename = st.text_input("Filename (optional)", value="input.py")
        code = st.text_area("Code", height=320, placeholder="Paste your Python code here...")
        if st.button("Review", type="primary"):
            if not code.strip():
                st.warning("Please paste some code first.")
            else:
                with st.spinner("Reviewing..."):
                    data, err = _post_review(
                        API_BASE_URL, code=code, language=language, filename=filename, strict=strict
                    )
                if err:
                    st.error("Review failed")
                    st.code(err)
                else:
                    st.session_state["last_response"] = data
                    _render_review_response(data or {})

    elif input_mode == "Upload file":
        up = st.file_uploader("Upload a .py file", type=["py"], accept_multiple_files=False)
        if up is not None:
            st.caption(f"Selected: {up.name} ({up.size} bytes)")
        if st.button("Review", type="primary"):
            if up is None:
                st.warning("Upload a .py file first.")
            else:
                with st.spinner("Reviewing..."):
                    data, err = _post_review_file(API_BASE_URL, filename=up.name, content=up.getvalue())
                if err:
                    st.error("Review failed")
                    st.code(err)
                else:
                    st.session_state["last_response"] = data
                    _render_review_response(data or {})

    else:
        repo_url = st.text_input("GitHub repo URL", placeholder="https://github.com/owner/repo")
        path = st.text_input("File path", value="app/main.py", help="Path to a .py file in the repo")
        ref = st.text_input("Ref (branch/tag/sha)", value="main")
        if st.button("Review", type="primary"):
            if not repo_url.strip():
                st.warning("Enter a repo URL.")
            else:
                with st.spinner("Fetching + reviewing..."):
                    data, err = _post_review_github(API_BASE_URL, repo_url=repo_url, path=path, ref=ref, strict=strict)
                if err:
                    st.error("Review failed")
                    st.code(err)
                else:
                    st.session_state["last_response"] = data
                    _render_review_response(data or {})

    if st.session_state.get("last_response"):
        with st.expander("Last response (cached)"):
            st.json(st.session_state["last_response"])
