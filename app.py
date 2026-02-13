import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from authlib.integrations.flask_client import OAuth
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key")

# Configure Session to use Filesystem (for development)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/infinity_hackers")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_default_database()
users_collection = db.users

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
        # Mock Data for Dashboard
        user_stats = {
            "level": 1,
            "xp_percentage": 0,
            "courses_completed": 0,
            "hours_learned": 0,
            "streak": 0
        }
        
        daily_goals = [
            {"task": "Complete 1 Python Lesson", "completed": False},
            {"task": "Solve 2 Coding Challenges", "completed": False},
            {"task": "Post in Community Forum", "completed": False}
        ]
        
        learning_path = [
            {"title": "Intro to Python", "description": "Basics of Python programming", "status": "in-progress", "progress": 0, "icon": "🐍"},
            {"title": "Data Structures", "description": "Lists, Dictionaries, Sets", "status": "locked", "progress": 0, "icon": "📊"},
            {"title": "Web Development", "description": "Flask, Django", "status": "locked", "progress": 0, "icon": "🌐"},
            {"title": "Machine Learning", "description": "Scikit-learn, TensorFlow", "status": "locked", "progress": 0, "icon": "🤖"},
            {"title": "C Language", "description": "Pointers, Memory Management", "status": "locked", "progress": 0, "icon": "💻"}
        ]
        
        recent_activity = [
            {"date": "Today", "items": [
                {"time": "Now", "description": "Joined LearnoSphere! 🚀"}
            ]}
        ]
        
        notifications = [
            {"message": "Welcome to LearnoSphere! Start your first lesson.", "time_ago": "Now", "read": False}
        ]

        return render_template('dashboard.html', user=session['user'], user_stats=user_stats, daily_goals=daily_goals, learning_path=learning_path, recent_activity=recent_activity, notifications=notifications)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        # Traditional login logic (placeholder)
        email = request.form.get('email')
        print(f"Login attempt: {email}")
        
        # Mock successful login
        session['user'] = {
            "name": "Test User",
            "email": email,
            "picture": "https://ui-avatars.com/api/?name=Test+User&background=random"
        }
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        # Traditional signup logic (placeholder)
        username = request.form.get('username')
        print(f"Signup attempt: {username}")
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
        {"title": "Python for Beginners", "description": "Learn the basics of Python programming language.", "progress": 0, "status": "in-progress", "icon": "🐍"},
        {"title": "Data Structures", "description": "Master common data structures like Lists and Trees.", "progress": 0, "status": "locked", "icon": "📊"},
        {"title": "Web Development", "description": "Build modern web applications with Flask and React.", "progress": 0, "status": "locked", "icon": "🌐"},
        {"title": "Machine Learning", "description": "Introduction to AI, Scikit-learn, and Neural Networks.", "progress": 0, "status": "locked", "icon": "🤖"},
        {"title": "C Language", "description": "Deep dive into low-level programming and memory management.", "progress": 0, "status": "locked", "icon": "💻"}
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
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""You are an expert Machine Learning professor and AI tutor.

Your task is to teach the concept: "{topic}"

Learner Level: "{level}" 

Follow these strict instructions:

1. Start with a 2-3 line simple summary.
2. Then explain using real-world analogy.
3. Then provide technical explanation.
4. Then provide mathematical formulation (if applicable, use LaTeX format).
5. Then explain step-by-step working of the algorithm/concept.
6. Then give clean Python implementation with comments (use sklearn if ML-related).
7. Then give one real-world practical use case.
8. Then provide advantages and disadvantages.
9. Then generate 3 conceptual quiz questions with answers.
10. Then give 1 small coding challenge with solution.

Formatting Rules:
- Use clear section headings.
- Use bullet points where needed.
- Keep explanation structured and readable.
- Avoid unnecessary repetition.
- Adapt difficulty based on learner level:
    - Beginner → Simple language, less math, more analogies.
    - Intermediate → Include formulas and intuition.
    - Advanced → Include derivations and optimization explanation.

Tone:
- Friendly but professional.
- Clear and confident.
- Like a personal AI mentor.

Provide your response in exactly this format:

SUMMARY:
[2-3 line simple summary]

ANALOGY:
[Real-world analogy]

TECHNICAL:
[Technical explanation]

MATH:
[Mathematical formulation in LaTeX, or "N/A" if not applicable]

STEPS:
[Step-by-step working]

CODE:
[Python implementation]

USECASE:
[Real-world use case]

PROS_CONS:
[Advantages and Disadvantages]

QUIZ:
[3 quiz questions with answers]

CHALLENGE:
[Coding challenge with solution]

Do not skip any section. Make it educational and comprehensive."""
            
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Parse the structured response
            def extract_section(text, start_marker, end_marker=None):
                try:
                    start_idx = text.find(start_marker)
                    if start_idx == -1:
                        return ""
                    start_idx += len(start_marker)
                    
                    if end_marker:
                        end_idx = text.find(end_marker, start_idx)
                        if end_idx == -1:
                            return text[start_idx:].strip()
                        return text[start_idx:end_idx].strip()
                    return text[start_idx:].strip()
                except:
                    return ""
            
            summary = extract_section(response_text, "SUMMARY:", "ANALOGY:")
            analogy = extract_section(response_text, "ANALOGY:", "TECHNICAL:")
            technical = extract_section(response_text, "TECHNICAL:", "MATH:")
            math = extract_section(response_text, "MATH:", "STEPS:")
            steps = extract_section(response_text, "STEPS:", "CODE:")
            code = extract_section(response_text, "CODE:", "USECASE:")
            usecase = extract_section(response_text, "USECASE:", "PROS_CONS:")
            pros_cons = extract_section(response_text, "PROS_CONS:", "QUIZ:")
            quiz = extract_section(response_text, "QUIZ:", "CHALLENGE:")
            challenge = extract_section(response_text, "CHALLENGE:")
            
            # Clean up math
            if "N/A" in math or "not applicable" in math.lower() or len(math.strip()) < 5:
                math = ""
            
            # Clean up code blocks
            code = code.replace("```python", "").replace("```", "").strip()
            challenge = challenge.replace("```python", "").replace("```", "").strip()
            
            if summary:  # If we successfully parsed
                return {
                    "summary": summary,
                    "analogy": analogy,
                    "technical": technical,
                    "math": math,
                    "steps": steps,
                    "code": code,
                    "usecase": usecase,
                    "pros_cons": pros_cons,
                    "quiz": quiz,
                    "challenge": challenge
                }
    except Exception as e:
        print(f"AI API Error: {e}")
    
    # Fallback mock response
    return {
        "summary": f"Unable to generate concept for '{topic}'. Please check your API key or try again.",
        "analogy": "AI service unavailable.",
        "technical": "The Concept Generator requires a valid Gemini API key to function.",
        "math": "",
        "steps": "1. Add GEMINI_API_KEY to .env file\n2. Restart the server\n3. Try again",
        "code": "# API key required",
        "usecase": "Educational learning platform",
        "pros_cons": "Advantages: AI-powered learning\nDisadvantages: Requires API key",
        "quiz": "Q1: What is needed? A: API key",
        "challenge": "# Set up your API key"
    }



@app.route('/tools/run-code', methods=['POST'])
def run_code():
    if 'user' not in session: return {"error": "Unauthorized"}, 401
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    
    if language == 'python':
        # Python execution
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()
        
        try:
            exec(code)
            output = redirected_output.getvalue()
            if not output:
                output = "// Code executed successfully (no output)"
        except Exception as e:
            output = f"Error: {str(e)}"
        finally:
            sys.stdout = old_stdout
            
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
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/google/callback')
def google_callback():
    google = oauth.create_client('google')  # create the google oauth client
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    
    # Store user in MongoDB
    user = users_collection.find_one({"email": user_info['email']})
    if not user:
        user = {
            "name": user_info['name'],
            "email": user_info['email'],
            "picture": user_info['picture'],
            "oauth_provider": "google"
        }
        users_collection.insert_one(user)
    
    # Store in session
    session['user'] = user_info
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
