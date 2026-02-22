Skip to content
Jitarth-Satija
Jitarth-AI
Repository navigation
Code
Issues
Pull requests
Actions
Projects
Security
Insights
Settings
Jitarth-AI
/
app.py
in
main

Edit

Preview
Indent mode

Spaces
Indent size

4
Line wrap mode

No wrap
Editing app.py file contents
set_page_config
nextpreviousallmatch caseregexpby word
Replace
replacereplace all×
current match. st.set_page_config(page_title="Jitarth AI" on line 97.
 50
 51
 52
 53
 54
 55
 56
 57
 58
 59
 60
 61
 62
 63
 64
 65
 66
 67
 68
 69
 70
 71
 72
 73
 74
 75
 76
 77
 78
 79
 80
 81
 82
 83
 84
 85
 86
 87
 88
 89
 90
 91
 92
 93
 94
 95
 96
 97
 98
 99
100
101
102
103
104
105
106
107
108
109
110
111
112
113
114
115
116
117
118
119
120
121
122
123
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
    return u

def validate_password(p):
    return p

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
st.set_page_config(page_title="Jitarth AI", page_icon="✨", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { 
        background-color: #131314 !important; /* Ye background ko ek jaisa kar dega */
        color: #e3e3e3; 
    }
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
Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
 
Copied!
