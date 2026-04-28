import streamlit as st
from lib.auth import login, signup, load_users

st.set_page_config(
    page_title="Monkey Baa AI Analysis",
    page_icon="🎭",
    layout="wide"
)

# Ensure admin exists
load_users()

st.markdown("""
<style>
:root {
    --card-bg: rgba(255,255,255,0.92);
    --text-main: #1f2937;
    --text-soft: #4b5563;
    --accent: #b83280;
    --border: #f3d1e3;
}
@media (prefers-color-scheme: dark) {
    :root {
        --card-bg: rgba(31,41,55,0.94);
        --text-main: #f9fafb;
        --text-soft: #d1d5db;
        --accent: #f9a8d4;
        --border: rgba(249,168,212,0.35);
    }
}
.login-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 26px;
    padding: 32px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.08);
}
.hero-title {
    color: var(--text-main);
    font-size: 38px;
    font-weight: 800;
}
.hero-text {
    color: var(--text-soft);
    font-size: 17px;
}
</style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

st.markdown("""
<div class="login-card">
    <div class="hero-title">🎭 Monkey Baa AI Impact Analytics</div>
    <div class="hero-text">
        Login to manage data, view Theory of Change insights, analyse OKRs and use the AI assistant.
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.logged_in:
    st.success(f"Welcome, {st.session_state.username}")

    st.info("""
    Use the sidebar to access:
    - Data Library
    - OKR Analysis
    - AI Dashboard
    - AI Assistant
    """)

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

else:
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        st.subheader("Login")

        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            success, message = login(username, password)

            if success:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        st.caption("Default main user: username = admin, password = admin")

    with tab_signup:
        st.subheader("Create New Account")

        new_username = st.text_input("New username", key="signup_username")
        new_password = st.text_input("New password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")

        if st.button("Sign Up"):
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = signup(new_username, new_password)

                if success:
                    st.success(message)
                else:
                    st.error(message)
from lib.floating_assistant import render_floating_ai_assistant
render_floating_ai_assistant()