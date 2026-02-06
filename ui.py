import os
import time
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st

st.set_page_config(page_title="Code Review Agent", layout="centered")

# --- Branding / Theme ---
# Logo path is relative to this file so it works when launched from repo root.
_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

# Streamlit doesn't provide full theming via Python, so we use minimal CSS
# overrides that are stable across versions.
# Palette (derived from logo): deep navy + electric blue + neon green.
st.markdown(
    """
    <style>
      /* Global typography */
      .stApp { background: #070F1A; }

      /* Title area */
      .cra-title {
        font-size: 2.0rem;
        font-weight: 800;
        color: #EAF3FF;
        margin: 0;
        line-height: 1.1;
      }
      .cra-subtitle {
        color: rgba(234, 243, 255, 0.75);
        margin-top: 0.35rem;
        margin-bottom: 0.25rem;
      }

      /* Inputs */
      textarea, input, .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(8, 22, 38, 0.85) !important;
      }

      /* Buttons */
      div.stButton > button {
        background: linear-gradient(90deg, #1F9CFF 0%, #20D0FF 45%, #39E58C 100%);
        color: #04101C;
        border: 0;
        font-weight: 800;
      }
      div.stButton > button:hover { filter: brightness(1.05); }

      /* Sidebar */
      section[data-testid="stSidebar"] {
        background: #071528;
        border-right: 1px solid rgba(31, 156, 255, 0.18);
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header: show logo if present, otherwise just show plain title.
col_logo, col_title = st.columns([1, 5], vertical_alignment="center")
with col_logo:
    if os.path.exists(_LOGO_PATH):
        st.image(_LOGO_PATH, width=84)
with col_title:
    st.markdown('<div class="cra-title">Code Review Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="cra-subtitle">Automated AI-powered code reviewer</div>', unsafe_allow_html=True)

API_BASE_URL = os.environ.get("CODE_REVIEW_API_URL", "http://127.0.0.1:8000").rstrip("/")

def _healthcheck(base_url: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Returns (ok, message, json_payload_if_any). Never raises."""
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

def _post_review(base_url: str, *, code: str, language: str = "python", filename: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Returns (json, error_string). Never raises."""
    body: Dict[str, Any] = {"code": code, "language": language}
    if filename:
        body["filename"] = filename

    try:
        resp = requests.post(f"{base_url}/review", json=body, timeout=30)
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {e!r}"

    if resp.status_code != 200:
        # Show server-provided error message if available.
        return None, f"HTTP {resp.status_code}: {resp.text}"

    try:
        return resp.json(), None
    except ValueError as e:
        return None, f"Invalid JSON from server: {e}"

# --- Sidebar: backend status ---
with st.sidebar:
    st.subheader("Backend")
    st.write("API:", API_BASE_URL)

    # Small cache so we don't spam /healthz on every widget interaction.
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
    else:
        st.error(f"Status: {msg}")
        st.caption("Start the API with: uvicorn app.main:app --reload")

# --- Main UI ---
code = st.text_area(
    "Paste your code here",
    height=250,
    placeholder="Enter your source code...",
)

# Kept for future expansion; backend currently assumes Python.
language = st.selectbox("Select language", ["python"], disabled=False)

if st.button("Review Code"):
    if not code.strip():
        st.warning("Please paste some code first.")
    else:
        with st.spinner("Reviewing your code..."):
            data, err = _post_review(API_BASE_URL, code=code, language=language)

        if err:
            st.error("Review request failed")
            st.code(err)
        else:
            issues = (data or {}).get("issues", [])

            static = (data or {}).get("static_analysis") or {}
            flake8 = (static.get("flake8") or {}) if isinstance(static, dict) else {}
            bandit = (static.get("bandit") or {}) if isinstance(static, dict) else {}

            flake8_issues = (flake8.get("issues") or []) if isinstance(flake8, dict) else []
            bandit_results = []
            if isinstance(bandit, dict):
                bandit_results = ((bandit.get("result") or {}).get("results") or []) if isinstance(bandit.get("result"), dict) else []

            static_tool_failed = False
            if isinstance(flake8, dict) and flake8.get("tool_error"):
                static_tool_failed = True
            if isinstance(bandit, dict) and bandit.get("exit_code") not in (None, 0) and not bandit.get("result"):
                static_tool_failed = True

            static_findings_present = bool(flake8_issues) or bool(bandit_results)

            clean = (not issues) and (not static_findings_present) and (not static_tool_failed)

            if clean:
                st.success("No issues found. Code looks good ✅")
            else:
                if static_tool_failed:
                    st.warning(
                        "LLM review returned no issues, but one or more static analysis tools failed to run. "
                        "Open 'Raw response' for details."
                    )
                elif not issues and static_findings_present:
                    st.warning(
                        f"LLM review returned no issues, but static analysis found {len(flake8_issues)} flake8 finding(s) "
                        f"and {len(bandit_results)} bandit finding(s)."
                    )

                if issues:
                    st.subheader("Review Results")
                    for i, issue in enumerate(issues, 1):
                        st.markdown(f"### Issue {i}")
                        st.write("**Severity:**", issue.get("severity"))
                        st.write("**Category:**", issue.get("category"))
                        st.write("**Problem:**", issue.get("description"))
                        st.write("**Suggestion:**", issue.get("suggestion"))
                        if issue.get("location"):
                            st.write("**Location:**", issue.get("location"))
                        st.divider()

                # --- Static analysis findings (flake8 + bandit) ---
                if static_findings_present:
                    st.subheader("Static Analysis Findings")

                    if flake8_issues:
                        st.markdown("#### flake8")
                        for j, it in enumerate(flake8_issues, 1):
                            loc = f"{it.get('path', 'input.py')}:{it.get('row', '?')}:{it.get('col', '?')}"
                            st.markdown(f"**{j}. {it.get('code', '')}** — {it.get('message', '')}")
                            st.caption(loc)

                    if bandit_results:
                        st.markdown("#### bandit")
                        for j, it in enumerate(bandit_results, 1):
                            # Bandit result shape is a bit verbose; extract common fields.
                            test_id = it.get("test_id") or it.get("test_name") or "bandit"
                            sev = it.get("issue_severity") or "unknown"
                            conf = it.get("issue_confidence") or "unknown"
                            text = it.get("issue_text") or it.get("issue") or ""
                            fname = it.get("filename") or ""
                            line = it.get("line_number") or it.get("line") or ""
                            where = f"{fname}:{line}" if fname or line else ""

                            st.markdown(f"**{j}. {test_id}** — severity={sev}, confidence={conf}")
                            if text:
                                st.write(text)
                            if where:
                                st.caption(where)

            with st.expander("Raw response"):
                st.json(data)
