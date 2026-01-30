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

# 2. Deep News Search Function
def search_internet(query):
    try:
        with DDGS() as ddgs:
            deep_query = f"{query} news 2025 2026"
            results = [r for r in ddgs.news(deep_query, max_results=5)]
            if not results:
                results = [r for r in ddgs.text(deep_query, max_results=5)]
            if results:
                context = "\n".join([f"Source: {r.get('title', 'No Title')} - {r.get('body', r.get('snippet', ''))}" for r in results])
                return context
            return "No live internet results found."
    except Exception:
        return "Search currently unavailable."

# 3. Database Initialization
def init_db():
    conn = sqlite3.connect('jitarth_ai.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, chats TEXT, q_idx INTEGER, q_ans TEXT)''')
    conn.commit()
    conn.close()

init_db()

SECURITY_QUESTIONS = ["What is your birth city?", "First school name?", "Favourite pet?"]

# Input Validation Helpers
def validate_username(u):
    u = re.sub(r'[^a-zA-Z0-9 @ _]', '', u)
    return u[:20]

def validate_password(p):
    p = p.replace(" ", "") 
    p = re.sub(r'[^a-zA-Z0-9@_]', '', p)
    return p[:15]

# 4. Page Config & CSS
st.set_page_config(page_title="Jitarth AI", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #131314; color: #e3e3e3; }
    [data-testid="stSidebar"] { background-color: #1e1f20 !important; border-right: 1px solid #3c4043; }
    .gemini-logo { font-family: 'Google Sans', sans-serif; font-size: 28px; font-weight: bold; background: linear-gradient(to right, #4e7cfe, #f06e9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; white-space: nowrap; }
    .sidebar-i-fix { font-size: 35px; }
    .login-logo-container { text-align: center; margin-top: 60px; margin-bottom: 40px; }
    .login-logo-text { font-family: 'Google Sans', sans-serif; font-size: 42px; font-weight: 800; background: linear-gradient(to right, #4e7cfe, #f06e9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; }
    .temp-warning { background-color: rgba(255, 75, 75, 0.1); border: 1px solid #ff4b4b; color: #ff4b4b; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
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

def update_user_credentials(old_u, new_u, new_p, q_idx, q_ans):
    conn = sqlite3.connect('jitarth_ai.db')
    c = conn.cursor()
    try:
        if old_u != new_u and get_user_data(new_u): return False
        c.execute("UPDATE users SET username=?, password=?, q_idx=?, q_ans=? WHERE username=?", (new_u, new_p, q_idx, q_ans, old_u))
        conn.commit(); return True
    except: return False
    finally: conn.close()

def delete_user_account(username):
    conn = sqlite3.connect('jitarth_ai.db')
    c = conn.cursor(); c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit(); conn.close()

def save_user_chats(username, chats):
    conn = sqlite3.connect('jitarth_ai.db')
    c = conn.cursor(); c.execute("UPDATE users SET chats=? WHERE username=?", (json.dumps(chats), username))
    conn.commit(); conn.close()

# 6. Dialogs
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
        elif action_type == "delete_account": 
            delete_user_account(st.session_state.logged_in_user)
            cookie_manager.delete('jitarth_user_cookie')
            st.session_state.logged_in_user = None
        elif action_type == "update_profile":
            if update_user_credentials(*data): 
                st.session_state.logged_in_user = data[1]
                cookie_manager.set('jitarth_user_cookie', data[1])
            else: st.error("Error updating profile")
        st.rerun()
    if cols[1].button("No, Cancel", use_container_width=True): st.rerun()

# 7. Recovery UI
def recovery_ui(is_from_settings=False):
    st.subheader("🔑 Recover Password")
    u_find = st.text_input("Enter Username", value=st.session_state.get('logged_in_user', "") if is_from_settings else "")
    user_check = get_user_data(u_find) if u_find else None
    with st.form("recover_form"):
        if user_check:
            st.info(f"Question: {SECURITY_QUESTIONS[user_check[3]]}")
            ans = st.text_input("Your Answer", type="password")
            if st.form_submit_button("Recover Password", use_container_width=True):
                if user_check[4].lower() == ans.lower(): st.success(f"Verified! Your Password is: {user_check[1]}")
                else: st.error("Wrong Answer!")
        else: st.form_submit_button("Check Username", disabled=True)
    if st.button("← Back"):
        if is_from_settings: st.session_state.settings_recover_mode = False
        else: st.session_state.forgot_mode = False
        st.rerun()

# 8. Main UI Logic Init
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
if "is_temp_mode" not in st.session_state: st.session_state.is_temp_mode = False
if "show_settings" not in st.session_state: st.session_state.show_settings = False

# MASTER COOKIE LOGIC
saved_user = cookie_manager.get('jitarth_user_cookie')
if saved_user and st.session_state.logged_in_user is None:
    st.session_state.logged_in_user = saved_user
    st.rerun()

# Login Screen Logic
if st.session_state.logged_in_user is None:
    st.markdown('<div class="login-logo-container"><div class="login-logo-text">Jitarth A<span class="sidebar-i-fix">I</span> ✨</div></div>', unsafe_allow_html=True)
    if st.session_state.get("forgot_mode"): 
        recovery_ui(False)
    else:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            u_login = st.text_input("Username", key="login_u")
            p_login = st.text_input("Password", type="password", key="login_p")
            if st.button("Log In", use_container_width=True):
                user = get_user_data(u_login)
                if user and user[1] == p_login:
                    st.session_state.logged_in_user = u_login
                    expiry = datetime.now() + timedelta(days=30)
                    cookie_manager.set('jitarth_user_cookie', u_login, expires_at=expiry)
                    st.rerun()
                else: st.error("Invalid Username or Password")
            if st.button("Recover Password?", use_container_width=True):
                st.session_state.forgot_mode = True
                st.rerun()
        with tab2:
            nu_raw = st.text_input("Choose Username (Min 5 chars)", key="reg_u")
            nu = validate_username(nu_raw)
            np_raw = st.text_input("Create Password (Min 4 chars)", type="password", key="reg_p")
            np = validate_password(np_raw)
            sq = st.selectbox("Security Question", SECURITY_QUESTIONS)
            sa = st.text_input("Answer (Min 2 characters)")
            if st.button("SIGN UP", use_container_width=True):
                if len(nu) < 5 or len(np) < 4 or len(sa) < 2: st.error("Requirements not met")
                elif get_user_data(nu): st.error("Username taken")
                else:
                    if create_user(nu, np, SECURITY_QUESTIONS.index(sq), sa):
                        st.success("Account Created! Please Login.")
                    else: st.error("Registration failed")
else:
    current_user = st.session_state.logged_in_user
    user_record = get_user_data(current_user)
    if not user_record:
        cookie_manager.delete('jitarth_user_cookie')
        st.session_state.logged_in_user = None
        st.rerun()
    user_chats = json.loads(user_record[2])

    with st.sidebar:
        # Layout pehle jaisa: Logo upar, phir buttons
        st.markdown('<div class="gemini-logo">Jitarth A<span class="sidebar-i-fix">I</span> ✨</div>', unsafe_allow_html=True)
        st.write("") # Spacer
        
        col_s1, col_s2 = st.columns([0.8, 0.2])
        with col_s1:
            if st.button("➕ New Chat", use_container_width=True):
                st.session_state.show_settings = False
                st.session_state.current_session = None
                st.session_state.is_temp_mode = False
                st.rerun()
        with col_s2:
            if st.button("⚙️"):
                st.session_state.show_settings = not st.session_state.show_settings
                st.rerun()

        if st.button("🤫 Temporary Chat", use_container_width=True):
            st.session_state.show_settings = False
            st.session_state.is_temp_mode = True
            st.session_state.temp_messages = []
            st.rerun()
            
        st.write("---")
        st.caption("Recent Chats")
        for title in reversed(list(user_chats.keys())):
            if st.button(f"💬 {title[:20]}...", key=f"sb_{title}", use_container_width=True):
                st.session_state.show_settings = False
                st.session_state.current_session = title
                st.session_state.is_temp_mode = False
                st.rerun()

    if st.session_state.show_settings:
        st.title("⚙️ Account Settings")
        v_p = st.text_input("Enter Password to Unlock Settings", type="password")
        if v_p == user_record[1]:
            st.success("Settings Unlocked ✅")
            with st.expander("👤 Update Profile Information", expanded=True):
                nu_settings = st.text_input("New Username", value=current_user)
                np_settings = st.text_input("New Password", value=user_record[1], type="password")
                uq = st.selectbox("Security Question", SECURITY_QUESTIONS, index=user_record[3])
                ua = st.text_input("Security Answer", value=user_record[4])
                if st.button("Save Changes", use_container_width=True):
                    confirm_dialog("Update profile details?", "update_profile", (current_user, nu_settings, np_settings, SECURITY_QUESTIONS.index(uq), ua))
            with st.expander("⚠️ Danger Zone"):
                if st.button("🔴 Logout Account", use_container_width=True): confirm_dialog("Logout?", "logout")
                if st.button("🗑️ Delete All Chats", use_container_width=True): confirm_dialog("Delete history?", "delete_chats")
                if st.button("❌ Delete Account Permanently", use_container_width=True): confirm_dialog("Delete account?", "delete_account")
        elif v_p: st.error("Incorrect Password")
        st.markdown("---")
        st.markdown("""<div style='text-align: center; background-color: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; margin-top: 20px;'><p style='color: #8e918f; font-size: 14px; margin-bottom: 8px;'>📲 For any queries or support, feel free to reach out</p><a href='https://www.instagram.com/jitarths_2013_js' target='_blank' style='color: #4e7cfe; text-decoration: none; font-weight: 600; font-size: 16px;'>Follow & Contact: @jitarths_2013_js</a></div>""", unsafe_allow_html=True)
    else:
        if st.session_state.is_temp_mode:
            if not st.session_state.get("temp_messages"): st.markdown('<div class="temp-warning">🔒 Temporary Chat Active (Not Saved)</div>', unsafe_allow_html=True)
            messages = st.session_state.get("temp_messages", [])
        else:
            if not st.session_state.get("current_session"):
                st.markdown(f"<h2 style='text-align:center; margin-top:100px;'>Hello, {current_user}</h2>", unsafe_allow_html=True)
                messages = []
            else: messages = user_chats.get(st.session_state.current_session, [])

        for m in messages:
            with st.chat_message(m["role"], avatar="👤" if m["role"]=="user" else "✨"): st.markdown(m["content"])

        if p := st.chat_input("Ask Jitarth AI..."):
            if st.session_state.is_temp_mode:
                if "temp_messages" not in st.session_state: st.session_state.temp_messages = []
                active_list = st.session_state.temp_messages
            else:
                if not st.session_state.get("current_session"):
                    st.session_state.current_session = p[:30]
                    user_chats[st.session_state.current_session] = []
                active_list = user_chats[st.session_state.current_session]
            
            active_list.append({"role": "user", "content": p})
            with st.chat_message("user", avatar="👤"): st.markdown(p)
            
            with st.chat_message("assistant", avatar="✨"):
                with st.status("🔍 Scanning Live 2026 Data...", expanded=False): 
                    internet_context = search_internet(p)
                
                sys_prompt = f"""You are ✨Jitarth AI, a super-intelligent and friendly AI. 
                Your creator and inventor is 'Jitarth Satija'. 
                If anyone asks who created you or who is your developer, you must ONLY answer 'Jitarth Satija'. 
                DO NOT mention Meta, Google, or any other company. You are independent.
                Current Date: {datetime.now().strftime('%B %Y')}.
                Context from Web: {internet_context}"""

                try:
                    response_obj = client.chat.completions.create(
                        messages=[{"role": "system", "content": sys_prompt}] + active_list, 
                        model="llama-3.3-70b-versatile"
                    )
                    response = response_obj.choices[0].message.content
                    st.markdown(response)
                    active_list.append({"role": "assistant", "content": response})
                    if not st.session_state.is_temp_mode: save_user_chats(current_user, user_chats)
                    st.rerun()
                except Exception as e:
                    # Rerun handling to prevent "Server Down" false positive
                    if "RerunException" not in str(type(e)):
                        st.error("Server Down. Try later.")
