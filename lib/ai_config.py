import os
import streamlit as st
from dotenv import load_dotenv


def get_openai_client():
    load_dotenv()

    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None, "OpenAI API key not found"

    return api_key, None