import streamlit as st
import sqlite3
import hashlib
from groq import Groq
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Jitarth AI Pro", page_icon="🛡️", layout="centered")

# --- API SETUP ---
api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("🚨 API Key missing in Secrets!")
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
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UI ---
st.title("🤖 Jitarth AI Pro")

if not st.session_state.logged_in:
    menu = ["Login", "Sign Up", "Forgot Password"]
    choice = st.sidebar.selectbox("Access Control", menu)

    if choice == "Login":
        st.subheader("Login to your AI")
        u = st.text_input("Username")
        p = st.text_input("Password", type='password')
        if st.button("Login"):
            if login_user(u, p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.success(f"Welcome back, {u}!")
                st.rerun()
            else:
                st.error("Galat hai bhai! Username ya Password check karo.")

    elif choice == "Sign Up":
        st.subheader("Create New Account")
        new_u = st.text_input("Choose Username (Min 4 chars)")
        new_p = st.text_input("Choose Password (Min 6 chars)", type='password')
        q = st.selectbox("Security Question", ["Your birth city?", "First pet name?", "Favorite teacher?"])
        a = st.text_input("Your Answer")
        
        if st.button("Register"):
            if len(new_u) < 4:
                st.warning("Username kam se kam 4 characters ka hona chahiye!")
            elif len(new_p) < 6:
                st.warning("Password kam se kam 6 characters ka hona chahiye!")
            elif not a:
                st.warning("Security answer zaroori hai!")
            else:
                try:
                    add_userdata(new_u, new_p, q, a)
                    st.success("Account ban gaya! Ab Login tab mein jao.")
                except:
                    st.error("Ye Username pehle se koi le chuka hai.")

    elif choice == "Forgot Password":
        st.subheader("Recover Account")
        ru = st.text_input("Enter Username")
        rq = st.selectbox("Your Security Question", ["Your birth city?", "First pet name?", "Favorite teacher?"])
        ra = st.text_input("Your Answer")
        if st.button("Show my Password"):
            if recover_password(ru, rq, ra):
                st.info("Identity Verified! Please set a new password via Database (Feature coming soon). For now, contact admin.")
            else:
                st.error("Details match nahi kar rahi!")

else:
    # --- CHAT INTERFACE ---
    st.sidebar.info(f"User: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if p := st.chat_input("Ask Jitarth AI..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        with st.chat_message("assistant"):
            try:
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "You are Jitarth AI, created by Jitarth Satija."}] + st.session_state.messages
                ).choices[0].message.content
                st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
            except Exception as e:
                st.error(f"Error: {e}")
