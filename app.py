import streamlit as st
import sqlite3
import hashlib
from groq import Groq
import os

# --- PAGE CONFIG (Original Style) ---
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

# --- UI - LOGO & TITLE (Original Look) ---
st.markdown("<h1 style='text-align: center;'>🤖 Jitarth AI</h1>", unsafe_content_ Wood=True)
st.markdown("<h4 style='text-align: center; color: gray;'>Your Personal Intelligent Assistant</h4>", unsafe_content_ Wood=True)

# --- MAIN LOGIC ---
if not st.session_state.logged_in:
    # Original Sidebar Menu
    st.sidebar.title("Navigation")
    menu = ["Login", "SignUp", "Forgot Password"]
    choice = st.sidebar.selectbox("Select Action", menu)

    if choice == "Login":
        st.subheader("Login Section")
        username = st.text_input("User Name")
        password = st.text_input("Password", type='password')
        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid Username/Password")

    elif choice == "SignUp":
        st.subheader("Create New Account")
        new_user = st.text_input("Username (Min 4 chars)")
        new_password = st.text_input("Password (Min 6 chars)", type='password')
        q = st.selectbox("Security Question", ["Your birth city?", "First pet name?", "Favorite teacher?"])
        a = st.text_input("Your Answer")
        
        if st.button("Signup"):
            if len(new_user) < 4:
                st.warning("Username bahut chota hai (Min 4)!")
            elif len(new_password) < 6:
                st.warning("Password kam se kam 6 characters ka ho!")
            else:
                try:
                    add_userdata(new_user, new_password, q, a)
                    st.success("Account Created! Please Login.")
                except:
                    st.error("Username already exists!")

    elif choice == "Forgot Password":
        st.subheader("Recover Password")
        user = st.text_input("Enter Username")
        ques = st.selectbox("Security Question", ["Your birth city?", "First pet name?", "Favorite teacher?"])
        ans = st.text_input("Your Answer")
        if st.button("Recover"):
            if recover_password(user, ques, ans):
                st.info("Verified! Your identity is confirmed. Contact Jitarth for reset.")
            else:
                st.error("Wrong Details!")

else:
    # --- LOGGED IN UI ---
    st.sidebar.success(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    if st.sidebar.button("Clear History"):
        st.session_state.messages = []
        st.rerun()

    # Chat UI
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask Jitarth AI..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "You are Jitarth AI, a witty assistant created by Jitarth Satija."}] + st.session_state.messages
                )
                response = completion.choices[0].message.content
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Error: {e}")
