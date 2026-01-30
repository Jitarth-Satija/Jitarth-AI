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
            return "No live internet results found. Please answer based on your current knowledge."
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
    return p[:10]

def generate_suggestions(base_u):
    if not base_u or len(base_u) < 2: base_u = "user"
    suggs = []
    attempts = 0
    while len(suggs) < 3 and attempts < 10:
        rand_val = "".join(random.choices(string.ascii_lowercase + string.digits, k=2))
        candidate = f"{base_u}{rand_val}"
        if not get_user_data(candidate):
            suggs.append(candidate)
        attempts += 1
    return suggs

# 4. Page Config & CSS
st.set_page_config(page_title="Jitarth AI", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #131314; color: #e3e3e3; }
    [data-testid="stSidebar"] { background-color: #1e1f20 !important; border-right: 1px solid #3c4043; }
    
    /* LOGO GLOBAL STYLES */
    .gemini-logo { 
        font-family: 'Google Sans', sans-serif; 
        font-size: 32px; 
        font-weight: 700; 
        background: linear-gradient(to right, #4e7cfe, #f06e9c); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        display: inline-flex; 
        align-items: center;
        white-space: nowrap;
        letter-spacing: -0.5px;
    }

    /* J and I size adjustments */
    .logo-j { font-size: 44px; line-height: 0; margin-right: -2px; }
    .i-fix { font-size: 32px; font-weight: 700; } 
    
    /* Login Screen Logo Specifics */
    .login-logo-container { 
        text-align: center; 
        margin-top: 50px; 
        margin-bottom: 30px; 
        display: flex;
        justify-content: center;
    }
    .login-logo-text { 
        font-family: 'Google Sans', sans-serif; 
        font-size: 48px; 
        font-weight: 800; 
        background: linear-gradient(to right, #4e7cfe, #f06e9c); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        display: inline-flex;
        align-items: center;
        letter-spacing: -1px;
    }
    .login-j { font-size: 64px; line-height: 0; margin-right: -2px; }
    .login-i { font-size: 48px; font-weight: 800; }

    .temp-warning { background-color: rgba(255, 75, 75, 0.1); border: 1px solid #ff4b4b; color: #ff4b4b; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    footer {visibility: hidden;}
    
    /* Sidebar Row Alignment */
    [data-testid="column"] {
        display: flex;
        align-items: center;
    }
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
            else: st.error("Error updating profile")
        st.rerun()
    if cols[1].button("No, Cancel", use_container_width=True): st.rerun()

# 7. Recovery UI
def recovery_ui(is_from_settings=False):
    st.subheader("🔑 Recover Password")
    u_find = st.text_input("Username", value=st.session_state.get('logged_in_user', "") if is_from_settings else "")
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
if "suggested_un" not in st.session_state: st.session_state.suggested_un = ""

# Master Cookie Login
saved_user = cookie_manager.get('jitarth_user_cookie')
if saved_user and st.session_state.logged_in_user is None:
    st.session_state.logged_in_user = saved_user
    st.rerun()

# Login Screen
if st.session_state.logged_in_user is None:
    # Optimized Login Logo with fixed aspect and centered alignment
   st.markdown('<div class="login-logo-container"><div class="login-logo-text"><span class="login-j">J</span>itarth A<span class="login-i">I</span> ✨</div></div>', unsafe_allow_html=True)
# Niche wali line add kar do
    st.markdown("<p style='text-align:center; color:#8e918f; margin-top:-25px; margin-bottom:20px;'>Connect: <a href='https://www.instagram.com/jitarths_2013_js' target='_blank' style='color:#4e7cfe; text-decoration:none; font-weight:bold;'>@jitarths_2013_js</a></p>", unsafe_allow_html=True)
        if st.session_state.get("forgot_mode"): recovery_ui(False)
        else:
            tab1, tab2 = st.tabs(["Login", "Sign Up"])
            with tab1:
                u_login = st.text_input("Username", key="login_u")
                p_login = st.text_input("Password", type="password", key="login_p")
                if st.button("Log In", use_container_width=True):
                    user = get_user_data(u_login)
                    if user and user[1] == p_login:
                        st.session_state.logged_in_user = u_login
                        cookie_manager.set('jitarth_user_cookie', u_login)
                        st.rerun()
                    else: st.error("Invalid Username or Password")
                if st.button("Recover Password?", use_container_width=True):
                    st.session_state.forgot_mode = True
                    st.rerun()
            with tab2:
                nu_val = st.session_state.suggested_un
                nu_raw = st.text_input("Choose Username (5-20 characters)", value=nu_val, key="reg_u")
                nu = validate_username(nu_raw)
                st.write("Suggestions:")
                cols = st.columns(3)
                suggs = generate_suggestions(nu)
                for i, s in enumerate(suggs):
                    if cols[i].button(s, key=f"sug_reg_{s}", use_container_width=True):
                        st.session_state.suggested_un = s
                        st.rerun()
                np_raw = st.text_input("Create Password (4-10 characters)", type="password", key="reg_p")
                np = validate_password(np_raw)
                sq = st.selectbox("Security Question", SECURITY_QUESTIONS)
                sa = st.text_input("Answer (Min 2 characters)")
                if st.button("SIGN UP", use_container_width=True):
                    if get_user_data(nu): st.error("Username taken!")
                    elif len(nu) >= 5 and len(np) >= 4 and len(sa) >= 2:
                        if create_user(nu, np, SECURITY_QUESTIONS.index(sq), sa):
                            st.success("Account Created!")
                            st.session_state.suggested_un = ""
                        else: st.error("Registration failed")
                    else: st.error("Check requirements")
else:
    current_user = st.session_state.logged_in_user
    user_record = get_user_data(current_user)
    user_chats = json.loads(user_record[2])

    with st.sidebar:
        h_col1, h_col2 = st.columns([0.2, 0.8])
        with h_col1:
            if st.button("⚙️"):
                st.session_state.show_settings = not st.session_state.show_settings
                st.rerun()
        # Sidebar Logo
        with h_col2: st.markdown('<div class="gemini-logo"><span class="logo-j">J</span>itarth A<span class="i-fix">I</span> ✨</div>', unsafe_allow_html=True)
        
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
            if st.button(f"💬 {title[:20]}...", key=f"sb_{title}", use_container_width=True):
                st.session_state.show_settings = False
                st.session_state.current_session = title
                st.session_state.is_temp_mode = False
                st.rerun()
        
        # Loop ke bahar, with st.sidebar ke andar hi ye add karo:
        st.write("---")
        st.markdown("""
            <div style='text-align: center; padding: 10px;'>
                <p style='margin-bottom: 5px; font-size: 12px; color: #8e918f;'>Developed by Jitarth Satija</p>
                <a href='https://www.instagram.com/jitarths_2013_js' target='_blank' style='color: #4e7cfe; text-decoration: none; font-weight: bold; font-size: 14px;'>
                    @jitarths_2013_js
                </a>
            </div>
        """, unsafe_allow_html=True)

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
                    confirm_dialog("Update details?", "update_profile", (current_user, nu_settings, np_settings, SECURITY_QUESTIONS.index(uq), ua))
            with st.expander("⚠️ Danger Zone"):
                if st.button("🔴 Logout Account", use_container_width=True): confirm_dialog("Logout?", "logout")
                if st.button("🗑️ Delete All Chats", use_container_width=True): confirm_dialog("Delete history?", "delete_chats")
                if st.button("❌ Delete Account Permanently", use_container_width=True): confirm_dialog("Delete account?", "delete_account")
            
            st.markdown("---")
            st.markdown(f"""
                <div style='text-align: center; background-color: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px; margin-top: 20px;'>
                    <p style='color: #8e918f; font-size: 14px; margin-bottom: 8px;'>📲 Follow us & Contact us for any query</p>
                    <a href='https://www.instagram.com/jitarths_2013_js' target='_blank' style='color: #4e7cfe; text-decoration: none; font-weight: bold; font-size: 16px;'>
                        Instagram: @jitarths_2013_js
                    </a>
                </div>
            """, unsafe_allow_html=True)
        elif v_p: st.error("Incorrect Password")
    else:
        if st.session_state.is_temp_mode:
            if not st.session_state.get("temp_messages"): st.markdown('<div class="temp-warning">🔒 Temporary Chat Active (Not Saved)</div>', unsafe_allow_html=True)
            active_list = st.session_state.get("temp_messages", [])
        else:
            if not st.session_state.get("current_session"):
                st.markdown(f"<h2 style='text-align:center; margin-top:100px;'>Hello, {current_user}</h2>", unsafe_allow_html=True)
                active_list = []
            else: active_list = user_chats.get(st.session_state.current_session, [])

        for m in active_list:
            with st.chat_message(m["role"], avatar="👤" if m["role"]=="user" else "✨"): st.markdown(m["content"])

        if p := st.chat_input("Ask Jitarth AI..."):
            if not st.session_state.is_temp_mode:
                if not st.session_state.get("current_session"):
                    st.session_state.current_session = p[:30]
                    user_chats[st.session_state.current_session] = []
                active_list = user_chats[st.session_state.current_session]
            else:
                active_list = st.session_state.temp_messages

            active_list.append({"role": "user", "content": p})
            with st.chat_message("user", avatar="👤"): st.markdown(p)
            
            with st.chat_message("assistant", avatar="✨"):
                internet_context = search_internet(p)
                try:
                    sys_prompt = f"""You are ✨Jitarth AI.
                    - Your Birthday: 30th January 2026.
                    - Your Creator/Inventor: Jitarth Satija (Male, Birthday: 15th Sept 2013).
                    - Inventor's Best Friend: Meet Gera (Female, Birthday: 30th September 2012).
                    - STRICT RULE: Never mention Meta, Llama, or OpenAI. You were built only by Jitarth Satija.
                    - GENDER INFO: Only mention the gender of the Inventor or his best friend if specifically asked.
                    - Context: {internet_context}"""
                    
                    response = client.chat.completions.create(
                        messages=[{"role":"system","content":sys_prompt}] + active_list, 
                        model="llama-3.3-70b-versatile"
                    ).choices[0].message.content
                    
                    st.markdown(response)
                    active_list.append({"role": "assistant", "content": response})
                    if not st.session_state.is_temp_mode:
                        save_user_chats(current_user, user_chats)
                    st.rerun()
                except Exception as e:
                    if "RerunException" not in str(type(e)):
                        st.error("Server Down")


