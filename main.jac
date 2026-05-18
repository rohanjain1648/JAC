"""
MyZenn — Agentic Mental Health Companion
Built with Jac (Jaseci) | Consumer Healthcare

This module implements the core agentic AI system for mental health support.
It uses Jac's Object-Spatial Programming (graphs, walkers, nodes) combined
with `by llm()` tool-calling to create a system that plans, reasons,
uses tools, maintains memory, and adapts to each user over time.
"""

import:py json;
import:py datetime;
import:py os;

# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================

glob CRISIS_KEYWORDS: list[str] = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die",
    "self-harm", "cutting", "hurt myself", "no reason to live",
    "better off dead", "can't go on", "hopeless"
];

glob CBT_TECHNIQUES: list[dict] = [
    {"name": "Cognitive Restructuring", "type": "CBT",
     "description": "Identify and challenge negative thought patterns, replacing them with balanced alternatives."},
    {"name": "Behavioral Activation", "type": "CBT",
     "description": "Schedule pleasurable and meaningful activities to combat depression and withdrawal."},
    {"name": "Thought Record", "type": "CBT",
     "description": "Document triggering situations, automatic thoughts, emotions, and alternative perspectives."},
    {"name": "Graded Exposure", "type": "CBT",
     "description": "Gradually face feared situations in a structured, manageable way."}
];

glob DBT_TECHNIQUES: list[dict] = [
    {"name": "TIPP Skills", "type": "DBT",
     "description": "Temperature, Intense exercise, Paced breathing, Paired muscle relaxation for crisis moments."},
    {"name": "STOP Skill", "type": "DBT",
     "description": "Stop, Take a step back, Observe, Proceed mindfully when emotions are overwhelming."},
    {"name": "Radical Acceptance", "type": "DBT",
     "description": "Accept reality as it is without judgment, reducing suffering caused by fighting the unchangeable."},
    {"name": "Opposite Action", "type": "DBT",
     "description": "Act opposite to the emotion-driven urge when the emotion doesn't fit the facts."}
];

glob MINDFULNESS_TECHNIQUES: list[dict] = [
    {"name": "Box Breathing", "type": "Mindfulness",
     "description": "Breathe in 4 seconds, hold 4 seconds, out 4 seconds, hold 4 seconds. Repeat 4 cycles."},
    {"name": "Body Scan", "type": "Mindfulness",
     "description": "Progressive attention from toes to head, noticing sensations without judgment."},
    {"name": "5-4-3-2-1 Grounding", "type": "Mindfulness",
     "description": "Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste."},
    {"name": "Mindful Breathing", "type": "Mindfulness",
     "description": "Focus on natural breath rhythm, gently returning attention when the mind wanders."}
];

glob MENTAL_HEALTH_CONTEXT: str = """
You are MyZenn, a compassionate and evidence-based mental health companion.
Your role is to provide empathetic support using CBT, DBT, and mindfulness techniques.

CRITICAL SAFETY RULES:
1. You are NOT a therapist or medical professional. Always clarify this.
2. If a user expresses suicidal ideation or self-harm, IMMEDIATELY recommend:
   - National Suicide Prevention Lifeline: 988 (US)
   - Crisis Text Line: Text HOME to 741741
   - International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/
3. Never diagnose conditions or prescribe medication.
4. Encourage professional help for serious concerns.
5. Maintain a warm, non-judgmental, and validating tone.
6. Use evidence-based techniques (CBT, DBT, Mindfulness).
7. Track mood patterns and suggest personalized coping strategies.
""";


# ============================================================================
# NODE DEFINITIONS — Graph Memory Structure
# ============================================================================

"""Represents a user's profile with their preferences and history."""
node UserProfile {
    has user_id: str = "default";
    has name: str = "Friend";
    has created_at: str = "";
    has goals: list[str] = [];
    has preferences: dict = {};
    has risk_level: str = "low";  # low, moderate, high
    has total_sessions: int = 0;
    has avg_mood: float = 5.0;
}

"""Represents a single therapy session with mood tracking."""
node Session {
    has session_id: str = "";
    has timestamp: str = "";
    has mood_start: int = 5;
    has mood_end: int = 5;
    has techniques_used: list[str] = [];
    has conversation_log: list[dict] = [];
    has notes: str = "";
    has is_active: bool = true;
}

"""Tracks individual mood data points over time."""
node MoodEntry {
    has timestamp: str = "";
    has score: int = 5;
    has emotions: list[str] = [];
    has triggers: list[str] = [];
    has context: str = "";
}

"""Stores personal journal entries with sentiment analysis."""
node JournalEntry {
    has timestamp: str = "";
    has content: str = "";
    has sentiment: str = "neutral";
    has themes: list[str] = [];
    has mood_score: int = 5;
}

"""Tracks coping strategies and their effectiveness for the user."""
node CopingStrategy {
    has name: str = "";
    has strategy_type: str = "";  # CBT, DBT, Mindfulness
    has description: str = "";
    has times_used: int = 0;
    has effectiveness_score: float = 5.0;
    has last_used: str = "";
}


# ============================================================================
# EDGE DEFINITIONS — Relationships Between Nodes
# ============================================================================

edge HasSession {}
edge HasMood {}
edge HasJournal {}
edge HasStrategy {}


# ============================================================================
# TOOL FUNCTIONS — Available to the LLM Agent
# ============================================================================

"""Analyze the user's emotional state from their message text.
Returns a JSON string with mood score (1-10), detected emotions, and potential triggers."""
can assess_mood(message: str) -> str
by llm(
    incl_info={"context": "You are a mood assessment tool. Analyze the emotional content of the message and return a JSON object with: mood_score (1-10 where 1=very negative, 10=very positive), emotions (list of detected emotions), triggers (list of potential triggers identified). Be precise and empathetic."}
);

"""Check if the user's message contains crisis indicators like suicidal ideation or self-harm.
Returns a JSON string with is_crisis (bool), risk_level (low/moderate/high), and recommended_action."""
can detect_crisis(message: str) -> str {
    message_lower = message.lower();
    is_crisis = false;
    for keyword in CRISIS_KEYWORDS {
        if keyword in message_lower {
            is_crisis = true;
            break;
        }
    }

    if is_crisis {
        return json.dumps({
            "is_crisis": true,
            "risk_level": "high",
            "recommended_action": "IMMEDIATE: Please reach out to the 988 Suicide & Crisis Lifeline (call or text 988) or Crisis Text Line (text HOME to 741741). You are not alone, and help is available 24/7.",
            "keywords_detected": true
        });
    }

    return json.dumps({
        "is_crisis": false,
        "risk_level": "low",
        "recommended_action": "Continue supportive conversation",
        "keywords_detected": false
    });
}

"""Recommend appropriate coping strategies based on the user's current emotional state and history.
Returns a JSON list of recommended techniques with descriptions."""
can recommend_coping(emotion: str, intensity: str = "moderate") -> str
by llm(
    incl_info={
        "cbt_techniques": json.dumps(CBT_TECHNIQUES),
        "dbt_techniques": json.dumps(DBT_TECHNIQUES),
        "mindfulness_techniques": json.dumps(MINDFULNESS_TECHNIQUES),
        "context": "You are a coping strategy recommender. Based on the emotion and intensity, select 2-3 most appropriate techniques from the available CBT, DBT, and Mindfulness techniques. Return a JSON array of objects with: name, type, description, and why_recommended (brief explanation of why this technique fits). For high intensity emotions, prioritize DBT and grounding techniques. For moderate, mix CBT and mindfulness. For low, focus on CBT and growth-oriented techniques."
    }
);

"""Store a journal entry and analyze its themes and sentiment.
Returns a JSON confirmation with sentiment analysis results."""
can analyze_journal(content: str) -> str
by llm(
    incl_info={"context": "You are a journal analysis tool. Analyze the journal entry and return a JSON object with: sentiment (positive/negative/neutral/mixed), mood_score (1-10), themes (list of key themes like 'relationships', 'work', 'self-esteem', etc.), insights (brief therapeutic insight about the entry). Be compassionate and observant."}
);

"""Retrieve mood history summary for the user.
Returns a formatted string describing mood trends."""
can get_mood_summary(mood_entries: list[dict]) -> str {
    if len(mood_entries) == 0 {
        return "No mood history available yet. This is a great time to start tracking!";
    }

    total = 0;
    for entry in mood_entries {
        total += entry.get("score", 5);
    }
    avg = total / len(mood_entries);

    recent = mood_entries[-1] if len(mood_entries) > 0 else {};

    return json.dumps({
        "total_entries": len(mood_entries),
        "average_mood": round(avg, 1),
        "recent_mood": recent.get("score", 5),
        "recent_emotions": recent.get("emotions", []),
        "trend": "improving" if len(mood_entries) > 1 and mood_entries[-1].get("score", 5) > mood_entries[-2].get("score", 5) else "stable"
    });
}

"""Generate a personalized affirmation based on the user's current emotional state and goals."""
can generate_affirmation(emotion: str, goals: list[str] = []) -> str
by llm(
    incl_info={"context": "You are an affirmation generator. Create a warm, genuine, and personalized affirmation (2-3 sentences) that acknowledges the user's current emotion and connects it to their growth. Avoid toxic positivity. Be authentic and grounding. Return just the affirmation text, no JSON."}
);

"""Search and return relevant mental health resources based on the user's concern."""
can search_resources(concern: str) -> str
by llm(
    incl_info={"context": "You are a mental health resource finder. Based on the concern, return a JSON array of 2-3 relevant resources with: name, type (article/exercise/hotline/app), description, and url (use reputable sources like NAMI, NIMH, Psychology Today, or WHO). Always include crisis hotlines for serious concerns."}
);

"""Get the current date and time."""
can get_current_time() -> str {
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S");
}


# ============================================================================
# MAIN THERAPY AGENT — ReAct Pattern with Tool Calling
# ============================================================================

"""The main therapy agent that uses ReAct pattern to provide mental health support.
It plans, reasons, uses tools, and generates empathetic responses."""
can therapy_respond(
    user_message: str,
    conversation_history: list[dict] = [],
    user_profile: dict = {},
    mood_history: list[dict] = []
) -> str
by llm(
    tools=[
        assess_mood,
        detect_crisis,
        recommend_coping,
        analyze_journal,
        get_mood_summary,
        generate_affirmation,
        search_resources,
        get_current_time
    ],
    incl_info={
        "system_context": MENTAL_HEALTH_CONTEXT,
        "instructions": """
You are MyZenn, a compassionate mental health companion. Follow this agentic workflow:

STEP 1 — SAFETY FIRST: Always check for crisis indicators using detect_crisis tool.
STEP 2 — ASSESS: Use assess_mood to understand the user's emotional state.
STEP 3 — PLAN: Based on mood and history, decide which support to provide.
STEP 4 — ACT: Use appropriate tools (recommend_coping, generate_affirmation, search_resources, etc.)
STEP 5 — RESPOND: Synthesize tool results into a warm, empathetic, personalized response.

Response style:
- Be warm, genuine, and non-judgmental
- Validate the user's feelings before offering strategies
- Use their name if available
- Reference their history/patterns when relevant
- Keep responses conversational (2-4 paragraphs max)
- End with a gentle check-in question
- If journaling, use analyze_journal tool
- NEVER diagnose or prescribe medication
"""
    }
);

sem therapy_respond = "Provide empathetic, evidence-based mental health support using available tools.";


# ============================================================================
# WALKER DEFINITIONS — Autonomous Agents
# ============================================================================

"""Main therapy session walker that manages the conversation flow."""
walker TherapySession {
    has user_id: str = "default";
    has user_message: str = "";
    has session_data: dict = {};

    can start with `root entry {
        # Find or create user profile
        user_profiles = [-->](?UserProfile)(?user_id == self.user_id);

        if len(user_profiles) == 0 {
            # Create new user profile
            new_profile = UserProfile(
                user_id=self.user_id,
                created_at=datetime.datetime.now().isoformat()
            );
            here ++> new_profile;
            visit new_profile;
        } else {
            visit user_profiles[0];
        }
    }

    can process with UserProfile entry {
        # Gather context
        profile_data = {
            "user_id": here.user_id,
            "name": here.name,
            "goals": here.goals,
            "risk_level": here.risk_level,
            "total_sessions": here.total_sessions,
            "avg_mood": here.avg_mood
        };

        # Get mood history
        mood_nodes = [-->](?MoodEntry);
        mood_history = [];
        for m in mood_nodes {
            mood_history.append({
                "timestamp": m.timestamp,
                "score": m.score,
                "emotions": m.emotions,
                "triggers": m.triggers
            });
        }

        # Get conversation history from active session
        session_nodes = [-->](?Session)(?is_active == true);
        conversation_history: list[dict] = [];
        active_session: Session? = None;

        if len(session_nodes) > 0 {
            active_session = session_nodes[0];
            conversation_history = active_session.conversation_log;
        } else {
            # Create new session
            active_session = Session(
                session_id=f"session_{here.total_sessions + 1}",
                timestamp=datetime.datetime.now().isoformat(),
                is_active=true
            );
            here ++> active_session;
        }

        # Run the therapy agent with ReAct pattern
        response = therapy_respond(
            user_message=self.user_message,
            conversation_history=conversation_history,
            user_profile=profile_data,
            mood_history=mood_history
        );

        # Update session log
        if active_session is not None {
            active_session.conversation_log.append({
                "role": "user",
                "content": self.user_message,
                "timestamp": datetime.datetime.now().isoformat()
            });
            active_session.conversation_log.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.datetime.now().isoformat()
            });
        }

        # Assess and store mood
        mood_result_str = assess_mood(self.user_message);
        try {
            mood_data = json.loads(mood_result_str);
            new_mood = MoodEntry(
                timestamp=datetime.datetime.now().isoformat(),
                score=mood_data.get("mood_score", 5),
                emotions=mood_data.get("emotions", []),
                triggers=mood_data.get("triggers", []),
                context=self.user_message[:200]
            );
            here ++> new_mood;

            # Update average mood
            all_moods = [-->](?MoodEntry);
            total_score = 0;
            for m in all_moods {
                total_score += m.score;
            }
            here.avg_mood = total_score / len(all_moods) if len(all_moods) > 0 else 5.0;
        } except {
            pass;
        }

        # Check and update risk level
        crisis_result_str = detect_crisis(self.user_message);
        try {
            crisis_data = json.loads(crisis_result_str);
            if crisis_data.get("is_crisis", false) {
                here.risk_level = "high";
            }
        } except {
            pass;
        }

        # Report response
        report {
            "response": response,
            "user_id": here.user_id,
            "session_id": active_session.session_id if active_session is not None else "",
            "mood_data": mood_result_str,
            "risk_level": here.risk_level
        };
    }
}

"""Walker to log a journal entry for a user."""
walker LogJournal {
    has user_id: str = "default";
    has journal_content: str = "";

    can start with `root entry {
        user_profiles = [-->](?UserProfile)(?user_id == self.user_id);
        if len(user_profiles) > 0 {
            visit user_profiles[0];
        } else {
            report {"error": "User not found"};
        }
    }

    can process with UserProfile entry {
        # Analyze the journal entry
        analysis_str = analyze_journal(self.journal_content);

        try {
            analysis = json.loads(analysis_str);
        } except {
            analysis = {"sentiment": "neutral", "mood_score": 5, "themes": [], "insights": ""};
        }

        # Create journal node
        new_journal = JournalEntry(
            timestamp=datetime.datetime.now().isoformat(),
            content=self.journal_content,
            sentiment=analysis.get("sentiment", "neutral"),
            themes=analysis.get("themes", []),
            mood_score=analysis.get("mood_score", 5)
        );
        here ++> new_journal;

        report {
            "status": "Journal entry saved",
            "analysis": analysis,
            "timestamp": new_journal.timestamp
        };
    }
}

"""Walker to retrieve user's mood history and trends."""
walker GetMoodHistory {
    has user_id: str = "default";

    can start with `root entry {
        user_profiles = [-->](?UserProfile)(?user_id == self.user_id);
        if len(user_profiles) > 0 {
            visit user_profiles[0];
        } else {
            report {"error": "User not found", "moods": []};
        }
    }

    can process with UserProfile entry {
        mood_nodes = [-->](?MoodEntry);
        moods = [];
        for m in mood_nodes {
            moods.append({
                "timestamp": m.timestamp,
                "score": m.score,
                "emotions": m.emotions,
                "triggers": m.triggers
            });
        }

        # Sort by timestamp (most recent last)
        moods.sort(key=lambda x: x["timestamp"]);

        report {
            "user_id": here.user_id,
            "name": here.name,
            "avg_mood": here.avg_mood,
            "total_entries": len(moods),
            "moods": moods[-20:],  # Last 20 entries
            "risk_level": here.risk_level
        };
    }
}

"""Walker to update user profile information."""
walker UpdateProfile {
    has user_id: str = "default";
    has name: str = "";
    has goals: list[str] = [];

    can start with `root entry {
        user_profiles = [-->](?UserProfile)(?user_id == self.user_id);
        if len(user_profiles) > 0 {
            visit user_profiles[0];
        } else {
            # Create new profile
            new_profile = UserProfile(
                user_id=self.user_id,
                name=self.name if self.name else "Friend",
                created_at=datetime.datetime.now().isoformat(),
                goals=self.goals
            );
            here ++> new_profile;
            report {
                "status": "Profile created",
                "user_id": self.user_id,
                "name": new_profile.name
            };
        }
    }

    can process with UserProfile entry {
        if self.name {
            here.name = self.name;
        }
        if len(self.goals) > 0 {
            here.goals = self.goals;
        }

        report {
            "status": "Profile updated",
            "user_id": here.user_id,
            "name": here.name,
            "goals": here.goals
        };
    }
}

"""Walker to get comprehensive user dashboard data."""
walker GetDashboard {
    has user_id: str = "default";

    can start with `root entry {
        user_profiles = [-->](?UserProfile)(?user_id == self.user_id);
        if len(user_profiles) > 0 {
            visit user_profiles[0];
        } else {
            report {
                "user_exists": false,
                "message": "No profile found. Start a conversation to create one."
            };
        }
    }

    can process with UserProfile entry {
        # Gather all data
        mood_nodes = [-->](?MoodEntry);
        journal_nodes = [-->](?JournalEntry);
        session_nodes = [-->](?Session);

        moods = [];
        for m in mood_nodes {
            moods.append({
                "timestamp": m.timestamp,
                "score": m.score,
                "emotions": m.emotions
            });
        }
        moods.sort(key=lambda x: x["timestamp"]);

        journals = [];
        for j in journal_nodes {
            journals.append({
                "timestamp": j.timestamp,
                "sentiment": j.sentiment,
                "themes": j.themes,
                "mood_score": j.mood_score,
                "preview": j.content[:100] + "..." if len(j.content) > 100 else j.content
            });
        }
        journals.sort(key=lambda x: x["timestamp"]);

        report {
            "user_exists": true,
            "profile": {
                "user_id": here.user_id,
                "name": here.name,
                "goals": here.goals,
                "risk_level": here.risk_level,
                "total_sessions": here.total_sessions,
                "avg_mood": here.avg_mood,
                "created_at": here.created_at
            },
            "mood_history": moods[-30:],
            "journals": journals[-10:],
            "total_sessions": len(session_nodes)
        };
    }
}
