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

# 2. Optimized Search Function
def search_internet(query):
    try:
        with DDGS() as ddgs:
            deep_query = f"{query} news 2025 2026"
            results = list(ddgs.text(deep_query, max_results=5))
            if results:
                context = "\n".join([f"Source: {r.get('title', '')} - {r.get('body', '')}" for r in results])
                return context
            return "No recent web data found."
    except Exception:
        return "Search timed out."

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

# Validation Helpers
def validate_username(u):
    u = re.sub(r'[^a-zA-Z0-9 @ _]', '', u)
    return u[:20]

def validate_password(p):
    p = re.sub(r'[^a-zA-Z0-9@_]', '', p)
    return p[:10]

def generate_suggestions(base_u):
    if not base_u or len(base_u) < 2: base_u = "user"
    suggs = []
    for _ in range(3):
        rand_val = "".join(random.choices(string.ascii_lowercase + string.digits, k=2))
        suggs.append(f"{base_u}{rand_val}")
    return suggs

# 4. Page Config & CSS
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

# Master Cookie Logic
saved_user = cookie_manager.get('jitarth_user_cookie')
if saved_user and st.session_state.logged_in_user is None:
    st.session_state.logged_in_user = saved_user
    st.rerun()

# 7. Login / Chat Logic
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
            else: st.error("Invalid Credentials")
    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        sq = st.selectbox("Security Question", SECURITY_QUESTIONS)
        sa = st.text_input("Answer")
        if st.button("Create Account", use_container_width=True):
            if create_user(nu, np, SECURITY_QUESTIONS.index(sq), sa): st.success("Created!")
            else: st.error("Failed")
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

    # Chat UI
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
            with st.spinner("Searching 2026 data..."):
                internet_context = search_internet(p)
            
            sys_prompt = f"""You are ✨Jitarth AI, created by Jitarth Satija. Today: Jan 30, 2026.
            Answer using this search data: {internet_context}. 
            If data is about Trump tariffs or Pahalgam 2025, give full details. 
            Do NOT mention knowledge cutoff. Talk like a 2026 assistant."""

            try:
                # Direct Stream for better stability
                response_container = st.empty()
                full_response = ""
                response_stream = client.chat.completions.create(
                    messages=[{"role": "system", "content": sys_prompt}] + active_list, 
                    model="llama-3.3-70b-versatile",
                    stream=True
                )
                for chunk in response_stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_container.markdown(full_response)
                
                active_list.append({"role": "assistant", "content": full_response})
                if not st.session_state.is_temp_mode: save_user_chats(current_user, user_chats)
            except: st.error("Connection slow. Try again.")
