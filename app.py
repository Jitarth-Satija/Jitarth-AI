import streamlit as st
from groq import Groq
import sqlite3
import json
from duckduckgo_search import DDGS
import re
import random
import string
import extra_streamlit_components as stx

# 1. Setup - API Key
api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)
cookie_manager = stx.CookieManager()

# 2. Deep News Search Function
def search_internet(query):
    try:
        with DDGS() as ddgs:
            deep_query = f"{query} detailed news report 2025 2026"
            results = [r for r in ddgs.news(deep_query, max_results=8)]
            if not results:
                results = [r for r in ddgs.text(deep_query, max_results=8)]
            if results:
                context = "\n".join([f"Source: {r['title']} - {r['body']}" for r in results])
                return context
            return "No live internet results found."
    except Exception as e:
        return f"Internet access error: {str(e)}"

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
    if u.count(' ') > 2: u = u[:u.rfind(' ')]
    if u.count('@') > 1: u = u[:u.rfind('@')]
    if u.count('_') > 1: u = u[:u.rfind('_')]
    return u[:20]

def validate_password(p):
    p = re.sub(r'[^a-zA-Z0-9@_]', '', p)
    if p.count('@') > 1: p = p[:p.rfind('@')]
    if p.count('_') > 1: p = p[:p.rfind('_')]
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
    .gemini-logo { font-family: 'Google Sans', sans-serif; font-size: 28px; font-weight: bold; background: linear-gradient(to right, #4e7cfe, #f06e9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; white-space: nowrap; }
    .gemini-logo::first-letter, .gemini-logo::after { font-size: 35px; }
    .sidebar-i-fix { font-size: 35px; }
    .login-logo-container { text-align: center; margin-top: 60px; margin-bottom: 40px; }
    .login-logo-text { font-family: 'Google Sans', sans-serif; font-size: 42px; font-weight: 800; background: linear-gradient(to right, #4e7cfe, #f06e9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; }
    .login-logo-text::first-letter { font-size: 55px; }
    .login-i-fix { font-size: 55px; }
    .login-star-fix { font-size: 55px; }
    .temp-warning { background-color: rgba(255, 75, 75, 0.1); border: 1px solid #ff4b4b; color: #ff4b4b; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .validation-text { font-size: 12px; color: #8e918f; margin-top: -15px; margin-bottom: 10px; }
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
            st.session_state.logged_in_user = None
        elif action_type == "update_profile":
            if update_user_credentials(*data): 
                st.session_state.logged_in_user = data[1]
                st.session_state.update_success = True
            else: 
                st.session_state.update_error = "Username already in use!"
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

# 8. Main UI Logic
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
if "is_temp_mode" not in st.session_state: st.session_state.is_temp_mode = False
if "show_settings" not in st.session_state: st.session_state.show_settings = False
if "suggested_un" not in st.session_state: st.session_state.suggested_un = ""
if "settings_un_sugg" not in st.session_state: st.session_state.settings_un_sugg = ""

saved_user = cookie_manager.get('jitarth_user_cookie')
if saved_user and st.session_state.logged_in_user is None:
    st.session_state.logged_in_user = saved_user

if st.session_state.logged_in_user is None:
    st.markdown('<div class="login-logo-container"><div class="login-logo-text">Jitarth A<span class="login-i-fix">I</span> <span class="login-star-fix">✨</span></div></div>', unsafe_allow_html=True)
    
    if st.session_state.get("forgot_mode"): 
        recovery_ui(False)
    else:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            u_login = st.text_input("Username", key="login_u")
            p_login = st.text_input("Password", type="password", key="login_p")
            keep_me_logged_in = st.checkbox("Keep me logged in")
            
            if st.button("Log In", use_container_width=True):
                user = get_user_data(u_login)
                if user and user[1] == p_login:
                    st.session_state.logged_in_user = u_login
                    if keep_me_logged_in:
                        cookie_manager.set('jitarth_user_cookie', u_login)
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
            
            if st.button("Recover Password?", use_container_width=True):
                st.session_state.forgot_mode = True
                st.rerun()

        with tab2:
            nu_val = st.session_state.suggested_un
            nu_raw = st.text_input("Choose Username (5 – 20 characters)", value=nu_val, key="reg_u")
            nu = validate_username(nu_raw)
            
            if len(nu) < 5: 
                st.markdown('<p class="validation-text" style="color:#ff4b4b;">Minimum 5 characters required</p>', unsafe_allow_html=True)
            else: 
                st.markdown(f'<p class="validation-text">{20 - len(nu)} characters left</p>', unsafe_allow_html=True)
            
            st.write("Suggestions:")
            cols = st.columns(3)
            suggs = generate_suggestions(nu)
            for i, s in enumerate(suggs):
                if cols[i].button(s, key=f"sug_reg_{s}", use_container_width=True):
                    st.session_state.suggested_un = s
                    st.rerun()

            np_raw = st.text_input("Create Password (4-10 characters)", type="password", key="reg_p")
            np = validate_password(np_raw)
            if len(np) < 4: 
                st.markdown('<p class="validation-text" style="color:#ff4b4b;">Minimum 4 characters required</p>', unsafe_allow_html=True)
            else: 
                st.markdown(f'<p class="validation-text">{10 - len(np)} characters left</p>', unsafe_allow_html=True)
            
            sq = st.selectbox("Security Question", SECURITY_QUESTIONS)
            sa = st.text_input("Answer (Min 2 characters)")
            
            if st.button("SIGN UP", use_container_width=True):
                if get_user_data(nu): 
                    st.error("Username is already in use!")
                elif len(nu) >= 5 and len(np) >= 4 and len(sa) >= 2:
                    if create_user(nu, np, SECURITY_QUESTIONS.index(sq), sa): 
                        st.success("Account Created!")
                        st.session_state.suggested_un = ""
                    else: 
                        st.error("Registration failed")
                else: 
                    st.error("Check requirements (User: 5, Pass: 4, Answer: 2)")

else:
    current_user = st.session_state.logged_in_user
    user_record = get_user_data(current_user)
    user_chats = json.loads(user_record[2])

    with st.sidebar:
        h_col1, h_col2 = st.columns([0.2, 0.8])
        with h_col1:
            if st.button("⚙️", key="top_settings_icon"):
                st.session_state.show_settings = not st.session_state.show_settings
                st.session_state.settings_recover_mode = False
                st.rerun()
        with h_col2:
            st.markdown('<div class="gemini-logo">Jitarth A<span class="sidebar-i-fix">I</span> ✨</div>', unsafe_allow_html=True)
        
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
            if st.button(f"💬 {title[:20]}...", key=f"sb_{title}", use_container_width=True):
                st.session_state.show_settings = False
                st.session_state.current_session = title
                st.session_state.is_temp_mode = False
                st.rerun()

    if st.session_state.show_settings:
        if st.session_state.get("settings_recover_mode"): 
            recovery_ui(True)
        else:
            st.title("⚙️ Account Settings")
            if st.button("Recover Password?"): 
                st.session_state.settings_recover_mode = True
                st.rerun()
            
            v_p = st.text_input("Enter Password to Unlock Settings", type="password")
            if v_p == user_record[1]:
                st.success("Settings Unlocked ✅")
                with st.expander("👤 Update Profile Information", expanded=True):
                    su_val = st.session_state.settings_un_sugg if st.session_state.settings_un_sugg else current_user
                    nu_raw_settings = st.text_input("New Username (5 – 20 characters)", value=su_val)
                    nu_settings = validate_username(nu_raw_settings)
                    
                    if len(nu_settings) < 5: 
                        st.markdown('<p class="validation-text" style="color:#ff4b4b;">Minimum 5 characters required</p>', unsafe_allow_html=True)
                    else: 
                        st.markdown(f'<p class="validation-text">{20 - len(nu_settings)} characters left</p>', unsafe_allow_html=True)
                    
                    st.write("Suggestions:")
                    scols = st.columns(3)
                    ssuggs = generate_suggestions(nu_settings)
                    for i, s in enumerate(ssuggs):
                        if scols[i].button(s, key=f"sug_set_{s}", use_container_width=True):
                            st.session_state.settings_un_sugg = s
                            st.rerun()
                    
                    st.write("")
                    np_raw_settings = st.text_input("New Password (4-10 characters)", value=user_record[1], type="password")
                    np_settings = validate_password(np_raw_settings)
                    if len(np_settings) < 4: 
                        st.markdown('<p class="validation-text" style="color:#ff4b4b;">Minimum 4 characters required</p>', unsafe_allow_html=True)
                    else: 
                        st.markdown(f'<p class="validation-text">{10 - len(np_settings)} characters left</p>', unsafe_allow_html=True)
                    
                    uq = st.selectbox("Security Question", SECURITY_QUESTIONS, index=user_record[3])
                    ua = st.text_input("Security Answer (Min 2 characters)", value=user_record[4])
                    
                    if st.button("Save Changes", use_container_width=True):
                        if len(nu_settings) >= 5 and len(np_settings) >= 4 and len(ua) >= 2:
                            confirm_dialog("Update profile details?", "update_profile", (current_user, nu_settings, np_settings, SECURITY_QUESTIONS.index(uq), ua))
                        else: 
                            st.error("Requirements not met!")
                
                with st.expander("⚠️ Danger Zone"):
                    if st.button("🔴 Logout Account", use_container_width=True): 
                        confirm_dialog("Logout?", "logout")
                    if st.button("🗑️ Delete All Chats", use_container_width=True): 
                        confirm_dialog("Delete history?", "delete_chats")
                    if st.button("❌ Delete Account Permanently", use_container_width=True): 
                        confirm_dialog("Delete account?", "delete_account")
            elif v_p: 
                st.error("Incorrect Password")
    else:
        # Chat Interface Logic
        if st.session_state.is_temp_mode:
            if not st.session_state.get("temp_messages"): 
                st.markdown('<div class="temp-warning">🔒 Temporary Chat Active</div>', unsafe_allow_html=True)
            messages = st.session_state.get("temp_messages", [])
        else:
            if not st.session_state.get("current_session"):
                st.markdown(f"<h2 style='text-align:center; margin-top:100px;'>Hello, {current_user}</h2>", unsafe_allow_html=True)
                messages = []
            else: 
                messages = user_chats[st.session_state.current_session]

        for m in messages:
            with st.chat_message(m["role"], avatar="👤" if m["role"]=="user" else "✨"): 
                st.markdown(m["content"])

        if p := st.chat_input("Ask Jitarth AI..."):
            if st.session_state.is_temp_mode:
                if "temp_messages" not in st.session_state: 
                    st.session_state.temp_messages = []
                active_list = st.session_state.temp_messages
            else:
                if not st.session_state.get("current_session"):
                    st.session_state.current_session = p[:30]
                    user_chats[st.session_state.current_session] = []
                active_list = user_chats[st.session_state.current_session]
            
            active_list.append({"role": "user", "content": p})
            with st.chat_message("user", avatar="👤"): 
                st.markdown(p)
            with st.chat_message("assistant", avatar="✨"):
                with st.status("🔍 Scanning Live Data...", expanded=False): 
                    internet_context = search_internet(p)
                sys_prompt = f"Your name is Jitarth AI, invented by Jitarth Satija. Current date: 2026. Use this context: {internet_context}"
                response = client.chat.completions.create(
                    messages=[{"role": "system", "content": sys_prompt}] + active_list, 
                    model="llama-3.3-70b-versatile"
                ).choices[0].message.content
                st.markdown(response)
                active_list.append({"role": "assistant", "content": response})
                if not st.session_state.is_temp_mode: 
                    save_user_chats(current_user, user_chats)
                st.rerun()
