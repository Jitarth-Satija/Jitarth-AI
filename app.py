from datetime import datetime, timedelta
import streamlit as st
from groq import Groq
import sqlite3
import json
from duckduckgo_search import DDGS
import re
import random
import string
import extra_streamlit_components as stx
import os

# 1. Setup - API Key
api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)
cookie_manager = stx.CookieManager()

# 2. Advanced Search Function (Improved for 2026 news)
def search_internet(query):
    try:
        with DDGS() as ddgs:
            # Query ko specifically 2026 IPL aur Dhoni ke liye customize kiya
            search_query = f"{query} news update January 2026"
            results = list(ddgs.text(search_query, max_results=6))
            if results:
                context = "\n".join([f"Source: {r.get('title', '')} - {r.get('body', '')}" for r in results])
                return context
            return "No real-time news found for 2026."
    except Exception:
        return "Internet search is currently unavailable."

# 3. Database Initialization
def init_db():
    conn = sqlite3.connect('jitarth_ai.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, chats TEXT, q_idx INTEGER, q_ans TEXT)''')
    conn.commit()
    conn.close()

init_db()

SECURITY_QUESTIONS = ["What is your birth city?", "First school name?", "Favourite pet?"]

# 4. Page Config & CSS (✨ Logo and Premium Look)
st.set_page_config(page_title="✨ Jitarth AI", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #131314; color: #e3e3e3; }
    [data-testid="stSidebar"] { background-color: #1e1f20 !important; }
    .gemini-logo { font-family: 'Google Sans', sans-serif; font-size: 28px; font-weight: bold; background: linear-gradient(to right, #4e7cfe, #f06e9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# 5. Database Functions
def get_user_data(username):
    conn = sqlite3.connect('jitarth_ai.db')
    c = conn.cursor(); c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone(); conn.close()
    return user

def create_user(username, password, q_idx, q_ans):
    conn = sqlite3.connect('jitarth_ai.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (username, password, json.dumps({}), q_idx, q_ans))
        conn.commit(); return True
    except: return False
    finally: conn.close()

def save_user_chats(username, chats):
    conn = sqlite3.connect('jitarth_ai.db')
    c = conn.cursor(); c.execute("UPDATE users SET chats=? WHERE username=?", (json.dumps(chats), username))
    conn.commit(); conn.close()

# 6. Session States
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
if "is_temp_mode" not in st.session_state: st.session_state.is_temp_mode = False
if "current_session" not in st.session_state: st.session_state.current_session = None

# Cookie Auto-Login
saved_user = cookie_manager.get('jitarth_user_cookie')
if saved_user and st.session_state.logged_in_user is None:
    st.session_state.logged_in_user = saved_user
    st.rerun()

# 7. UI Logic
if st.session_state.logged_in_user is None:
    st.title("✨ Jitarth AI")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        u_login = st.text_input("Username")
        p_login = st.text_input("Password", type="password")
        if st.button("Log In", use_container_width=True):
            user = get_user_data(u_login)
            if user and user[1] == p_login:
                st.session_state.logged_in_user = u_login
                cookie_manager.set('jitarth_user_cookie', u_login)
                st.rerun()
            else: st.error("Wrong details!")
    with tab2:
        nu = st.text_input("Choose Username")
        np = st.text_input("Choose Password", type="password")
        sq = st.selectbox("Security Question", SECURITY_QUESTIONS)
        sa = st.text_input("Answer")
        if st.button("Create Account", use_container_width=True):
            if create_user(nu, np, SECURITY_QUESTIONS.index(sq), sa): st.success("Account Ready!")
            else: st.error("Username taken.")
else:
    current_user = st.session_state.logged_in_user
    user_record = get_user_data(current_user)
    user_chats = json.loads(user_record[2])

    with st.sidebar:
        st.markdown('<div class="gemini-logo">Jitarth AI ✨</div>', unsafe_allow_html=True)
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.current_session = None
            st.session_state.is_temp_mode = False
            st.rerun()
        if st.button("🤫 Temporary Chat", use_container_width=True):
            st.session_state.is_temp_mode = True
            st.session_state.temp_messages = []
            st.rerun()
        st.write("---")
        for title in reversed(list(user_chats.keys())):
            if st.button(f"💬 {title[:20]}", use_container_width=True):
                st.session_state.current_session = title
                st.session_state.is_temp_mode = False
                st.rerun()
        if st.button("🔴 Logout", use_container_width=True):
            cookie_manager.delete('jitarth_user_cookie')
            st.session_state.logged_in_user = None
            st.rerun()

    # --- CHAT AREA ---
    messages = st.session_state.temp_messages if st.session_state.is_temp_mode else (user_chats.get(st.session_state.current_session, []) if st.session_state.current_session else [])
    
    for m in messages:
        with st.chat_message(m["role"], avatar="👤" if m["role"]=="user" else "✨"): st.markdown(m["content"])

    if p := st.chat_input("Ask ✨Jitarth AI..."):
        if st.session_state.is_temp_mode: active_list = st.session_state.temp_messages
        else:
            if not st.session_state.current_session:
                st.session_state.current_session = p[:30]
                user_chats[st.session_state.current_session] = []
            active_list = user_chats[st.session_state.current_session]
        
        active_list.append({"role": "user", "content": p})
        with st.chat_message("user", avatar="👤"): st.markdown(p)
        
        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("Checking 2026 sports news..."):
                internet_context = search_internet(p)
            
            # THE "FORCE" PROMPT: This tells AI it is 2026 and to USE the search data.
            sys_prompt = f"""You are ✨Jitarth AI, an advanced AI developed by Jitarth Satija.
            Today's Date: January 30, 2026.
            
            IMPORTANT: Use the following SEARCH DATA to answer. Do not say you are an AI with a 2025 cutoff. 
            Act as if you are living in 2026.
            
            SEARCH DATA:
            {internet_context}
            
            If the user asks about Dhoni in IPL 2026 or Trump Tariffs, look for the answer in the SEARCH DATA above. 
            Be specific and helpful."""

            try:
                response_container = st.empty()
                full_response = ""
                # Streaming for better stability
                stream = client.chat.completions.create(
                    messages=[{"role": "system", "content": sys_prompt}] + active_list, 
                    model="llama-3.3-70b-versatile",
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_container.markdown(full_response)
                
                active_list.append({"role": "assistant", "content": full_response})
                if not st.session_state.is_temp_mode: save_user_chats(current_user, user_chats)
            except Exception:
                st.error("Server is a bit slow. Please ask again!")
