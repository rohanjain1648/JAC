# 🧘 MyZenn — Agentic Mental Health Companion

**MyZenn** is an AI-native mental health companion built with **Jac (Jaseci)** for the Consumer Healthcare Hackathon. It demonstrates real agentic behavior using Object-Spatial Programming (OSP) and `by llm()` tool-calling.

## 🌟 Features

- **Agentic ReAct Workflow**: Multi-step reasoning to Assess → Check Crisis → Plan → Act → Respond.
- **7+ Domain-Specific Tools**: Mood assessment, crisis detection, CBT/DBT strategy selection, journal analysis, and more.
- **Persistent Graph Memory**: Tracks UserProfiles, Sessions, MoodEntries, and JournalEntries as nodes in a graph.
- **Premium UI**: Glassmorphic dark mode, animated background, mood ring, and interactive breathing exercises.
- **Safety First**: Hardcoded crisis detection that bypasses the LLM to immediately provide hotline resources.

## 🏗️ Architecture

- **Backend Logic**: `main.jac` contains the core nodes, edges, walkers, and tool definitions.
- **API Server**: `server.py` uses FastAPI to expose the Jac agent to the web frontend, with a fallback to direct OpenAI API usage if Jac is not fully installed.
- **Frontend**: Vanilla HTML/CSS/JS (`frontend/`) for an ultra-fast, premium user experience.

## 🚀 Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

*(Optional) Install Jaclang for full graph execution:*
```bash
pip install jaclang byllm
```

### 2. Configure Environment
Rename `.env.example` to `.env` and add your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-key-here
```

### 3. Run the Server
```bash
python server.py
```

### 4. Open the App
Navigate to `http://localhost:8000` in your browser.

## 🧠 Jac Implementation Details

The `main.jac` file demonstrates:
1. **Meaning Typed Programming**: Using `by llm()` to seamlessly integrate LLMs as function bodies.
2. **Tool Orchestration**: Passing 8 tools to the main `therapy_respond` function.
3. **Context Injection**: Supplying global constants (CBT techniques, system prompts) via `incl_info`.
4. **Graph Traversal**: Walkers traversing `UserProfile` -> `MoodEntry` to generate dashboards and summaries.
