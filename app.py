import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from authlib.integrations.flask_client import OAuth
from pymongo import MongoClient
from dotenv import load_dotenv
import google.generativeai as genai
import requests
import json

# Load environment variables
load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Check for API Key
if not os.getenv("GEMINI_API_KEY"):
    print("--- WARNING: GEMINI_API_KEY not found in .env file! ---")
else:
    print("--- SUCCESS: GEMINI_API_KEY loaded successfully. ---")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key")

# Configure Session to use Filesystem (for development)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# MongoDB Configuration (Lazy initialization to avoid socket issues on Windows)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/infinity_hackers")
db = None
users_collection = None
python_progress_collection = None
web_progress_collection = None

def get_db():
    global db, users_collection, python_progress_collection, web_progress_collection
    if db is None:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000)
            db = client.get_default_database()
            users_collection = db.users
            python_progress_collection = db.python_progress
            web_progress_collection = db.web_progress
            print("--- MongoDB connection initialized successfully. ---")
        except Exception as e:
            print(f"--- WARNING: MongoDB connection failed: {e} ---")
            db = False # Mark as failed so we don't retry every time
    return db

# --- Dynamic Model Discovery ---
AVAILABLE_AI_MODELS = []
def discover_models():
    """Fetches available models from Google to avoid 404s."""
    global AVAILABLE_AI_MODELS
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return
    
    for api_version in ['v1beta', 'v1']:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_version}/models?key={api_key}"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if 'models' in data:
                for m in data['models']:
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        name = m['name'].replace('models/', '')
                        if name not in AVAILABLE_AI_MODELS:
                            AVAILABLE_AI_MODELS.append(name)
            if AVAILABLE_AI_MODELS: break # Stop if we found something
        except Exception:
            continue
    
    if AVAILABLE_AI_MODELS:
        print(f"--- Discovered {len(AVAILABLE_AI_MODELS)} AI Models: {AVAILABLE_AI_MODELS} ---")
    else:
        print("--- WARNING: No compatible AI models discovered. Check API key permissions. ---")

# --- Robust AI Helper Function ---
def call_gemini_v2(prompt):
    """
    Attempts to call Gemini API by iterating through discovered models
    and using both library and REST fallbacks.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: API Key not found. Please set GEMINI_API_KEY in .env"

    if not AVAILABLE_AI_MODELS:
        discover_models()

    # Priority models we want to try first (standardized names)
    priority_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro', 'gemini-1.0-pro']
    
    # Combined list: priorities first, then any other discovered models
    candidate_models = []
    for p in priority_models:
        if p in AVAILABLE_AI_MODELS: candidate_models.append(p)
    for m in AVAILABLE_AI_MODELS:
        if m not in candidate_models: candidate_models.append(m)
        
    # If discovery failed, use a hardcoded fallback list
    if not candidate_models:
        candidate_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro', 'gemini-1.0-pro']

    for model_name in candidate_models:
        # 1. Try Library with REST transport
        try:
            genai.configure(api_key=api_key, transport='rest')
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                print(f"--- AI Success with Library: {model_name} ---")
                return response.text
        except Exception as e:
            error_str = str(e)
            print(f"--- Library Skip ({model_name}): {error_str} ---")

        # 2. Try Direct REST API Call (Try v1beta then v1)
        for api_version in ['v1beta', 'v1']:
            try:
                url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"
                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 2048}
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp_data = resp.json()
                
                if 'candidates' in resp_data and len(resp_data['candidates']) > 0:
                    print(f"--- AI Success with REST ({api_version}): {model_name} ---")
                    return resp_data['candidates'][0]['content']['parts'][0]['text']
                else:
                    err_msg = resp_data.get('error', {}).get('message', 'No candidate')
                    print(f"--- REST Skip ({model_name} @ {api_version}): {err_msg} ---")
            except Exception as e:
                pass
    
    return "Error: All AI models failed. Please verify your API key is valid (active) and has 'Generative Language API' enabled in Google Cloud Console."

# --- Python Course Data ---
PYTHON_COURSE_TOPICS = [
    {
        "id": 1,
        "title": "Hello World",
        "explanation": "To print something in Python, we use the `print()` function. For example: `print('Hello, World!')`",
        "requirement": "The output must exactly be 'Hello, World!'",
        "starter_code": "# Write code to print Hello World\n",
        "validation_type": "output",
        "expected_output": "Hello, World!"
    },
    {
        "id": 2,
        "title": "Add Two Numbers",
        "explanation": "You can use variables to store numbers and the `+` operator to add them. Take input using `input()` or just assign values.",
        "requirement": "Take two numbers (e.g., 5 and 10) and print their sum (15).",
        "starter_code": "a = 5\nb = 10\n# Calculate and print sum\n",
        "validation_type": "output",
        "expected_output": "15"
    },
    {
        "id": 3,
        "title": "Even or Odd",
        "explanation": "Use the modulo operator `%` to check the remainder. `n % 2 == 0` means the number is even.",
        "requirement": "Check if number 7 is even or odd and print 'Odd'.",
        "starter_code": "n = 7\n# Check and print 'Even' or 'Odd'\n",
        "validation_type": "output",
        "expected_output": "Odd"
    },
    {
        "id": 4,
        "title": "Largest of Three Numbers",
        "explanation": "Use `if-elif-else` statements to compare numbers.",
        "requirement": "Find the largest among 10, 25, and 15 and print it.",
        "starter_code": "a, b, c = 10, 25, 15\n# Find and print the largest number\n",
        "validation_type": "output",
        "expected_output": "25"
    },
    {
        "id": 5,
        "title": "Factorial of a Number",
        "explanation": "The factorial of n is n * (n-1) * ... * 1. You can use a loop or recursion.",
        "requirement": "Calculate the factorial of 5 and print it (120).",
        "starter_code": "n = 5\n# Calculate factorial and print\n",
        "validation_type": "output",
        "expected_output": "120"
    },
    {
        "id": 6,
        "title": "Fibonacci Series",
        "explanation": "A series where each number is the sum of the two preceding ones: 0, 1, 1, 2, 3, 5, 8...",
        "requirement": "Print the first 5 Fibonacci numbers: 0 1 1 2 3",
        "starter_code": "n = 5\n# Print first 5 Fibonacci numbers separated by space\n",
        "validation_type": "output",
        "expected_output": "0 1 1 2 3"
    },
    {
        "id": 7,
        "title": "Prime Number Check",
        "explanation": "A prime number is only divisible by 1 and itself.",
        "requirement": "Check if 13 is prime and print 'Prime'.",
        "starter_code": "n = 13\n# Check and print 'Prime' or 'Not Prime'\n",
        "validation_type": "output",
        "expected_output": "Prime"
    },
    {
        "id": 8,
        "title": "Multiplication Table",
        "explanation": "Use a `for` loop to print the table of a number.",
        "requirement": "Print the table of 2 up to 2x5 (2, 4, 6, 8, 10) separated by newlines.",
        "starter_code": "n = 2\n# Print table up to 5\n",
        "validation_type": "output",
        "expected_output": "2\n4\n6\n8\n10"
    },
    {
        "id": 9,
        "title": "Reverse a Number",
        "explanation": "You can reverse a number by converting it to a string or using math operations.",
        "requirement": "Reverse 123 and print 321.",
        "starter_code": "num = 123\n# Reverse and print\n",
        "validation_type": "output",
        "expected_output": "321"
    },
    {
        "id": 10,
        "title": "Palindrome Number",
        "explanation": "A palindrome reads the same forwards and backwards.",
        "requirement": "Check if 121 is a palindrome and print 'Palindrome'.",
        "starter_code": "num = 121\n# Check and print\n",
        "validation_type": "output",
        "expected_output": "Palindrome"
    },
    {
        "id": 11,
        "title": "Count Vowels",
        "explanation": "Iterate through a string and check if each character is in 'aeiou'.",
        "requirement": "Count vowels in 'Hello World' and print the count (3).",
        "starter_code": "s = 'Hello World'\n# Count vowels and print\n",
        "validation_type": "output",
        "expected_output": "3"
    },
    {
        "id": 12,
        "title": "String Reverse",
        "explanation": "Use slicing `[::-1]` to reverse a string easily.",
        "requirement": "Reverse 'Python' and print 'nohtyP'.",
        "starter_code": "s = 'Python'\n# Reverse and print\n",
        "validation_type": "output",
        "expected_output": "nohtyP"
    },
    {
        "id": 13,
        "title": "Sum of Digits",
        "explanation": "Sum each digit of the number.",
        "requirement": "Find the sum of digits of 1234 and print 10.",
        "starter_code": "num = 1234\n# Sum digits and print\n",
        "validation_type": "output",
        "expected_output": "10"
    },
    {
        "id": 14,
        "title": "Armstrong Number",
        "requirement": "Check if 153 is an Armstrong number (1^3 + 5^3 + 3^3 = 153) and print 'Armstrong'.",
        "explanation": "A number that is the sum of its own digits each raised to the power of the number of digits.",
        "starter_code": "num = 153\n# Check and print\n",
        "validation_type": "output",
        "expected_output": "Armstrong"
    },
    {
        "id": 15,
        "title": "Simple Calculator",
        "explanation": "Implement basic arithmetic operations.",
        "requirement": "Perform 10 / 2 and print the result (5.0).",
        "starter_code": "a, b = 10, 2\n# Print division result\n",
        "validation_type": "output",
        "expected_output": "5.0"
    },
    {
        "id": 16,
        "title": "Find GCD",
        "explanation": "Greatest Common Divisor of two numbers.",
        "requirement": "Find GCD of 12 and 18 and print 6.",
        "starter_code": "import math\na, b = 12, 18\n# Find GCD and print\n",
        "validation_type": "output",
        "expected_output": "6"
    },
    {
        "id": 17,
        "title": "Find LCM",
        "explanation": "Least Common Multiple of two numbers.",
        "requirement": "Find LCM of 12 and 18 and print 36.",
        "starter_code": "import math\na, b = 12, 18\n# Find LCM and print (Hint: LCM = (a*b)/GCD)\n",
        "validation_type": "output",
        "expected_output": "36.0"
    },
    {
        "id": 18,
        "title": "Count Words",
        "explanation": "Split a sentence by spaces and count the length of the list.",
        "requirement": "Count words in 'Python is amazing' and print 3.",
        "starter_code": "s = 'Python is amazing'\n# Count words and print\n",
        "validation_type": "output",
        "expected_output": "3"
    },
    {
        "id": 19,
        "title": "Find Maximum in List",
        "explanation": "Use `max()` function or a loop.",
        "requirement": "Find max in [1, 5, 2, 8, 3] and print 8.",
        "starter_code": "nums = [1, 5, 2, 8, 3]\n# Find max and print\n",
        "validation_type": "output",
        "expected_output": "8"
    },
    {
        "id": 20,
        "title": "Remove Duplicates from List",
        "explanation": "Convert the list to a `set()` and back to a `list()`.",
        "requirement": "Remove duplicates from [1, 2, 2, 3, 3, 4] and print the result as a sorted list.",
        "starter_code": "nums = [1, 2, 2, 3, 3, 4]\n# Remove duplicates and print sorted list\n",
        "validation_type": "output",
        "expected_output": "[1, 2, 3, 4]"
    }
]

# --- Web (HTML) Course Data ---
WEB_COURSE_TOPICS = [
    {
        "id": 1,
        "title": "Introduction to HTML",
        "explanation": "HTML (HyperText Markup Language) is the standard language for creating web pages. It describes the structure of a page using elements like headings, paragraphs, and links.",
        "requirement": "Create a simple HTML line: 'Hello HTML'",
        "starter_code": "<!-- Type Hello HTML below -->\n",
        "validation_type": "content",
        "expected_content": "Hello HTML"
    },
    {
        "id": 2,
        "title": "Basic HTML Structure",
        "explanation": "Every HTML document starts with <!DOCTYPE html> and contains <html>, <head>, and <body> tags.",
        "requirement": "Create a basic structure with <html><body>Hi</body></html>",
        "starter_code": "<!DOCTYPE html>\n",
        "validation_type": "content",
        "expected_content": "<body>Hi</body>"
    },
    {
        "id": 3,
        "title": "HTML Elements & Tags",
        "explanation": "Elements consist of an opening tag, content, and a closing tag. Some tags are 'empty' like <br>.",
        "requirement": "Use a <p> tag to write 'I am a paragraph'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<p>I am a paragraph</p>"
    },
    {
        "id": 4,
        "title": "Text Formatting Tags",
        "explanation": "Use <h1> to <h6> for headings and <strong> for bold text.",
        "requirement": "Create an <h1> heading with the text 'My Website'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<h1>My Website</h1>"
    },
    {
        "id": 5,
        "title": "Links & Navigation",
        "explanation": "The <a> tag creates links. The 'href' attribute specifies the destination.",
        "requirement": "Create a link to 'https://google.com' with text 'Google'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "href=\"https://google.com\""
    },
    {
        "id": 6,
        "title": "Images",
        "explanation": "The <img> tag embeds images. It requires 'src' and 'alt' attributes.",
        "requirement": "Add an image tag with src='logo.png' and alt='Logo'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<img src=\"logo.png\" alt=\"Logo\">"
    },
    {
        "id": 7,
        "title": "Lists",
        "explanation": "<ul> is for unordered lists, and <ol> is for ordered lists. Use <li> for items.",
        "requirement": "Create an unordered list with one item: 'Coffee'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<ul><li>Coffee</li></ul>"
    },
    {
        "id": 8,
        "title": "Tables",
        "explanation": "Tables use <table>, <tr> (rows), and <td> (data cells).",
        "requirement": "Create a table with one row and one cell containing 'Data'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<table><tr><td>Data</td></tr></table>"
    },
    {
        "id": 9,
        "title": "Forms",
        "explanation": "Forms take user input using <input>, <label>, and <button>.",
        "requirement": "Create a text input with placeholder 'Enter Name'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<input type=\"text\" placeholder=\"Enter Name\">"
    },
    {
        "id": 10,
        "title": "HTML Attributes",
        "explanation": "Attributes provide extra info about elements, like 'id', 'class', or 'style'.",
        "requirement": "Create a <div> with id='main'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<div id=\"main\">"
    },
    {
        "id": 11,
        "title": "Semantic HTML",
        "explanation": "Tags like <header>, <footer>, and <section> give meaning to web structure.",
        "requirement": "Wrap a paragraph in a <section> tag.",
        "starter_code": "<p>Content</p>",
        "validation_type": "content",
        "expected_content": "<section><p>Content</p></section>"
    },
    {
        "id": 12,
        "title": "Multimedia",
        "explanation": "HTML5 allows embedding <audio> and <video> directly.",
        "requirement": "Add a <video> tag with src='video.mp4'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<video src=\"video.mp4\""
    },
    {
        "id": 13,
        "title": "Responsive Basics",
        "explanation": "The viewport meta tag and CSS help make sites look good on mobile.",
        "requirement": "Add the viewport meta tag for mobile responsiveness.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "name=\"viewport\" content=\"width=device-width"
    },
    {
        "id": 14,
        "title": "HTML5 Features",
        "explanation": "HTML5 introduced <canvas>, <svg>, and better form inputs.",
        "requirement": "Create a <canvas> element.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "<canvas id=\"myCanvas\"></canvas>"
    },
    {
        "id": 15,
        "title": "SEO & Best Practices",
        "explanation": "Good SEO uses proper heading hierarchy and alt tags.",
        "requirement": "Write a meta description tag with content='Easy learning'.",
        "starter_code": "",
        "validation_type": "content",
        "expected_content": "name=\"description\" content=\"Easy learning\""
    },
    {
        "id": 16,
        "title": "Mini Projects (Practice)",
        "explanation": "Apply everything you've learned to build a personal profile.",
        "requirement": "Create an <h1> Profile and a <p> about yourself.",
        "starter_code": "<!-- Build your Mini Profile here -->\n",
        "validation_type": "content",
        "expected_content": "<h1>Profile</h1>"
    }
]

# OAuth Configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only needed if using openId connect
    client_kwargs={'scope': 'openid email profile'},
)

@app.route('/')
def home():
    if 'user' in session:
        user_email = session['user']['email']
        
        # Safe check for MongoDB
        completed_ids = []
        if python_progress_collection is not None:
            try:
                progress_doc = python_progress_collection.find_one({"email": user_email})
                completed_ids = progress_doc.get('completed_topics', []) if progress_doc else []
            except Exception as e:
                print(f"DB Error in home: {e}")
        
        # Merge with session-based progress (fallback/local)
        session_completed = session.get('python_completed_topics', [])
        completed_ids = list(set(completed_ids + session_completed))
        
        total_topics = len(PYTHON_COURSE_TOPICS)
        python_progress = int((len(completed_ids) / total_topics) * 100) if total_topics > 0 else 0

        # Web Course Progress
        web_completed_ids = []
        if web_progress_collection is not None:
            try:
                web_progress_doc = web_progress_collection.find_one({"email": user_email})
                web_completed_ids = web_progress_doc.get('completed_topics', []) if web_progress_doc else []
            except Exception as e:
                print(f"DB Error in home (web): {e}")
        
        session_web_completed = session.get('web_completed_topics', [])
        web_completed_ids = list(set(web_completed_ids + session_web_completed))
        
        web_total = len(WEB_COURSE_TOPICS)
        web_progress = int((len(web_completed_ids) / web_total) * 100) if web_total > 0 else 0

        # Mock Data for Dashboard
        user_stats = {
            "level": (len(completed_ids) // 2) + 1,
            "xp_percentage": (len(completed_ids) % 2) * 50,
            "courses_completed": 1 if python_progress == 100 else 0,
            "hours_learned": len(completed_ids) * 0.5,
            "streak": 1
        }
        
        daily_goals = [
            {"task": "Complete 1 Python Lesson", "completed": len(completed_ids) > 0},
            {"task": "Solve 2 Coding Challenges", "completed": len(completed_ids) > 1},
            {"task": "Post in Community Forum", "completed": False}
        ]
        
        learning_path = [
            {"title": "Python Mastery", "description": "Basics to advanced Python", "status": "unlocked" if python_progress == 0 else ("in-progress" if python_progress < 100 else "completed"), "progress": python_progress, "icon": "🐍", "link": "/courses/python"},
            {"title": "Web Development", "description": "HTML, CSS, JS Basics", "status": "unlocked" if web_progress == 0 else ("in-progress" if web_progress < 100 else "completed"), "progress": web_progress, "icon": "🌐", "link": "/courses/web"},
            {"title": "C Language", "description": "Pointers, Memory Management", "status": "locked", "progress": 0, "icon": "💻"},
            {"title": "Data Structures", "description": "Lists, Dictionaries, Sets", "status": "locked", "progress": 0, "icon": "📊"},
            {"title": "Machine Learning", "description": "Scikit-learn, TensorFlow", "status": "locked", "progress": 0, "icon": "🤖"}
        ]
        
        recent_activity = [
            {"date": "Today", "items": [
                {"time": "Now", "description": f"Completed {len(completed_ids)} Python topics! 🚀"}
            ]}
        ]
        
        notifications = [
            {"message": "Welcome back! Keep up the great work in your Python course.", "time_ago": "Now", "read": False}
        ]

        return render_template('dashboard.html', user=session['user'], user_stats=user_stats, daily_goals=daily_goals, learning_path=learning_path, recent_activity=recent_activity, notifications=notifications)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Try to find user in MongoDB
        user = None
        if users_collection is not None:
            try:
                user = users_collection.find_one({"email": email, "password": password})
            except Exception as e:
                print(f"DB Error in login: {e}")
                
        # Fallback to local session users (for demo/offline)
        if not user:
            local_users = session.get('local_users', [])
            user = next((u for u in local_users if u['email'] == email and u['password'] == password), None)
            
        if user:
            session['user'] = {
                "name": user.get('name', user.get('username', 'Student')),
                "email": user['email'],
                "picture": user.get('picture', f"https://ui-avatars.com/api/?name={user.get('name', user.get('username', 'Student'))}&background=random")
            }
            return redirect(url_for('home'))
        else:
            return "Invalid email or password", 401
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        new_user = {
            "name": username,
            "email": email,
            "password": password,
            "picture": f"https://ui-avatars.com/api/?name={username}&background=random"
        }
        
        # Save to MongoDB if available
        success = False
        if users_collection is not None:
            try:
                if users_collection.find_one({"email": email}):
                    return "Email already exists", 400
                users_collection.insert_one(new_user)
                success = True
            except Exception as e:
                print(f"DB Error in signup: {e}")
        
        # Always fallback save to session for currently running instance stability
        if 'local_users' not in session:
            session['local_users'] = []
        
        # Check if email exists in local store
        if any(u['email'] == email for u in session['local_users']):
             return "Email already exists", 400
             
        session['local_users'].append(new_user)
        session.modified = True
        
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- Dashboard Functionality Routes ---
@app.route('/courses')
def courses():
    if 'user' not in session: return redirect(url_for('login'))
    
    all_courses = [
        {"title": "Python for Beginners", "description": "Learn the basics of Python programming language.", "progress": 0, "status": "unlocked", "icon": "🐍"},
        {"title": "Web Development", "description": "Build modern web applications with HTML, CSS, and JS.", "progress": 0, "status": "unlocked", "icon": "🌐"},
        {"title": "C Language", "description": "Deep dive into low-level programming and memory management.", "progress": 0, "status": "locked", "icon": "💻"},
        {"title": "Data Structures", "description": "Master common data structures like Lists and Trees.", "progress": 0, "status": "locked", "icon": "📊"},
        {"title": "Machine Learning", "description": "Introduction to AI, Scikit-learn, and Neural Networks.", "progress": 0, "status": "locked", "icon": "🤖"}
    ]
    
    return render_template('courses.html', user=session['user'], courses=all_courses)

@app.route('/community')
def community():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('community.html', user=session['user'])

@app.route('/settings')
def settings():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('settings.html', user=session['user'])

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        # Update user session data logic (mock)
        session['user']['name'] = request.form.get('name')
        session['user']['bio'] = request.form.get('bio')
        session.modified = True 
        return redirect(url_for('home')) # Redirect back to dashboard after save
    return render_template('edit_profile.html', user=session['user'])

@app.route('/ai-tutor')
def ai_tutor():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('ai_tutor.html', user=session['user'])

@app.route('/ai-tutor/chat', methods=['POST'])
def ai_tutor_chat():
    if 'user' not in session: return {"error": "Unauthorized"}, 401
    
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return {"error": "Message is required"}, 400
        
    # Initialize chat history in session if not exists
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    # Keep only last 10 messages for context
    history = session['chat_history'][-10:]
    
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            # Construct context-aware prompt
            history_context = ""
            for msg in history:
                role = "Student" if msg['role'] == 'user' else "LearnoSphere AI"
                history_context += f"{role}: {msg['content']}\n"
            
            prompt = f"""You are 'LearnoSphere AI', a friendly and expert AI Tutor.
            
Your goal is to help students learn coding, machine learning, and computer science concepts.
The student's name is '{session['user'].get('name', 'Student')}'.

Previous Conversation:
{history_context}

Current Student Message: "{user_message}"

Follow these rules:
1. Be encouraging and patient.
2. If the user asks a question, explain it clearly with examples.
3. If they provide code with bugs, help them find and fix them (don't just give the answer immediately, guide them).
4. Use markdown for formatting code blocks, bold text, and lists.
5. Keep responses conversational, concise but comprehensive, like ChatGPT or Gemini.
6. If the question is not related to learning or computer science, politely steer them back to educational topics.

Provide a helpful, educational response."""

            ai_response = call_gemini_v2(prompt)
            
            if ai_response.startswith("Error"):
                return {"error": ai_response}, 500

            if ai_response.startswith("Error"):
                return {"error": ai_response}, 500
            
            # Update history in session
            session['chat_history'].append({"role": "user", "content": user_message})
            session['chat_history'].append({"role": "bot", "content": ai_response})
            session.modified = True
            
            return {"response": ai_response}
            
    except Exception as e:
        print(f"AI Tutor API Error: {e}")
        return {"error": "I'm having trouble connecting to my brain right now. Please try again later."}, 500

    return {"response": "My apologies, but my AI services are currently offline. Please check your configuration."}

# --- Learning Tools Routes ---
# Redirect /tools to concept-generator for backward compatibility
@app.route('/tools')
def tools_redirect():
    return redirect(url_for('concept_generator'))

@app.route('/tools/concept-generator')
def concept_generator():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('concept_generator.html', user=session['user'])

@app.route('/tools/code-playground')
def code_playground():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('code_playground.html', user=session['user'])

@app.route('/tools/visuals')
def visual_learning():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('visual_learning.html', user=session['user'])

@app.route('/tools/audio-player')
def audio_player():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('audio_player.html', user=session['user'])

# --- Python Course Routes ---
@app.route('/courses/python')
def python_course():
    if 'user' not in session: return redirect(url_for('login'))
    
    user_email = session['user']['email']
    
    completed_ids = []
    if python_progress_collection is not None:
        try:
            progress = python_progress_collection.find_one({"email": user_email})
            completed_ids = progress.get('completed_topics', []) if progress else []
        except Exception as e:
            print(f"DB Error in python_course: {e}")
    
    # Merge with session-based progress
    session_completed = session.get('python_completed_topics', [])
    completed_ids = list(set(completed_ids + session_completed))
    
    # Calculate progress percentage
    total_topics = len(PYTHON_COURSE_TOPICS)
    completed_count = len(completed_ids)
    progress_percent = int((completed_count / total_topics) * 100) if total_topics > 0 else 0
    
    # Mark topics as locked/unlocked
    topics_with_status = []
    for topic in PYTHON_COURSE_TOPICS:
        status = "locked"
        t_id = int(topic['id'])
        if t_id <= 2 or t_id in completed_ids or (t_id - 1) in completed_ids:
            status = "unlocked"
        if t_id in completed_ids:
            status = "completed"
            
        topics_with_status.append({**topic, "status": status})
        
    return render_template('python_course.html', 
                           user=session['user'], 
                           topics=topics_with_status, 
                           progress=progress_percent)

@app.route('/courses/python/topic/<int:topic_id>')
def python_topic(topic_id):
    if 'user' not in session: return redirect(url_for('login'))
    
    topic = next((t for t in PYTHON_COURSE_TOPICS if t['id'] == topic_id), None)
    if not topic:
        return "Topic not found", 404
        
    user_email = session['user']['email']
    completed_ids = []
    if python_progress_collection is not None:
        try:
            progress = python_progress_collection.find_one({"email": user_email})
            completed_ids = progress.get('completed_topics', []) if progress else []
        except Exception as e:
            print(f"DB Error in python_topic: {e}")
    
    # Merge with session
    session_completed = session.get('python_completed_topics', [])
    completed_ids = list(set(completed_ids + session_completed))
    
    # Check if unlocked
    if topic_id > 2 and (topic_id - 1) not in completed_ids and topic_id not in completed_ids:
        return redirect(url_for('python_course'))
        
    return render_template('python_topic.html', user=session['user'], topic=topic)

@app.route('/courses/python/verify', methods=['POST'])
def verify_python_topic():
    if 'user' not in session: return {"error": "Unauthorized"}, 401
    
    data = request.get_json()
    try:
        topic_id = int(data.get('topic_id'))
        code = data.get('code', '')
    except (ValueError, TypeError):
        return {"error": "Invalid topic ID"}, 400
    
    topic = next((t for t in PYTHON_COURSE_TOPICS if t['id'] == topic_id), None)
    if not topic: return {"error": "Topic not found"}, 404
    
    # Execute code and capture output (similar to run_code)
    import io, contextlib, math, random
    f = io.StringIO()
    success = False
    output = ""
    error = None
    
    with contextlib.redirect_stdout(f):
        try:
            exec_globals = {"math": math, "random": random}
            exec(code, exec_globals)
            output = f.getvalue().strip()
        except Exception as e:
            error = str(e)
            
    # Simple validation based on expected output
    expected = str(topic.get('expected_output', '')).strip()
    
    if error:
        message = f"Execution Error: {error}"
    elif output == expected:
        success = True
        message = "Perfect! You've completed this topic."
        
        # Update session progress anyway (fallback/live update)
        if 'python_completed_topics' not in session:
            session['python_completed_topics'] = []
        if topic_id not in session['python_completed_topics']:
            session['python_completed_topics'].append(topic_id)
            session.modified = True

        # Update progress in DB if available
        if python_progress_collection is not None:
            try:
                user_email = session['user']['email']
                python_progress_collection.update_one(
                    {"email": user_email},
                    {"$addToSet": {"completed_topics": topic_id}},
                    upsert=True
                )
            except Exception as e:
                print(f"DB Error in verify: {e}")
        else:
            message += " (Your progress is saved in your current session!)"
    else:
        # Get AI suggestion if it doesn't match
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                ai_model = genai.GenerativeModel('gemini-1.5-flash')
                ai_prompt = f"""The student is trying to solve: '{topic['title']}'
                Requirement: {topic['requirement']}
                Their code:
                ```python
                {code}
                ```
                Actual output: '{output}'
                Expected output: '{expected}'
                
                The output did not match exactly. Provide a very brief (1-2 sentence) hint or suggestion to help them fix it. Do NOT give the full code answer."""
                ai_response = ai_model.generate_content(ai_prompt)
                suggestion = ai_response.text
            else:
                suggestion = f"Expected '{expected}', but got '{output}'. Check your logic!"
        except:
            suggestion = f"Expected '{expected}', but got '{output}'. Check your logic!"
            
        message = f"Not quite. {suggestion}"

    return {
        "success": success,
        "message": message,
        "output": output if not error else f"Error: {error}"
    }

# --- Web Course Routes ---
@app.route('/courses/web')
def web_course():
    if 'user' not in session: return redirect(url_for('login'))
    
    user_email = session['user']['email']
    
    completed_ids = []
    if web_progress_collection is not None:
        try:
            progress = web_progress_collection.find_one({"email": user_email})
            completed_ids = progress.get('completed_topics', []) if progress else []
        except Exception as e:
            print(f"DB Error in web_course: {e}")
    
    session_completed = session.get('web_completed_topics', [])
    completed_ids = list(set(completed_ids + session_completed))
    
    total_topics = len(WEB_COURSE_TOPICS)
    completed_count = len(completed_ids)
    progress_percent = int((completed_count / total_topics) * 100) if total_topics > 0 else 0
    
    topics_with_status = []
    for topic in WEB_COURSE_TOPICS:
        status = "locked"
        t_id = int(topic['id'])
        # Two topics open for beginners (id 1 and 2)
        if t_id <= 2 or t_id in completed_ids or (t_id - 1) in completed_ids:
            status = "unlocked"
        if t_id in completed_ids:
            status = "completed"
            
        topics_with_status.append({**topic, "status": status})
        
    return render_template('web_course.html', 
                           user=session['user'], 
                           topics=topics_with_status, 
                           progress=progress_percent)

@app.route('/courses/web/topic/<int:topic_id>')
def web_topic(topic_id):
    if 'user' not in session: return redirect(url_for('login'))
    
    topic = next((t for t in WEB_COURSE_TOPICS if t['id'] == topic_id), None)
    if not topic:
        return "Topic not found", 404
        
    user_email = session['user']['email']
    completed_ids = []
    if web_progress_collection is not None:
        try:
            progress = web_progress_collection.find_one({"email": user_email})
            completed_ids = progress.get('completed_topics', []) if progress else []
        except Exception as e:
            print(f"DB Error in web_topic: {e}")
    
    session_completed = session.get('web_completed_topics', [])
    completed_ids = list(set(completed_ids + session_completed))
    
    # Check if unlocked (first 2 topics or previous completed)
    if topic_id > 2 and (topic_id - 1) not in completed_ids and topic_id not in completed_ids:
        return redirect(url_for('web_course'))
        
    return render_template('web_topic.html', user=session['user'], topic=topic)

@app.route('/courses/web/verify', methods=['POST'])
def verify_web_topic():
    if 'user' not in session: return {"error": "Unauthorized"}, 401
    
    data = request.get_json()
    try:
        topic_id = int(data.get('topic_id'))
        code = data.get('code', '')
    except (ValueError, TypeError):
        return {"error": "Invalid topic ID"}, 400
    
    topic = next((t for t in WEB_COURSE_TOPICS if t['id'] == topic_id), None)
    if not topic: return {"error": "Topic not found"}, 404
    
    success = False
    message = ""
    
    if topic.get('validation_type') == 'content':
        expected = str(topic.get('expected_content', ''))
        if expected.lower() in code.lower():
            success = True
            message = "Great job! You've mastered this topic."
        else:
            message = f"Not quite. Make sure your code contains: '{expected}'"

    if success:
        if 'web_completed_topics' not in session:
            session['web_completed_topics'] = []
        if topic_id not in session['web_completed_topics']:
            session['web_completed_topics'].append(topic_id)
            session.modified = True

        if web_progress_collection is not None:
            try:
                user_email = session['user']['email']
                web_progress_collection.update_one(
                    {"email": user_email},
                    {"$addToSet": {"completed_topics": topic_id}},
                    upsert=True
                )
            except Exception as e:
                print(f"DB Error in web verify: {e}")

    return {
        "success": success,
        "message": message
    }

import sys
import io
import subprocess
import tempfile

@app.route('/tools/generate-concept', methods=['POST'])
def generate_concept():
    if 'user' not in session: return {"error": "Unauthorized"}, 401
    data = request.get_json()
    topic = data.get('topic', '')
    level = data.get('level', 'Intermediate')  # Beginner, Intermediate, or Advanced
    
    # Try to use actual AI if API key is available
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            prompt = f"""You are an expert AI tutor designed to teach programming and technical subjects.

Your task is to provide a comprehensive, clear, and highly educational explanation of the concept: "{topic}".

Follow these instructions:
1. Adapt the explanation to the Learner Level: "{level}".
2. Use clear section headings, bold text, and bullet points.
3. Provide working code examples if the topic is technical.
4. Use Markdown for all formatting (headers, bold, lists, code blocks).
5. Explain concepts using real-world analogies.
6. Include a few practice questions or a mini-challenge at the end.

Provide your response in a natural, conversational format similar to Google Gemini or ChatGPT."""
            
            ai_response = call_gemini_v2(prompt)
            if ai_response.startswith("Error"):
                return {"error": ai_response}, 500
            
            return {"response": ai_response}
    except Exception as e:
        print(f"AI API Error: {e}")
        return {"error": str(e)}, 500
    
    # Fallback in case of logic issues
    return {"error": "Unexpected error occurred"}, 500

@app.route('/tools/ai-code-gen', methods=['POST'])
def ai_code_gen():
    if 'user' not in session: return {"error": "Unauthorized"}, 401
    data = request.get_json()
    prompt = data.get('prompt', '')
    language = data.get('language', 'python')
    
    if not prompt:
        return {"error": "Prompt is required"}, 400
        
    ai_prompt = f"""You are an expert programmer. Generate a code snippet based on the following request: "{prompt}".
    Language: {language}
    
    Requirements:
    1. Only return the code itself.
    2. Do not include any explanations, markdown code blocks (like ```python), or extra text.
    3. Ensure the code is clean, working, and well-commented.
    4. If it's a snippet, make sure it's complete.
    
    Code:"""
    
    generated_code = call_gemini_v2(ai_prompt)
    
    if generated_code.startswith("Error"):
        return {"error": generated_code}, 500
        
    # Clean up any accidental markdown blocks
    if "```" in generated_code:
        # Try to extract content between triple backticks
        import re
        match = re.search(r'```(?:\w+)?\n(.*?)\n```', generated_code, re.DOTALL)
        if match:
            generated_code = match.group(1)
        else:
            generated_code = generated_code.replace("```", "")
            
    return {"code": generated_code.strip()}



@app.route('/tools/run-code', methods=['POST'])
def run_code():
    if 'user' not in session: return {"error": "Unauthorized"}, 401
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    
    if language == 'python':
        # Python execution
        import contextlib
        import math
        import random
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            try:
                # Provide a fresh dictionary for global and local scopes
                exec_globals = {
                    "math": math,
                    "random": random
                }
                exec(code, exec_globals)
                output = f.getvalue()
                if not output:
                    output = "// Code executed successfully (no output)"
            except Exception as e:
                output = f"Error: {str(e)}"
            
    elif language == 'c':
        # C execution (requires gcc)
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
                f.write(code)
                c_file = f.name
            
            exe_file = c_file.replace('.c', '.exe')
            
            # Compile
            compile_result = subprocess.run(
                ['gcc', c_file, '-o', exe_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if compile_result.returncode != 0:
                output = f"Compilation Error:\n{compile_result.stderr}"
            else:
                # Run
                run_result = subprocess.run(
                    [exe_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = run_result.stdout if run_result.stdout else "// Program executed successfully (no output)"
                if run_result.stderr:
                    output += f"\nWarnings/Errors:\n{run_result.stderr}"
            
            # Cleanup
            import os as os_module
            try:
                os_module.remove(c_file)
                if os_module.path.exists(exe_file):
                    os_module.remove(exe_file)
            except:
                pass
                
        except subprocess.TimeoutExpired:
            output = "Error: Code execution timed out (5 seconds limit)"
        except FileNotFoundError:
            output = "Error: GCC compiler not found. Please install MinGW or GCC to run C code."
        except Exception as e:
            output = f"Error: {str(e)}"
    else:
        output = f"Error: Unsupported language '{language}'"
        
    return {"output": output}


# Google OAuth Routes
@app.route('/google/login')
def google_login():
    google = oauth.create_client('google')
    # Using '_external=True' might resolve some callback URL issues on localhost
    redirect_uri = url_for('google_callback', _external=True)
    # Adding prompt='consent' can help if user session is stuck
    return google.authorize_redirect(redirect_uri, prompt='select_account')

@app.route('/google/callback')
def google_callback():
    google = oauth.create_client('google')
    try:
        token = google.authorize_access_token()
        resp = google.get('userinfo')
        user_info = resp.json()
    except Exception as e:
        print(f"OAuth Error: {e}")
        return f"OAuth Error: {str(e)}", 400
    
    email = user_info['email']
    
    # Check if user exists in DB
    user = None
    if users_collection is not None:
        try:
            user = users_collection.find_one({"email": email})
        except Exception as e:
            print(f"DB Error in google_callback: {e}")
            
    # Fallback to local session users
    if not user:
        local_users = session.get('local_users', [])
        user = next((u for u in local_users if u['email'] == email), None)
        
    if not user:
        # New Google User - Save with temporary name and flag for username setting
        new_user = {
            "name": user_info['name'],
            "email": email,
            "picture": user_info['picture'],
            "oauth_provider": "google",
            "needs_username": True
        }
        
        if users_collection is not None:
            try:
                users_collection.insert_one(new_user)
            except: pass
            
        if 'local_users' not in session:
            session['local_users'] = []
        session['local_users'].append(new_user)
        session.modified = True
        user = new_user
        
    # Store in session
    session['user'] = {
        "name": user.get('name', user_info.get('name', 'Student')),
        "email": email,
        "picture": user.get('picture', user_info.get('picture', ''))
    }
    
    if user.get('needs_username'):
        return redirect(url_for('set_username'))
        
    return redirect(url_for('home'))

@app.route('/set-username', methods=['GET', 'POST'])
def set_username():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        new_username = request.form.get('username')
        email = session['user']['email']
        
        # Update in DB
        if users_collection is not None:
            try:
                users_collection.update_one(
                    {"email": email},
                    {"$set": {"name": new_username, "needs_username": False}}
                )
            except: pass
            
        # Update in session
        session['user']['name'] = new_username
        
        # Update in local session users
        local_users = session.get('local_users', [])
        for u in local_users:
            if u['email'] == email:
                u['name'] = new_username
                u['needs_username'] = False
        session.modified = True
        
        return redirect(url_for('home'))
        
    return render_template('set_username.html', user=session['user'])

if __name__ == '__main__':
    with app.app_context():
        discover_models()
    app.run(debug=True)
