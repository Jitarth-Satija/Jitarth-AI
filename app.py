import streamlit as st
import sqlite3
import hashlib
from groq import Groq
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Jitarth AI", page_icon="🤖", layout="centered")

# --- API SETUP ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    api_key = os.getenv("GROQ_API_KEY")

client = Groq(api_key=api_key)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_userdata(username, password):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users(username, password) VALUES (?,?)", (username, password))
    conn.commit()

def login_user(username, password):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username =? AND password =?", (username, password))
    data = cursor.fetchall()
    return data

# --- SESSION STATE (The "Keep Logged In" Engine) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UI ---
st.title("🤖 Jitarth AI")

if not st.session_state.logged_in:
    menu = ["Login", "SignUp"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("Login Section")
        username = st.text_input("User Name")
        password = st.text_input("Password", type='password')
        
        # Keep me logged in checkbox (visual/logic placeholder)
        keep_me_logged_in = st.checkbox("Keep me logged in")
        
        if st.button("Login"):
            hashed_pswd = make_hashes(password)
            result = login_user(username, check_hashes(password, hashed_pswd))
            if result:
                st.session_state.logged_in = True
                st.session_state.username = username
                # If checked, session state remains active during the current browser session
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid Username/Password")

    elif choice == "SignUp":
        st.subheader("Create New Account")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')
        if st.button("Signup"):
            try:
                add_userdata(new_user, make_hashes(new_password))
                st.success("Account Created! Please Login.")
            except sqlite3.IntegrityError:
                st.error("Username already exists!")

else:
    # --- LOGGED IN AREA ---
    st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
    
    # Sidebar features
    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # Chat Interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask Jitarth AI anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                # Using the latest powerful llama model
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are Jitarth AI, a helpful and witty assistant created by Jitarth Satija."},
                        *st.session_state.messages
                    ],
                )
                response = completion.choices[0].message.content
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                # Specific check for API key issues
                if "Authentication" in str(e):
                    st.error("Groq API Key Error! Check your Streamlit Secrets.")
                else:
                    st.error(f"Error: {e}")
