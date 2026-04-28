import streamlit as st
from lib.ai_agent import ask_ai_agent


def render_floating_ai_assistant():
    st.markdown("""
    <style>
    .assistant-box {
        position: fixed;
        bottom: 25px;
        right: 25px;
        width: 360px;
        max-height: 520px;
        overflow-y: auto;
        background: rgba(255,255,255,0.97);
        border: 1px solid #f3d1e3;
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 12px 30px rgba(0,0,0,0.18);
        z-index: 9999;
    }

    @media (prefers-color-scheme: dark) {
        .assistant-box {
            background: rgba(31,41,55,0.97);
            border: 1px solid rgba(249,168,212,0.35);
            color: #f9fafb;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    with st.expander("🤖 AI Help Assistant", expanded=False):
        st.caption(
            "Ask about uploaded data, OKR gaps, risks, Theory of Change, recommendations, or how to use this page."
        )

        if "floating_ai_messages" not in st.session_state:
            st.session_state["floating_ai_messages"] = []

        for msg in st.session_state["floating_ai_messages"][-5:]:
            st.markdown(f"**{msg['role']}:** {msg['content']}")

        question = st.text_input(
            "Ask the assistant",
            key=f"floating_ai_question_{st.session_state.get('page_name', 'page')}"
        )

        if st.button("Ask AI", key=f"floating_ai_button_{st.session_state.get('page_name', 'page')}"):
            if question.strip():
                answer = ask_ai_agent(question)

                st.session_state["floating_ai_messages"].append({
                    "role": "User",
                    "content": question
                })

                st.session_state["floating_ai_messages"].append({
                    "role": "Assistant",
                    "content": answer
                })

                st.rerun()