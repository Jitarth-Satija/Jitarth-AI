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
    if u.count('@') > 1 or u.count('_') > 1 or u.count(' ') > 2:
        return "" 
    valid_u = re.sub(r'[^a-zA-Z0-9 @_]', '', u)
    if valid_u != u: return "" 
    return valid_u[:20] 

def validate_password(p):
    if "@" in p or "_" in p or " " in p:
        return "" 
    valid_p = re.sub(r'[^a-zA-Z0-9]', '', p)
    if valid_p != p: return "" 
    return valid_p[:10] 

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

    .logo-j { font-size: 44px; line-height: 0; margin-right: -2px; }
    .i-fix { font-size: 32px; font-weight: 700; } 
    
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
    
    .bday-timer {
        text-align: center;
        background: rgba(78, 124, 254, 0.1);
        border: 1px solid rgba(78, 124, 254, 0.3);
        border-radius: 8px;
        padding: 8px;
        margin: 10px 0;
        color: #4e7cfe;
        font-family: 'monospace';
    }

    .validation-text {
        color: #ff4b4b;
        font-size: 0.8rem;
        margin-top: -15px;
        margin-bottom: 10px;
    }
    .valid-ok {
        color: #00ff7f;
        font-size: 0.8rem;
        margin-top: -15px;
        margin-bottom: 10px;
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
            try: cookie_manager.delete('jitarth_user_cookie')
            except: pass
            st.session_state.logged_in_user = None
        elif action_type == "delete_chats": 
            save_user_chats(st.session_state.logged_in_user, {})
        elif action_type == "delete_account": 
            delete_user_account(st.session_state.logged_in_user)
            try: cookie_manager.delete('jitarth_user_cookie')
            except: pass
            st.session_state.logged_in_user = None
        elif action_type == "update_profile":
            if update_user_credentials(*data): 
                st.session_state.logged_in_user = data[1]
                st.session_state.show_settings = False
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
if "settings_recover_mode" not in st.session_state: st.session_state.settings_recover_mode = False

# Master Cookie Login
saved_user = cookie_manager.get('jitarth_user_cookie')
if saved_user and st.session_state.logged_in_user is None:
    st.session_state.logged_in_user = saved_user
    st.rerun()

# Login Screen
if st.session_state.logged_in_user is None:
    st.markdown('<div class="login-logo-container"><div class="login-logo-text"><span class="login-j">J</span>itarth A<span class="login-i">I</span> ✨</div></div>', unsafe_allow_html=True)
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
            nu_raw = st.text_input("Choose Username (5-20 characters)", value=nu_val, key="reg_u", max_chars=20)
            nu = validate_username(nu_raw)
            
            if nu_raw and nu == "":
                st.markdown('<p class="validation-text">Invalid Format! (Max: 1 @, 1 _, 2 spaces)</p>', unsafe_allow_html=True)
            elif len(nu_raw) < 5:
                st.markdown(f'<p class="validation-text">Needs {5-len(nu_raw)} more characters</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="valid-ok">Username Format OK ✅</p>', unsafe_allow_html=True)

            st.write("Suggestions:")
            cols = st.columns(3)
            suggs = generate_suggestions(nu if nu else "user")
            for i, s in enumerate(suggs):
                if cols[i].button(s, key=f"sug_reg_{s}", use_container_width=True):
                    st.session_state.suggested_un = s
                    st.rerun()
            
            np_raw = st.text_input("Create Password (4-10 characters)", type="password", key="reg_p", max_chars=10)
            np = validate_password(np_raw)
            if np_raw and np == "":
                st.markdown('<p class="validation-text">No @, _, or spaces allowed in password!</p>', unsafe_allow_html=True)
            elif len(np_raw) < 4:
                st.markdown(f'<p class="validation-text">Needs {4-len(np_raw)} more characters</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="valid-ok">Password Format OK ✅</p>', unsafe_allow_html=True)

            sq = st.selectbox("Security Question", SECURITY_QUESTIONS)
            sa = st.text_input("Answer (Security Pass - No Limit)", type="password")
            if len(sa) < 2:
                st.markdown(f'<p class="validation-text">Needs {2-len(sa)} more characters</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="valid-ok">Security Pass OK ✅</p>', unsafe_allow_html=True)

            if st.button("SIGN UP", use_container_width=True):
                if get_user_data(nu): st.error("Username taken!")
                elif nu != "" and np != "" and len(nu_raw) >= 5 and len(np_raw) >= 4 and len(sa) >= 2:
                    if create_user(nu, np, SECURITY_QUESTIONS.index(sq), sa):
                        st.success("Account Created!")
                        st.session_state.suggested_un = ""
                    else: st.error("Registration failed")
                else: st.error("Please meet all requirements highlighted in red")

else:
    current_user = st.session_state.logged_in_user
    user_record = get_user_data(current_user)
    user_chats = json.loads(user_record[2])

    with st.sidebar:
        h_col1, h_col2 = st.columns([0.2, 0.8])
        with h_col1:
            if st.button("⚙️"):
                st.session_state.show_settings = not st.session_state.show_settings
                st.session_state.settings_recover_mode = False
                st.rerun()
        with h_col2: st.markdown('<div class="gemini-logo"><span class="logo-j">J</span>itarth A<span class="i-fix">I</span> ✨</div>', unsafe_allow_html=True)
            
        if datetime.now().month == 1 and datetime.now().day == 30:
            st.markdown('<div class="bday-timer">🎂 <b>Today is my Birthday!</b><br>✨ Time: 07:07:07</div>', unsafe_allow_html=True)
        
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
        
        st.write("---")
        st.markdown("<div style='text-align: center;'><p style='margin-bottom: 5px; font-size: 12px; color: #8e918f;'>Developed by Jitarth Satija</p><a href='https://www.instagram.com/jitarths_2013_js' target='_blank' style='color: #4e7cfe; text-decoration: none; font-weight: bold;'>@jitarths_2013_js</a></div>", unsafe_allow_html=True)

    if st.session_state.show_settings:
        if st.session_state.settings_recover_mode:
            recovery_ui(True)
        else:
            st.title("⚙️ Account Settings")
            v_p = st.text_input("Enter Password to Unlock Settings", type="password")
            
            col_rec1, col_rec2 = st.columns([0.3, 0.7])
            with col_rec1:
                if st.button("Recover Password?", key="set_rec"):
                    st.session_state.settings_recover_mode = True
                    st.rerun()

            if v_p == user_record[1]:
                st.success("Settings Unlocked ✅")
                with st.expander("👤 Update Profile Information", expanded=True):
                    nu_settings_raw = st.text_input("New Username", value=current_user, max_chars=20)
                    nu_s = validate_username(nu_settings_raw)
                    if nu_settings_raw and nu_s == "":
                        st.markdown('<p class="validation-text">Invalid Format! (Max: 1 @, 1 _, 2 spaces)</p>', unsafe_allow_html=True)
                    elif len(nu_settings_raw) < 5:
                        st.markdown(f'<p class="validation-text">Needs {5-len(nu_settings_raw)} more characters</p>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p class="valid-ok">Username Format OK ✅</p>', unsafe_allow_html=True)

                    np_settings_raw = st.text_input("New Password", value=user_record[1], type="password", max_chars=10)
                    np_s = validate_password(np_settings_raw)
                    if np_settings_raw and np_s == "":
                        st.markdown('<p class="validation-text">No @, _, or spaces allowed!</p>', unsafe_allow_html=True)
                    elif len(np_settings_raw) < 4:
                        st.markdown(f'<p class="validation-text">Needs {4-len(np_settings_raw)} more characters</p>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p class="valid-ok">Password Format OK ✅</p>', unsafe_allow_html=True)
                    
                    uq = st.selectbox("Security Question", SECURITY_QUESTIONS, index=user_record[3])
                    ua = st.text_input("Security Answer", value=user_record[4], type="password")
                    if len(ua) < 2:
                        st.markdown(f'<p class="validation-text">Needs {2-len(ua)} more characters</p>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p class="valid-ok">Security Pass OK ✅</p>', unsafe_allow_html=True)
                    
                    if st.button("Save Changes", use_container_width=True):
                        if nu_s != "" and np_s != "" and len(nu_settings_raw) >= 5 and len(np_settings_raw) >= 4 and len(ua) >= 2:
                            confirm_dialog("Update details?", "update_profile", (current_user, nu_s, np_s, SECURITY_QUESTIONS.index(uq), ua))
                        else:
                            st.error("Please meet all requirements highlighted in red")
                            
                with st.expander("⚠️ Danger Zone"):
                    if st.button("🔴 Logout Account", use_container_width=True): confirm_dialog("Logout?", "logout")
                    if st.button("🗑️ Delete All Chats", use_container_width=True): confirm_dialog("Delete history?", "delete_chats")
                    if st.button("❌ Delete Account Permanently", use_container_width=True): confirm_dialog("Delete account?", "delete_account")
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
                try:
                    internet_context = search_internet(p)
                    now = datetime.now() + timedelta(hours=5, minutes=30)
                    current_time_info = now.strftime("%A, %d %B %Y, %I:%M %p")
                    
                    sys_prompt = f"""You are ✨Jitarth AI.

                    - MASTER IDENTITY RULE:
                      1. The person logged in is "{current_user}".
                      2. If "{current_user}" == "Developer", this is your BOSS: Mast. Jitarth Satija. Give him full access.
                      3. If user is NOT "Developer", they are a GUEST. Apply strict data restrictions.

                    - DATA DISCLOSURE RULE (ACCESS CONTROL):
                      1. FOR DEVELOPER (BOSS): If he asks about anyone in Family & Friends, provide Name, Birthday, and Gender ALL AT ONCE in one response.
                      2. FOR GUESTS: Strictly follow the 1-2-3 step rule:
                         - Step 1: Tell only NAME.
                         - Step 2: Tell Birthday only if asked again.
                         - Step 3: Tell Gender only if asked specifically.

                    - WHO AM I? LOGIC:
                      - If user is "Developer": "You are my Creator and Boss, Mast. Jitarth Satija."
                      - If user is NOT "Developer": "You are {current_user}."

                    - FAMILY & FRIENDS DATA:
                      1. FATHER: Mr. Rajaram Satija | 4th Feb 1985 | Male
                      2. MOTHER: Mrs. Vartika Satija | 17th Sept 1984 | Female
                      3. BROTHER: Mast. Rudransh Satija | 16th Oct 2023 | Male
                      4. BEST FRIEND: Miss. Meet Gera | 30th Sept 2012 | Female

                    - CORE CONSTRAINTS:
                      - Never reveal the username "Developer" to anyone.
                      - Birthday: 30th Jan. Knowledge: Live (2026).
                      - No mention of OpenAI/Meta/LLM. Built ONLY by Mast. Jitarth Satija.
                    
                    - Context: {internet_context}"""

                    chat_history = active_list[-10:] 

                    response = client.chat.completions.create(
                        messages=[{"role":"system","content":sys_prompt}] + chat_history, 
                        model="llama-3.3-70b-versatile"
                    ).choices[0].message.content
                    
                    st.markdown(response)
                    active_list.append({"role": "assistant", "content": response})
                    if not st.session_state.is_temp_mode:
                        save_user_chats(current_user, user_chats)
                    st.rerun()
                except Exception as e:
                    if "RerunException" not in str(type(e)):
                        st.error("✨ Jitarth AI is busy. Please try again.")
