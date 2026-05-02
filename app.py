import streamlit as st
from pathlib import Path

from lib.auth import login, signup, load_users
from lib.style import inject_css, LOGO_URL, render_sidebar_nav

st.set_page_config(
    page_title="Monkey Baa AI Analysis",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_users()
inject_css()

# -------------------------------
# SESSION STATE
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


# -------------------------------
# PAGE PATHS
# -------------------------------
DATA_LIBRARY_PAGE = "pages/1_Data_Library.py"
OKR_PAGE = "pages/2_OKR_Analysis.py"
AI_ASSISTANT_PAGE = "pages/4_AI_Assistant.py"


render_sidebar_nav()

# -------------------------------
# AFTER LOGIN HOME PAGE
# -------------------------------
if st.session_state.logged_in:

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.image(LOGO_URL, width=500)

    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-title">Welcome back, {st.session_state.username} 👋</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    m1, m2 = st.columns(2)

    with m1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-number">AI</div>
            <div class="metric-label">Impact Analysis Engine</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-number">OKR</div>
            <div class="metric-label">Outcome-Based Measurement</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("## Platform Modules")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("""
        <div class="saas-card">
            <div class="feature-title">📂 Data Library</div>
            <div class="feature-text">
                Upload, manage, clean, and organise survey datasets, Excel files, venue data, and framework documents.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if Path(DATA_LIBRARY_PAGE).exists():
            st.page_link(DATA_LIBRARY_PAGE, label="Open Data Library", icon="📂")
        else:
            st.warning("Data Library page file not found.")

        st.markdown("""
        <div class="saas-card">
            <div class="feature-title">🎯 OKR Analysis</div>
            <div class="feature-text">
                Map Key Results to impact indicators and evaluate performance against outcome-based targets.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if Path(OKR_PAGE).exists():
            st.page_link(OKR_PAGE, label="Open OKR Analysis", icon="🎯")
        else:
            st.warning("OKR Analysis page file not found.")

    with c2:
        st.markdown("""
        <div class="saas-card">
            <div class="feature-title">🤖 AI Assistance</div>
            <div class="feature-text">
                Ask natural-language questions about the data and generate clear, board-ready impact insights.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if Path(AI_ASSISTANT_PAGE).exists():
            st.page_link(AI_ASSISTANT_PAGE, label="Open AI Assistance", icon="🤖")
        else:
            st.warning("AI Assistance page file not found.")


# -------------------------------
# BEFORE LOGIN PAGE
# -------------------------------
else:

    st.markdown("""
    <div class="hero-card">
        <div class="hero-title">🎭 Monkey Baa AI Impact Analytics</div>
        <div class="hero-text">
            A prototype AI-powered reporting platform for social impact analysis.
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1])

    with left:
        st.image(LOGO_URL, use_container_width=True)

    with right:
        st.markdown("""
        <div class="login-card">
            <div class="feature-text">
                Demo details are pre-filled. Click Login to continue.
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

        with tab_login:
            username = st.text_input(
                "Username",
                value="admin",
                key="login_username"
            )

            password = st.text_input(
                "Password",
                value="admin",
                type="password",
                key="login_password"
            )

            if st.button("Login", type="primary", use_container_width=True):
                success, message = login(username, password)

                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

            st.caption("Demo login is pre-filled: admin / admin")

        with tab_signup:
            new_username = st.text_input("New username", key="signup_username")
            new_password = st.text_input("New password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")

            if st.button("Sign Up", use_container_width=True):
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = signup(new_username, new_password)

                    if success:
                        st.success(message)
                    else:
                        st.error(message)


# -------------------------------
# FLOATING ASSISTANT
# -------------------------------
try:
    from lib.floating_assistant import render_floating_ai_assistant
    render_floating_ai_assistant()
except Exception:
    pass