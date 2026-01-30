import streamlit as st
import sqlite3
import hashlib
from groq import Groq
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Jitarth AI", page_icon="🤖", layout="centered")

# --- API SETUP ---
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("🚨 API Key missing! Check Secrets.")
    st.stop()
client = Groq(api_key=api_key)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT,
            security_question TEXT,
            answer TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_userdata(username, password, q, a):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users(username, password, security_question, answer) VALUES (?,?,?,?)", 
                   (username, make_hashes(password), q, make_hashes(a.lower())))
    conn.commit()

def login_user(username, password):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username =? AND password =?", (username, make_hashes(password)))
    return cursor.fetchall()

def recover_password(username, q, a):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username =? AND security_question =? AND answer =?", 
                   (username, q, make_hashes(a.lower())))
    return cursor.fetchall()

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UI: COLORFUL LOGO & TITLE (Wahi Purana Wala) ---
st.markdown("""
    <div style="text-align: center;">
        <img src="https://www.gstatic.com/lamda/images/favicon_v1_150160d13988654bc731.svg" width="80">
        <h1 style="background: -webkit-linear-gradient(#4285F4, #34A853, #FBBC05, #EA4335);
                   -webkit-background-clip: text;
                   -webkit-text-fill-color: transparent;
                   font-size: 60px; font-weight: bold; font-family: 'Google Sans';">
            Jitarth AI
        </h1>
        <p style="color: #5f6368; font-size: 20px;">Built by Jitarth Satija</p>
    </div>
""", unsafe_allow_html=True)

# --- MAIN LOGIC ---
if not st.session_state.logged_in:
    # Sidebar Navigation (As per your old design)
    st.sidebar.title("🔒 Security Gate")
    menu = ["Login", "SignUp", "Forgot Password"]
    choice = st.sidebar.selectbox("Choose Action", menu)

    if choice == "Login":
        st.markdown("### 🔑 Welcome Back!")
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')
        keep_me = st.checkbox("Keep me logged in") # Naya feature added
        
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Hello {username}, AI is ready!")
                st.rerun()
            else:
                st.error("Username ya Password galat hai!")

    elif choice == "SignUp":
        st.markdown("### 📝 Register New User")
        new_user = st.text_input("Username (Min 4 chars)")
        new_password = st.text_input("Password (Min 6 chars)", type='password')
        q = st.selectbox("Security Question", ["Your birth city?", "First pet name?", "Favorite teacher?"])
        a = st.text_input("Your Answer")
        
        if st.button("Signup"):
            if len(new_user) < 4:
                st.warning("Username chota hai!")
            elif len(new_password) < 6:
                st.warning("Password chota hai!")
            else:
                try:
                    add_userdata(new_user, new_password, q, a)
                    st.success("Account created! Ab login karo.")
                except:
                    st.error("Username already taken!")

    elif choice == "Forgot Password":
        st.markdown("### 🛡️ Account Recovery")
        user = st.text_input("Username")
        ques = st.selectbox("Select Question", ["Your birth city?", "First pet name?", "Favorite teacher?"])
        ans = st.text_input("Answer")
        if st.button("Verify Identity"):
            if recover_password(user, ques, ans):
                st.info("Identity Verified! Please contact Jitarth to reset.")
            else:
                st.error("Details match nahi kar rahi.")

else:
    # --- CHAT UI (Gemini Feel) ---
    st.sidebar.markdown(f"### 👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    if st.sidebar.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

    # Conversation Display
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask me anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "You are Jitarth AI, a helpful assistant."}] + st.session_state.messages
                )
                response = completion.choices[0].message.content
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"API Error: {e}")
