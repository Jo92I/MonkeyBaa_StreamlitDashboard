"""
Reusable floating AI assistant helper for Monkey Baa Streamlit app.
"""

from __future__ import annotations

import os
import streamlit as st
from openai import OpenAI


def _get_openai_client():
    api_key = None

    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    return OpenAI(api_key=api_key)


def _assistant_answer(question: str, page_title: str, extra_context: str = "") -> str:
    client = _get_openai_client()

    if client is None:
        return """
⚠️ OpenAI API key not found.

Add this to `.streamlit/secrets.toml`:

OPENAI_API_KEY = "your-api-key-here"
"""

    system_prompt = f"""
You are the Monkey Baa AI Assistant.

You help users understand and use the Monkey Baa AI Social Impact Tool.

Current page: {page_title}

Extra page context:
{extra_context}

You should:
- Give clear, simple guidance.
- Explain what the user can do on this page.
- Help interpret dashboards, OKRs, survey data, reports, and impact indicators.
- Link advice to Monkey Baa's Theory of Change where relevant.
- Keep responses practical and professional.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )

    return response.choices[0].message.content


def render_helper(page_key: str, page_title: str, extra_context: str = ""):
    """
    Renders a reusable AI helper panel.

    Use this at the bottom of any page:

    from lib.assistant import render_helper

    render_helper(
        page_key="dashboard",
        page_title="AI Dashboard",
        extra_context="The user is viewing data visualisations and impact insights."
    )
    """

    state_key = f"{page_key}_helper_messages"

    if state_key not in st.session_state:
        st.session_state[state_key] = [
            {
                "role": "assistant",
                "content": f"Hi, I am your AI helper for **{page_title}**. Ask me how to use this page or interpret the results.",
            }
        ]

    st.markdown(
        """
        <style>
        .assistant-box {
            border: 1px solid rgba(120, 120, 120, 0.25);
            border-radius: 18px;
            padding: 18px;
            margin-top: 24px;
            background: linear-gradient(135deg, rgba(91,44,131,0.08), rgba(214,75,140,0.08));
        }

        .assistant-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .assistant-subtitle {
            font-size: 0.9rem;
            opacity: 0.75;
            margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🤖 AI Assistant Helper", expanded=False):
        st.markdown(
            f"""
            <div class="assistant-box">
                <div class="assistant-title">AI Helper · {page_title}</div>
                <div class="assistant-subtitle">
                    Ask for help, explanation, page guidance, or impact interpretation.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for message in st.session_state[state_key]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        helper_question = st.chat_input(
            f"Ask the helper about {page_title}...",
            key=f"{page_key}_helper_input",
        )

        if helper_question:
            st.session_state[state_key].append(
                {"role": "user", "content": helper_question}
            )

            with st.chat_message("user"):
                st.markdown(helper_question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        answer = _assistant_answer(
                            question=helper_question,
                            page_title=page_title,
                            extra_context=extra_context,
                        )
                    except Exception as e:
                        answer = f"⚠️ Assistant error: {e}"

                st.markdown(answer)

            st.session_state[state_key].append(
                {"role": "assistant", "content": answer}
            )