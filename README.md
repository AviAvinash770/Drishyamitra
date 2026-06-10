# 🎯 Drishyamitra — AI-Powered Smart Photo Management

Drishyamitra is an advanced, premium AI-powered photo management application designed to organize, search, and share your personal photo libraries effortlessly. By combining state-of-the-art AI orchestration with a beautiful, responsive user interface, it provides a seamless experience for indexing memories, recognizing faces, and natural-language sharing.

---

## 🌟 Key Features

### 🔍 1. Smart Semantic Search
- **Natural Language Queries**: Search for photos using conversational prompts (e.g., *"family picnic in 2024"*, *"wedding ceremony outdoors"*).
- **Hybrid Search Engine**: Combines ChromaDB vector embeddings for deep semantic matches with SQL structure-based queries (filename, description, tags, locations).

### 🎙️ 2. Voice Search Engine
- **Multilingual Support**: Supports searching via voice inputs in multiple languages including English (EN), Hindi (HI), Spanish (ES), and Telugu (TE).
- **Browser-level Audio Permissions**: Safely handles browser-level microphone access clearances explicitly before recording.
- **Auto-Submission**: Strips trailing speech-to-text punctuation automatically and instantly fires search queries.
- **Resilient Fallbacks**: Gracefully intercepts connection drops or Speech API timeouts to prompt retry instructions instead of hard-crashing.

### 👥 3. Face Recognition & Smart Clustering
- **AI-Driven Clustering**: Automated background pipelines scan uploaded photos, extract faces, and group them into recognized person profiles.
- **Manual Labeling**: Assign unrecognized face clusters to new or existing names.
- **Strict Filtering**: Searching a person's name intercepts the search engine to query direct face-to-photo relations, eliminating semantic search noise.

### 💬 4. Conversational AI Assistant
- **LangGraph State Machine**: Powered by Groq Llama 3.3 to orchestrate search and sharing workflows.
- **Database Tool-Calling**: The assistant executes SQL-level count queries in real-time when asked counts (e.g. *"how many photos do I have?"*).
- **Direct Search Redirection**: Chatbot search answers automatically transition the gallery viewport state to show relevant search queries, avoiding grid duplication in chat history.
- **Help Center Manual**: Built-in resilience guides users on site navigation, deletion, sharing, and key features.

### 📂 5. Automated & Manual Albums
- **Automated Scene Albums**: Instantly groups photos into preset event categories (*Birthdays, Weddings, Anniversaries*) by parsing descriptions and tags.
- **Manual Album Creator**: Create custom albums from the top navigation bar and select batches of photos to assign them.

### ✉️ 6. One-Click WhatsApp & Email Dispatcher
- **WhatsApp Deliveries**: Integrated with Twilio to dispatch photo attachments directly to phone numbers.
- **Gmail Deliveries**: Standard secure SMTP worker sending high-resolution images as attachments.
- **Contextual Memory**: Share options in chat automatically fetch the on-screen active photos to allow immediate conversational sending.

### 📊 7. Live Analytics Dashboard
- **Storage Breakdown**: Displays overall usage against a 10 GB limit with a radial progress ring and category card breakdown (Photos, AI Cache, Thumbnails).
- **Activity Metrics**: Live counters showing detected faces, auto-sorted faces, deliveries sent, and total photo counts.
- **Visual Charts**: Interactive monthly upload frequency bar charts and "Most Photographed" progress tracking.

---

## 💻 Technology Stack

### Backend
- **Core**: Python 3.10+ & Flask API
- **Database**: SQLite & SQLAlchemy ORM
- **Semantic Vector Store**: ChromaDB (stores photo embeddings)
- **AI Agent Orchestration**: LangGraph (managing chat nodes)
- **LLM Engine**: Groq Llama 3.3 (via Groq API)
- **Image Processing**: OpenCV & Dlib / Face Recognition
- **Integrations**: Twilio API (WhatsApp) & SMTP (Gmail)

### Frontend
- **Framework**: React.js (v18)
- **Styling**: Modern, premium Vanilla CSS with custom HSL variables, smooth transitions, glassmorphic headers, and responsive grid layouts.
- **Audio Hook**: Web Speech API for voice search
- **Network**: Axios Client with authorization interceptors

---

## 🚀 Step-by-Step Setup Guide

### 📋 Prerequisites

Ensure the following tools are installed on your machine:

| Tool | Version | Download |
|------|---------|----------|
| **Python** | 3.10 or higher | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18 or higher | [nodejs.org](https://nodejs.org/) |
| **Git** | Latest | [git-scm.com](https://git-scm.com/) |

> **Tip:** Ensure the option **"Add Python to PATH"** is checked during Python installation.

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/sathish0408/Drishyamitra.git
cd Drishyamitra
```

---

### Step 2: Backend Setup
```bash
# Navigate to backend folder
cd drishyamitra-backend

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\activate
# Windows (CMD):
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create the .env file from template
# Windows:
copy .env.example .env
# Linux/Mac:
cp .env.example .env
```

---

### Step 3: Configure Environment Variables
Open the newly created `drishyamitra-backend/.env` file and input your credentials:

1. **Groq API Key (Required for AI Chat & Auto-Tagging)**:
   - Generate a free key at [console.groq.com](https://console.groq.com/keys).
   - Set `GROQ_API_KEY=gsk_your_key_here`.
2. **Gmail App Password (Optional - for Email Sharing)**:
   - Enable 2-Factor Authentication on your Google Account.
   - Generate an **App Password** (select "Mail" app) under security settings.
   - Set `SMTP_USER=your_email@gmail.com` and `SMTP_PASSWORD=your_app_password`.
3. **Twilio Account (Optional - for WhatsApp Sharing)**:
   - Sign up for a trial account at [twilio.com](https://www.twilio.com).
   - Set `TWILIO_ACCOUNT_SID=ACxxxx...` and `TWILIO_AUTH_TOKEN=your_token`.
   - Connect your WhatsApp device to the Twilio Sandbox number (+1 415 523 8886) by sending the sandbox activation code.

---

### Step 4: Frontend Setup
```bash
# Navigate to the frontend folder (in a new terminal window)
cd drishyamitra-frontend

# Install node dependencies
npm install
```

---

### Step 5: Start the Application

You must run the backend API server and frontend React dev server concurrently in separate terminals:

#### Terminal 1: Backend
```bash
cd drishyamitra-backend
.venv\Scripts\activate
python app.py
```
*Expected Output:* `Drishyamitra Backend running on http://localhost:5000`

#### Terminal 2: Frontend
```bash
cd drishyamitra-frontend
npm start
```
*Expected Output:* The React app automatically compiles and opens in your default web browser at `http://localhost:3000`.

---

## 🛠️ Troubleshooting

- **PowerShell Execution Policy Error**: If script execution is blocked on Windows PowerShell, run:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```
- **Port Conflicts**: Make sure ports `5000` (backend) and `3000` (frontend) are not occupied by other services.
- **Microphone Blocked**: If voice search fails, ensure you have clicked "Allow" when the browser requests microphone permissions.

---

## 📁 Repository Directory Structure

```
Drishyamitra/
├── drishyamitra-backend/       # Flask API Server
│   ├── agents/                 # LangGraph Agent nodes (Orchestrator, Search, Sharing)
│   ├── database/               # SQLite database configuration
│   ├── models/                 # SQLAlchemy ORM Tables (Photo, Person, Face, Album, Sharing)
│   ├── routes/                 # Flask routes (Photos, Faces, Analytics, Chat, Albums)
│   ├── services/               # Core logic (Vector service, Face clustering, SMTP/WhatsApp)
│   ├── workflows/              # LangGraph workflow loops
│   ├── uploads/                # Directory storing physical uploaded files
│   ├── app.py                  # API entry point
│   ├── requirements.txt        # Python dependency manifest
│   └── .env.example            # Environment template config
│
├── drishyamitra-frontend/      # React Client App
│   ├── src/
│   │   ├── components/         # React components (auth, pages, gallery, common)
│   │   ├── styles/             # CSS styling stylesheets
│   │   ├── api.js              # Axios backend connection client
│   │   └── App.js              # React routing and main dashboard wrapper
│   └── package.json            # NPM dependencies configuration
```
