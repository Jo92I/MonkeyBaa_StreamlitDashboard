import streamlit as st

LOGO_URL = "data/MonkeyBaaLogo.png"

from pathlib import Path

DATA_LIBRARY_PAGE = "pages/1_Data_Library.py"
OKR_PAGE = "pages/2_OKR_Analysis.py"
AI_ASSISTANT_PAGE = "pages/4_AI_Assistant.py"


def render_sidebar_nav():
    with st.sidebar:
        st.markdown("### 🎭 Monkey Baa")
        st.markdown("**AI Impact Analytics**")
        st.divider()

        if st.session_state.get("logged_in", False):
            st.success(f"Logged in as {st.session_state.get('username', 'admin')}")

            st.markdown("### Navigation")

            st.page_link("app.py", label="🏠 Home", icon="🏠")

            if Path(DATA_LIBRARY_PAGE).exists():
                st.page_link(DATA_LIBRARY_PAGE, label="📂 Data Library", icon="📂")

            if Path(OKR_PAGE).exists():
                st.page_link(OKR_PAGE, label="🎯 OKR Analysis", icon="🎯")

            if Path(AI_ASSISTANT_PAGE).exists():
                st.page_link(AI_ASSISTANT_PAGE, label="🤖 AI Assistance", icon="🤖")

            st.divider()

            if st.button("Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()
        else:
            st.info("Demo login is pre-filled.")
def inject_css():
    st.markdown("""
    <style>
    :root {
        --card-bg: rgba(255,255,255,0.94);
        --text-main: #1f2937;
        --text-soft: #4b5563;
        --accent: #b83280;
        --accent-2: #5b2c83;
        --border: #f3d1e3;
        --shadow: rgba(0,0,0,0.08);
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --card-bg: rgba(31,41,55,0.94);
            --text-main: #f9fafb;
            --text-soft: #d1d5db;
            --accent: #f9a8d4;
            --accent-2: #c084fc;
            --border: rgba(249,168,212,0.35);
            --shadow: rgba(0,0,0,0.28);
        }
    }

    /* Hide default Streamlit pages list */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #5b2c83 0%, #b83280 100%);
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    .hero-card {
        background: linear-gradient(135deg, rgba(91,44,131,0.95), rgba(184,50,128,0.92));
        border-radius: 30px;
        padding: 42px;
        margin-bottom: 26px;
        color: white;
        box-shadow: 0 18px 45px var(--shadow);
        animation: fadeSlide 0.9s ease-out;
    }

    .hero-title {
        font-size: 44px;
        font-weight: 900;
        margin-bottom: 12px;
    }

    .hero-text {
        font-size: 18px;
        opacity: 0.95;
        max-width: 850px;
    }

    @keyframes fadeSlide {
        from { opacity: 0; transform: translateY(-18px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .saas-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 26px;
        box-shadow: 0 10px 28px var(--shadow);
        margin-bottom: 20px;
    }

    .metric-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 8px 22px var(--shadow);
    }

    .metric-number {
        font-size: 34px;
        font-weight: 900;
        color: var(--accent);
    }

    .metric-label {
        font-size: 15px;
        color: var(--text-soft);
    }

    .login-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 26px;
        padding: 32px;
        box-shadow: 0 10px 28px var(--shadow);
        margin-bottom: 24px;
    }

    .feature-title {
        color: var(--text-main);
        font-size: 20px;
        font-weight: 800;
    }

    .feature-text {
        color: var(--text-soft);
        font-size: 15px;
    }

    div.stButton > button {
        border-radius: 14px;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)


def banner(title, subtitle=""):
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-title">{title}</div>
        <div class="hero-text">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def section(title):
    st.markdown(f"## {title}")