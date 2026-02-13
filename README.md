# 🚀 LearnoSphere - AI-Powered Learning Platform

An intelligent learning platform with Google OAuth authentication, AI-powered concept generation, interactive code playground, and comprehensive course management.

## ✨ Features

- 🔐 **Google OAuth Authentication** - Secure login with Google
- 🧠 **AI Concept Generator** - ML Professor mode with 10 comprehensive sections
  - Adaptive learning levels (Beginner/Intermediate/Advanced)
  - Real-world analogies, technical explanations, math formulas
  - Quiz questions and coding challenges
- 💻 **Code Playground** - Run Python and C code in browser
- 📊 **Visual Learning** - Interactive ML visualizations
- 🔊 **Audio Player** - Text-to-speech lesson narration
- 📚 **Course Management** - Python, Data Science, Web Dev, Machine Learning, C
- 🎯 **Progress Tracking** - XP system, streaks, and achievements

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **AI**: Google Gemini 1.5 Flash
- **Database**: MongoDB
- **Authentication**: Google OAuth 2.0

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/chintu47916/learnosphere.git
cd learnosphere
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
MONGO_URI=mongodb://localhost:27017/infinity_hackers
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GEMINI_API_KEY=your_gemini_api_key
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://127.0.0.1:5000/`

## 🔑 API Keys Required

- **Google OAuth**: Get from [Google Cloud Console](https://console.cloud.google.com/)
- **Gemini API**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)

## 📝 License

MIT License

## 👨‍💻 Author

Built for educational purposes
