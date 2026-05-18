"""
MyZenn — FastAPI Server
Exposes the Jac agent as REST API endpoints for the web frontend.
Uses jaclang library mode to invoke walkers and interact with the graph.
"""

import os
import json
import uuid
import datetime
import shelve
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Attempt to import Jac library mode — fallback to simulated mode
# ---------------------------------------------------------------------------
JAC_AVAILABLE = False
try:
    import jaclang
    from jaclang.runtimelib.machine import JacMachine
    JAC_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# LLM-based fallback (used when jaclang is not installed or for API-first mode)
# ---------------------------------------------------------------------------
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MyZenn — Mental Health Companion",
    description="Agentic AI mental health support powered by Jac",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# ---------------------------------------------------------------------------
# In-Memory Data Store (with shelve persistence)
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / ".myzenn_data"
DATA_DIR.mkdir(exist_ok=True)

class DataStore:
    """Simple persistent data store using shelve."""
    
    def __init__(self):
        self.db_path = str(DATA_DIR / "myzenn_db")
    
    def _open(self):
        return shelve.open(self.db_path)
    
    def get_user(self, user_id: str) -> dict:
        with self._open() as db:
            return db.get(f"user:{user_id}", {
                "user_id": user_id,
                "name": "Friend",
                "goals": [],
                "risk_level": "low",
                "avg_mood": 5.0,
                "total_sessions": 0,
                "created_at": datetime.datetime.now().isoformat()
            })
    
    def save_user(self, user_id: str, data: dict):
        with self._open() as db:
            db[f"user:{user_id}"] = data
    
    def get_conversations(self, user_id: str) -> list:
        with self._open() as db:
            return db.get(f"convos:{user_id}", [])
    
    def save_conversation(self, user_id: str, message: dict):
        with self._open() as db:
            key = f"convos:{user_id}"
            convos = db.get(key, [])
            convos.append(message)
            # Keep last 100 messages
            db[key] = convos[-100:]
    
    def get_moods(self, user_id: str) -> list:
        with self._open() as db:
            return db.get(f"moods:{user_id}", [])
    
    def save_mood(self, user_id: str, mood: dict):
        with self._open() as db:
            key = f"moods:{user_id}"
            moods = db.get(key, [])
            moods.append(mood)
            db[key] = moods[-200:]
    
    def get_journals(self, user_id: str) -> list:
        with self._open() as db:
            return db.get(f"journals:{user_id}", [])
    
    def save_journal(self, user_id: str, journal: dict):
        with self._open() as db:
            key = f"journals:{user_id}"
            journals = db.get(key, [])
            journals.append(journal)
            db[key] = journals[-100:]

store = DataStore()

# ---------------------------------------------------------------------------
# Mental Health Context & Tools
# ---------------------------------------------------------------------------

CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die",
    "self-harm", "cutting", "hurt myself", "no reason to live",
    "better off dead", "can't go on"
]

SYSTEM_PROMPT = """You are MyZenn, a compassionate, evidence-based mental health companion.

PERSONALITY:
- Warm, empathetic, and non-judgmental
- Uses evidence-based techniques (CBT, DBT, Mindfulness)
- Validates feelings before offering strategies
- Asks gentle check-in questions
- References user history when available

CRITICAL SAFETY RULES:
1. You are NOT a therapist. Always clarify this when appropriate.
2. If crisis is detected, IMMEDIATELY provide:
   - 988 Suicide & Crisis Lifeline (US)
   - Crisis Text Line: Text HOME to 741741
3. Never diagnose or prescribe medication.
4. Encourage professional help for serious concerns.

AGENTIC WORKFLOW:
1. ASSESS the user's emotional state
2. CHECK for crisis indicators  
3. PLAN the best support approach
4. RESPOND with empathy + actionable techniques
5. TRACK mood data for personalization

TECHNIQUES TO DRAW FROM:
- CBT: Cognitive Restructuring, Behavioral Activation, Thought Records
- DBT: TIPP Skills, STOP Skill, Radical Acceptance, Opposite Action
- Mindfulness: Box Breathing, Body Scan, 5-4-3-2-1 Grounding

Keep responses conversational (2-4 paragraphs). End with a gentle question."""


def detect_crisis(message: str) -> dict:
    """Check for crisis indicators."""
    message_lower = message.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword in message_lower:
            return {
                "is_crisis": True,
                "risk_level": "high",
                "action": "🚨 If you're in crisis, please reach out:\n• 988 Suicide & Crisis Lifeline (call/text 988)\n• Crisis Text Line (text HOME to 741741)\n• Emergency: Call 911\n\nYou are not alone. ❤️"
            }
    return {"is_crisis": False, "risk_level": "low", "action": None}


def assess_mood_simple(message: str) -> dict:
    """Simple keyword-based mood assessment fallback."""
    negative_words = ["sad", "depressed", "anxious", "worried", "stressed", "angry", "frustrated",
                      "lonely", "hopeless", "tired", "exhausted", "overwhelmed", "scared", "afraid"]
    positive_words = ["happy", "good", "great", "better", "grateful", "calm", "peaceful",
                      "excited", "hopeful", "proud", "relaxed", "content", "joy"]
    
    message_lower = message.lower()
    neg_count = sum(1 for w in negative_words if w in message_lower)
    pos_count = sum(1 for w in positive_words if w in message_lower)
    
    if neg_count > pos_count:
        score = max(1, 5 - neg_count)
        emotions = [w for w in negative_words if w in message_lower]
    elif pos_count > neg_count:
        score = min(10, 5 + pos_count)
        emotions = [w for w in positive_words if w in message_lower]
    else:
        score = 5
        emotions = ["neutral"]
    
    return {"mood_score": score, "emotions": emotions, "triggers": []}


def get_llm_response(user_message: str, conversation_history: list, user_data: dict, mood_history: list) -> str:
    """Get response from LLM with full context."""
    
    # Build context
    context_parts = [SYSTEM_PROMPT]
    
    if user_data.get("name") and user_data["name"] != "Friend":
        context_parts.append(f"\nUser's name: {user_data['name']}")
    if user_data.get("goals"):
        context_parts.append(f"User's goals: {', '.join(user_data['goals'])}")
    if mood_history:
        recent_moods = mood_history[-5:]
        mood_summary = ", ".join([f"{m.get('score', '?')}/10" for m in recent_moods])
        context_parts.append(f"Recent mood scores: {mood_summary}")
        avg = sum(m.get("score", 5) for m in recent_moods) / len(recent_moods)
        context_parts.append(f"Average recent mood: {avg:.1f}/10")
    
    system_message = "\n".join(context_parts)
    
    # Build messages
    messages = [{"role": "system", "content": system_message}]
    
    # Add recent conversation history (last 10 messages)
    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": user_message})
    
    # Check crisis first
    crisis = detect_crisis(user_message)
    if crisis["is_crisis"]:
        crisis_prefix = crisis["action"] + "\n\n"
    else:
        crisis_prefix = ""
    
    # Try Gemini API
    if GEMINI_AVAILABLE:
        try:
            api_key = os.getenv("GEMINI_API_KEY", os.getenv("LLM_API_KEY", ""))
            if not api_key:
                print("Warning: GEMINI_API_KEY not set")
            else:
                genai.configure(api_key=api_key)
                
                # Convert messages format to Gemini format
                gemini_messages = []
                for msg in messages:
                    # Skip system prompt here, handle it in GenerativeModel
                    if msg["role"] == "system":
                        continue
                        
                    role = "model" if msg["role"] == "assistant" else "user"
                    gemini_messages.append({"role": role, "parts": [msg["content"]]})
                    
                model = genai.GenerativeModel(
                    model_name=os.getenv("LLM_MODEL", "gemini-1.5-flash"),
                    system_instruction=system_message
                )
                
                response = model.generate_content(
                    gemini_messages,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=800,
                    )
                )
                
                return crisis_prefix + response.text
            
        except Exception as e:
            print(f"LLM API error: {e}")
    
    # Fallback response
    return crisis_prefix + generate_fallback_response(user_message, user_data)


def generate_fallback_response(message: str, user_data: dict) -> str:
    """Generate a supportive response without LLM API."""
    mood = assess_mood_simple(message)
    name = user_data.get("name", "Friend")
    
    if mood["mood_score"] <= 3:
        return f"""I hear you, {name}. What you're feeling right now is valid, and I want you to know that it takes courage to express these emotions. 💙

Here's something that might help right now: Try the **5-4-3-2-1 Grounding Technique**. Look around and name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, and 1 you can taste. This can help bring you back to the present moment when emotions feel overwhelming.

Remember, difficult moments are temporary, and you don't have to face them alone. Would you like to talk more about what's on your mind, or would you prefer to try a breathing exercise together?"""
    
    elif mood["mood_score"] <= 5:
        return f"""Thank you for sharing that with me, {name}. It sounds like you're navigating some challenging feelings right now, and that's completely okay. 🌿

One technique that might resonate with you is **Cognitive Restructuring** — when you notice a negative thought, try asking yourself: "Is this thought based on facts, or is it an interpretation? What would I tell a friend in this situation?" Sometimes just pausing to examine our thoughts can shift our perspective.

How are you feeling in this moment? Is there anything specific you'd like to explore together?"""
    
    else:
        return f"""That's wonderful to hear, {name}! It sounds like you're in a positive space right now, and I'm glad you're taking a moment to acknowledge that. ✨

This is actually a great time to practice **Behavioral Activation** — building on this positive momentum. Consider scheduling something enjoyable or meaningful for tomorrow to keep this energy going. Even small things like a walk, calling a friend, or trying a new recipe can reinforce these good feelings.

What's been contributing to this positive mood? I'd love to hear more about what's working well for you!"""


# ---------------------------------------------------------------------------
# API Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"

class JournalRequest(BaseModel):
    content: str
    user_id: str = "default"

class ProfileRequest(BaseModel):
    user_id: str = "default"
    name: Optional[str] = None
    goals: Optional[list[str]] = None

class MoodRequest(BaseModel):
    user_id: str = "default"
    score: int = 5
    emotions: Optional[list[str]] = None
    triggers: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Serve the main frontend page."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "MyZenn API is running", "docs": "/docs"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint — invokes the therapy agent."""
    try:
        user_data = store.get_user(req.user_id)
        conversation_history = store.get_conversations(req.user_id)
        mood_history = store.get_moods(req.user_id)
        
        # Get AI response
        response = get_llm_response(
            req.message,
            conversation_history,
            user_data,
            mood_history
        )
        
        # Assess mood
        mood_data = assess_mood_simple(req.message)
        
        # Check crisis
        crisis = detect_crisis(req.message)
        
        # Save conversation
        timestamp = datetime.datetime.now().isoformat()
        store.save_conversation(req.user_id, {
            "role": "user",
            "content": req.message,
            "timestamp": timestamp
        })
        store.save_conversation(req.user_id, {
            "role": "assistant",
            "content": response,
            "timestamp": timestamp
        })
        
        # Save mood
        store.save_mood(req.user_id, {
            "timestamp": timestamp,
            "score": mood_data["mood_score"],
            "emotions": mood_data["emotions"],
            "triggers": mood_data.get("triggers", [])
        })
        
        # Update user stats
        user_data["total_sessions"] = user_data.get("total_sessions", 0) + 1
        if crisis["is_crisis"]:
            user_data["risk_level"] = "high"
        moods = store.get_moods(req.user_id)
        if moods:
            user_data["avg_mood"] = sum(m["score"] for m in moods[-20:]) / min(len(moods), 20)
        store.save_user(req.user_id, user_data)
        
        return {
            "response": response,
            "mood": mood_data,
            "crisis": crisis,
            "timestamp": timestamp
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/journal")
async def save_journal(req: JournalRequest):
    """Save and analyze a journal entry."""
    try:
        mood_data = assess_mood_simple(req.content)
        timestamp = datetime.datetime.now().isoformat()
        
        journal_entry = {
            "timestamp": timestamp,
            "content": req.content,
            "sentiment": "positive" if mood_data["mood_score"] > 6 else "negative" if mood_data["mood_score"] < 4 else "neutral",
            "mood_score": mood_data["mood_score"],
            "themes": mood_data["emotions"]
        }
        
        store.save_journal(req.user_id, journal_entry)
        
        return {
            "status": "saved",
            "analysis": journal_entry,
            "timestamp": timestamp
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/moods/{user_id}")
async def get_moods(user_id: str):
    """Get mood history for a user."""
    moods = store.get_moods(user_id)
    user_data = store.get_user(user_id)
    
    return {
        "user_id": user_id,
        "name": user_data.get("name", "Friend"),
        "avg_mood": user_data.get("avg_mood", 5.0),
        "total_entries": len(moods),
        "moods": moods[-30:]
    }


@app.get("/api/journals/{user_id}")
async def get_journals(user_id: str):
    """Get journal entries for a user."""
    journals = store.get_journals(user_id)
    return {
        "user_id": user_id,
        "total_entries": len(journals),
        "journals": journals[-20:]
    }


@app.post("/api/profile")
async def update_profile(req: ProfileRequest):
    """Update user profile."""
    user_data = store.get_user(req.user_id)
    
    if req.name:
        user_data["name"] = req.name
    if req.goals:
        user_data["goals"] = req.goals
    
    store.save_user(req.user_id, user_data)
    
    return {"status": "updated", "profile": user_data}


@app.get("/api/profile/{user_id}")
async def get_profile(user_id: str):
    """Get user profile."""
    return store.get_user(user_id)


@app.get("/api/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    """Get comprehensive dashboard data."""
    user_data = store.get_user(user_id)
    moods = store.get_moods(user_id)
    journals = store.get_journals(user_id)
    conversations = store.get_conversations(user_id)
    
    # Calculate streaks and insights
    today = datetime.date.today()
    unique_days = set()
    for mood in moods:
        try:
            d = datetime.datetime.fromisoformat(mood["timestamp"]).date()
            unique_days.add(d)
        except:
            pass
    
    streak = 0
    check_date = today
    while check_date in unique_days:
        streak += 1
        check_date -= datetime.timedelta(days=1)
    
    return {
        "profile": user_data,
        "mood_history": moods[-30:],
        "journals": journals[-10:],
        "stats": {
            "total_conversations": len(conversations) // 2,
            "total_moods": len(moods),
            "total_journals": len(journals),
            "current_streak": streak,
            "avg_mood": user_data.get("avg_mood", 5.0)
        }
    }


@app.post("/api/mood")
async def log_mood(req: MoodRequest):
    """Manually log a mood entry."""
    timestamp = datetime.datetime.now().isoformat()
    mood_entry = {
        "timestamp": timestamp,
        "score": req.score,
        "emotions": req.emotions or [],
        "triggers": req.triggers or []
    }
    store.save_mood(req.user_id, mood_entry)
    
    return {"status": "saved", "mood": mood_entry}


@app.get("/api/breathing-exercise")
async def get_breathing_exercise():
    """Get a breathing exercise configuration."""
    return {
        "name": "Box Breathing",
        "description": "A calming technique used by Navy SEALs to reduce stress.",
        "steps": [
            {"action": "Breathe In", "duration": 4, "color": "#6C63FF"},
            {"action": "Hold", "duration": 4, "color": "#4ECDC4"},
            {"action": "Breathe Out", "duration": 4, "color": "#45B7D1"},
            {"action": "Hold", "duration": 4, "color": "#96CEB4"}
        ],
        "cycles": 4,
        "total_time": 64
    }


@app.get("/api/coping-strategies")
async def get_coping_strategies():
    """Get available coping strategies."""
    return {
        "cbt": [
            {"name": "Cognitive Restructuring", "description": "Identify and challenge negative thought patterns."},
            {"name": "Behavioral Activation", "description": "Schedule pleasurable activities to combat depression."},
            {"name": "Thought Record", "description": "Document triggering situations and alternative perspectives."},
            {"name": "Graded Exposure", "description": "Gradually face feared situations in a structured way."}
        ],
        "dbt": [
            {"name": "TIPP Skills", "description": "Temperature, Intense exercise, Paced breathing, Paired relaxation."},
            {"name": "STOP Skill", "description": "Stop, Take a step back, Observe, Proceed mindfully."},
            {"name": "Radical Acceptance", "description": "Accept reality without judgment."},
            {"name": "Opposite Action", "description": "Act opposite to the emotion-driven urge."}
        ],
        "mindfulness": [
            {"name": "Box Breathing", "description": "4-count breathing pattern for calm."},
            {"name": "Body Scan", "description": "Progressive attention from toes to head."},
            {"name": "5-4-3-2-1 Grounding", "description": "Engage all 5 senses to ground yourself."},
            {"name": "Mindful Breathing", "description": "Focus on natural breath rhythm."}
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MyZenn Mental Health Companion",
        "jac_available": JAC_AVAILABLE,
        "llm_available": GEMINI_AVAILABLE,
        "timestamp": datetime.datetime.now().isoformat()
    }


# ---------------------------------------------------------------------------
# Run Server
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"""
╔══════════════════════════════════════════════════════════╗
║        🧘 MyZenn — Mental Health Companion              ║
║        Powered by Jac (Jaseci) Agentic AI               ║
╠══════════════════════════════════════════════════════════╣
║  Server:  http://localhost:{port}                         ║
║  API:     http://localhost:{port}/docs                    ║
║  Health:  http://localhost:{port}/health                  ║
╚══════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=port)
