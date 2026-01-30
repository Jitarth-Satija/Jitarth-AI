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

# 2. Advanced Multi-Engine Search (Fixed for better results)
def search_internet(query):
    try:
        results_list = []
        with DDGS() as ddgs:
            # 1st Attempt: News Search
            news_results = ddgs.news(f"{query} 2026", max_results=5)
            for r in news_results:
                results_list.append(f"News: {r['title']} - {r['body']}")
            
            # 2nd Attempt: If news is thin, get Web Text
            if len(results_list) < 3:
                web_results = ddgs.text(f"{query} latest update 2026", max_results=5)
                for r in web_results:
                    results_list.append(f"Web: {r['title']} - {r['body']}")
            
        if results_list:
            return "\n".join(results_list)
        return "No real-time data found. Answer based on current context of Jan 2026."
    except Exception as e:
        return f"Search error: {str(e)}"

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

# --- Input Validation Helpers ---
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

# 4. Page Config & CSS (Tera Original Style)
st.set_page_config(page_title="Jitarth AI", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #131314; color: #e3e3e3; }
    [data-testid="stSidebar"] { background-color: #1e1f20 !important; border-right: 1px solid #3c4043; }
    .gemini-logo { font-family: 'Google Sans', sans-serif; font-size: 28px; font-weight: bold; background: linear-gradient(to right, #4e7cfe, #f06e9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; }
    .login-logo-text { font-family: 'Google Sans', sans-serif; font-size: 42px; font-weight: 800; background: linear-gradient(to right, #4e7cfe, #f06e9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; }
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

# 6. Dialogs (Tera Original)
@st.dialog("Confirm Action")
def confirm_dialog(message, action_type, data=None):
    st.write(f"⚠️ {message}")
    st.write("---")
    cols = st.columns(2)
    if cols[0].button("Yes, Proceed", use_container_width=True, type="primary"):
        if action_type == "logout":
            cookie_manager.delete('jitarth_user_cookie')
            st.session_state.logged_in_user = None
        elif action_type == "delete_chats": 
            save_user_chats(st.session_state.logged_in_user, {})
        st.rerun()
    if cols[1].button("No, Cancel", use_container_width=True): st.rerun()

# 8. Main UI Logic
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
if "is_temp_mode" not in st.session_state: st.session_state.is_temp_mode = False
if "show_settings" not in st.session_state: st.session_state.show_settings = False

# Cookie Auto-Login
saved_user = cookie_manager.get('jitarth_user_cookie')
if saved_user and st.session_state.logged_in_user is None:
    st.session_state.logged_in_user = saved_user
    st.rerun()

if st.session_state.logged_in_user is None:
    st.markdown('<div style="text-align:center; margin-top:50px;"><div class="login-logo-text">Jitarth AI ✨</div></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        u_login = st.text_input("Username", key="l_u")
        p_login = st.text_input("Password", type="password", key="l_p")
        if st.button("Log In", use_container_width=True):
            user = get_user_data(u_login)
            if user and user[1] == p_login:
                st.session_state.logged_in_user = u_login
                cookie_manager.set('jitarth_user_cookie', u_login)
                st.rerun()
            else: st.error("Galt details hain bhai!")
    with tab2:
        nu = st.text_input("Choose Username", key="r_u")
        np = st.text_input("Choose Password", type="password", key="r_p")
        sq = st.selectbox("Security Question", SECURITY_QUESTIONS)
        sa = st.text_input("Answer")
        if st.button("Sign Up", use_container_width=True):
            if create_user(nu, np, SECURITY_QUESTIONS.index(sq), sa): st.success("Account Ready!")
            else: st.error("Username already exists.")

else:
    current_user = st.session_state.logged_in_user
    user_record = get_user_data(current_user)
    user_chats = json.loads(user_record[2])

    with st.sidebar:
        # --- SETTINGS BUTTON (WAPAS AA GAYA) ---
        sc1, sc2 = st.columns([0.2, 0.8])
        with sc1:
            if st.button("⚙️", key="settings_btn"):
                st.session_state.show_settings = not st.session_state.show_settings
                st.rerun()
        with sc2:
            st.markdown('<div class="gemini-logo">Jitarth AI ✨</div>', unsafe_allow_html=True)
        
        st.write("")
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.show_settings = False
            st.session_state.current_session = None
            st.session_state.is_temp_mode = False
            st.rerun()
        if st.button("🤫 Temporary Chat", use_container_width=True):
            st.session_state.show_settings = False
            st.session_state.is_temp_mode = True
            st.session_state.temp_messages = []
            st.rerun()
        st.write("---")
        for title in reversed(list(user_chats.keys())):
            if st.button(f"💬 {title[:20]}...", use_container_width=True):
                st.session_state.show_settings = False
                st.session_state.current_session = title
                st.session_state.is_temp_mode = False
                st.rerun()

    # Settings View
    if st.session_state.show_settings:
        st.title("⚙️ Account Settings")
        if st.button("🔴 Logout", use_container_width=True):
            confirm_dialog("Logout karna chahte ho?", "logout")
        if st.button("🗑️ Clear All Chats", use_container_width=True):
            confirm_dialog("Sari history delete karein?", "delete_chats")
    else:
        # Chat Interface
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
                with st.status("🔍 Searching Web (2026 Reports)...", expanded=False):
                    internet_context = search_internet(p)
                
                # FINAL PROMPT: No Cutoff excuses!
                sys_prompt = f"""You are ✨Jitarth AI by Jitarth Satija. Today: Jan 30, 2026.
                SEARCH DATA: {internet_context}
                INSTRUCTION: Use the search data to answer accurately about 2025-2026. 
                If the search data mentions Dhoni, Trump, or Pahalgam, explain it based on the sources.
                Do not say your cutoff is 2025. Stream the response."""

                response_container = st.empty()
                full_response = ""
                try:
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
                except: st.error("Server slow hai, dubara pucho bhai!")
