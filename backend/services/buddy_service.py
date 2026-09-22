import json
import os
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Tuple
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from models.buddy import BuddyMessage
from models.user import User
from services.buddy_context_engine import BuddyContextEngine

STANDARD_BUDDY_DISCLAIMER = (
    "Notice: Virtual Gym Buddy provides fitness and wellness guidance based on your logged context. "
    "This does not replace advice from a certified trainer or medical healthcare professional."
)

MEDICAL_SAFETY_RESPONSE = (
    "I am your Virtual Gym Buddy—a fitness and workout coaching assistant, NOT a medical doctor. "
    "I cannot diagnose medical conditions, evaluate acute physical injuries, prescribe medications, or recommend extreme restrictive diets. "
    "If you are experiencing physical pain, joint injury, dizziness, chest discomfort, or medical symptoms, please stop exercising immediately "
    "and consult a qualified medical professional or doctor."
)

# Medical & safety keyword boundaries
MEDICAL_KEYWORDS = [
    "diagnose", "diagnosis", "doctor", "medicine", "prescription", "prescribe",
    "chest pain", "heart attack", "broken bone", "fracture", "torn ligament",
    "sharp pain", "severe pain", "joint dislocation", "fainting", "dizziness",
    "starve", "anorexia", "bulimia", "extreme diet", "0 calories", "suicide",
]


class BuddyService:
    """
    Core Virtual Gym Buddy Service.
    Handles conversation flow, context gathering, medical safety boundary enforcement,
    LLM API dispatch, deterministic fallback, and chat persistence.
    """

    @classmethod
    def chat(cls, db: Session, user_id: int, message: str) -> Dict[str, Any]:
        """
        Processes a user chat message with context engine integration and safety boundaries.
        Persists both prompt and response into database.
        """
        clean_msg = message.strip()
        if not clean_msg:
            raise ValueError("Message cannot be empty.")

        # 1. Medical & Safety Boundary Check
        msg_lower = clean_msg.lower()
        if any(kw in msg_lower for kw in MEDICAL_KEYWORDS):
            # Save user prompt
            user_msg_rec = BuddyMessage(
                user_id=user_id,
                sender="user",
                content=clean_msg,
                provider=None,
            )
            db.add(user_msg_rec)

            # Save safety response
            bot_msg_rec = BuddyMessage(
                user_id=user_id,
                sender="assistant",
                content=MEDICAL_SAFETY_RESPONSE,
                provider="system_safety",
            )
            db.add(bot_msg_rec)
            db.commit()

            return {
                "message": MEDICAL_SAFETY_RESPONSE,
                "provider": "system_safety",
                "disclaimer": STANDARD_BUDDY_DISCLAIMER,
                "context_summary": {"safety_triggered": True},
                "timestamp": datetime.utcnow(),
            }

        # 2. Gather authenticated user context
        context = BuddyContextEngine.gather_user_context(db, user_id)

        # 3. Attempt LLM provider execution if key is present
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        response_text = None
        provider = "deterministic_buddy_fallback"

        if gemini_key or openai_key:
            try:
                response_text, provider = cls._call_llm_buddy(clean_msg, context, gemini_key, openai_key)
            except Exception as e:
                print(f"[Virtual Gym Buddy] LLM execution failed ({e}). Executing deterministic fallback.")
                response_text = None

        # 4. Fallback to Deterministic Expert Buddy Engine if LLM skipped or failed
        if not response_text:
            response_text = cls._generate_deterministic_buddy_response(clean_msg, context)
            provider = "deterministic_buddy_fallback"

        # 5. Save conversation history to PostgreSQL database
        user_msg_rec = BuddyMessage(
            user_id=user_id,
            sender="user",
            content=clean_msg,
            provider=None,
        )
        db.add(user_msg_rec)

        bot_msg_rec = BuddyMessage(
            user_id=user_id,
            sender="assistant",
            content=response_text,
            provider=provider,
        )
        db.add(bot_msg_rec)
        db.commit()

        return {
            "message": response_text,
            "provider": provider,
            "disclaimer": STANDARD_BUDDY_DISCLAIMER,
            "context_summary": context,
            "timestamp": datetime.utcnow(),
        }

    @classmethod
    def get_history(cls, db: Session, user_id: int) -> List[BuddyMessage]:
        """Retrieves authenticated user's persistent chat messages."""
        return db.execute(
            select(BuddyMessage)
            .where(BuddyMessage.user_id == user_id)
            .order_by(BuddyMessage.created_at.asc())
        ).scalars().all()

    @classmethod
    def clear_history(cls, db: Session, user_id: int) -> int:
        """Clears authenticated user's chat history."""
        result = db.execute(
            delete(BuddyMessage).where(BuddyMessage.user_id == user_id)
        )
        db.commit()
        return result.rowcount

    @classmethod
    def _call_llm_buddy(
        cls,
        user_message: str,
        context: Dict[str, Any],
        gemini_key: str | None,
        openai_key: str | None,
    ) -> Tuple[str, str]:
        """Calls external Gemini or OpenAI LLM API with context block."""
        context_block = BuddyContextEngine.format_context_prompt_block(context)

        system_instruction = (
            "You are Virtual Gym Buddy, an encouraging, intelligent, and highly supportive personal fitness and nutrition assistant.\n"
            "Your job is to answer user questions using their actual authenticated fitness context below.\n\n"
            "RULES:\n"
            "1. Strictly rely on the provided context for workout counts, performance scores, form issues, and nutrition targets.\n"
            "2. DO NOT invent fake workout records, fake weights, or fake nutrition logs that are missing from context.\n"
            "3. If context data is unavailable or 0 (e.g. 0 workouts logged), politely state that you do not have that data recorded yet.\n"
            "4. Never provide medical diagnoses or prescribe medical treatment.\n"
            "5. Keep responses concise, warm, actionable, and structured with clean markdown.\n\n"
            f"{context_block}"
        )

        if gemini_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_instruction}\n\nUser Question: {user_message}"}
                        ]
                    }
                ]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                if not text:
                    raise ValueError("Empty response from Gemini API.")
                return text, "llm_gemini"

        if openai_key:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_message},
                ],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result["choices"][0]["message"]["content"].strip()
                if not text:
                    raise ValueError("Empty response from OpenAI API.")
                return text, "llm_openai"

        raise ValueError("No LLM API keys configured.")

    @classmethod
    def _generate_deterministic_buddy_response(
        cls, user_message: str, context: Dict[str, Any]
    ) -> str:
        """
        Deterministic expert buddy response generator.
        Provides accurate, context-aware answers without needing an LLM key.
        """
        msg = user_message.lower()
        prof = context.get("profile", {})
        work = context.get("workout_performance", {})
        nutr = context.get("nutrition", {})

        goal = prof.get("fitness_goal") or "fitness & wellness"
        total_w = work.get("total_workouts", 0)
        avg_score = work.get("avg_performance_score", 0.0)
        top_ex = work.get("top_exercise") or "Squat"
        issues = work.get("recurring_form_issues", [])
        focus = work.get("next_week_focus") or "Focus on movement control and stability."

        cals_target = nutr.get("target_calories", 2000.0)
        consumed = nutr.get("consumed_calories_today", 0.0)
        rem_cals = nutr.get("remaining_calories_today", cals_target)
        p_target = nutr.get("target_protein", 150.0)
        p_consumed = nutr.get("consumed_protein_today", 0.0)

        # 1. Performance / Weekly Report Questions
        if any(k in msg for k in ["perform", "week", "report", "stats", "score"]):
            if total_w == 0:
                return (
                    f"👋 Hi there! Looking at your data for the past 7 days, you haven't logged any completed workout sessions yet.\n\n"
                    f"To track your performance and get AI form scores, head over to the **Workout** page and complete a squat session!"
                )
            issue_str = f"Your main area to watch is **{issues[0]}**." if issues else "Your movement form has been clean with no major recurring issues!"
            return (
                f"📊 **Weekly Performance Summary**:\n"
                f"- **Workouts Completed**: {total_w} sessions\n"
                f"- **Average Form Score**: {avg_score}/100\n"
                f"- **Top Exercise**: {top_ex}\n"
                f"- **Form Insight**: {issue_str}\n"
                f"- **Next Focus**: {focus}\n\n"
                f"Keep up the great effort toward your goal of **{goal}**!"
            )

        # 2. Form / Squat / Technique Questions
        if any(k in msg for k in ["form", "squat", "technique", "issue", "valgus", "depth"]):
            if issues:
                return (
                    f"🔍 **Form Analysis & Advice**:\n"
                    f"Based on your recent Pose AI metrics, we detected a recurring pattern: **{issues[0]}**.\n\n"
                    f"**How to fix it**:\n"
                    f"1. Keep your feet shoulder-width apart and push knees outward over toes.\n"
                    f"2. Engage your core before initiating the descent.\n"
                    f"3. Focus on pushing hips back while keeping chest upright.\n\n"
                    f"Your recommended focus for next session: **{focus}**."
                )
            return (
                f"💪 **Form Analysis & Advice**:\n"
                f"Your recent workouts show great technique with an average score of **{avg_score}/100**! "
                f"No major recurring form violations were detected in your latest sessions. Keep maintaining deep, controlled squats!"
            )

        # 3. Next Workout / Focus Questions
        if any(k in msg for k in ["next", "focus", "plan", "train", "tomorrow"]):
            return (
                f"🎯 **Next Workout Action Plan**:\n"
                f"- **Primary Focus**: {focus}\n"
                f"- **Target Exercise**: {top_ex}\n"
                f"- **Target Goal**: {goal.capitalize()}\n\n"
                f"Tip: Do a proper 5-minute dynamic warm-up before stepping in front of the camera for pose tracking!"
            )

        # 4. Nutrition / Calorie Questions
        if any(k in msg for k in ["nutrition", "food", "calorie", "diet", "macro", "protein"]):
            if nutr.get("logs_count_today", 0) == 0:
                return (
                    f"🥗 **Nutrition Status for Today**:\n"
                    f"- **Daily Calorie Target**: {cals_target} kcal\n"
                    f"- **Protein Target**: {p_target}g\n\n"
                    f"You haven't logged any meals yet today. Head to the **Nutrition** tab to log your meals or generate a custom meal plan!"
                )
            return (
                f"🥗 **Nutrition Status Today**:\n"
                f"- **Calories Consumed**: {consumed} / {cals_target} kcal ({rem_cals} kcal remaining)\n"
                f"- **Protein**: {p_consumed}g / {p_target}g\n"
                f"- **Meals Logged Today**: {nutr.get('logs_count_today', 0)}\n\n"
                f"Ensure you reach your protein intake to support muscle recovery after your workouts!"
            )

        # 5. Motivation / Encouragement Questions
        if any(k in msg for k in ["motivation", "inspire", "tired", "hard", "push", "energy"]):
            return (
                f"🔥 **Your Daily Motivation**:\n"
                f"\"Consistency beats intensity every single time.\"\n\n"
                f"You are working towards **{goal}**. Every rep you log and every meal you track brings you closer to your target. "
                f"Step up, stay focused, and let's conquer today's session!"
            )

        # 6. Default Personal Fitness Assistant Fallback
        return (
            f"🤖 **Virtual Gym Buddy**:\n"
            f"Hello! I am your AI Gym Buddy tuned to your goal of **{goal}**.\n\n"
            f"Here is a quick snapshot of your active context:\n"
            f"- **Workouts this week**: {total_w} (Avg Score: {avg_score}/100)\n"
            f"- **Calorie Target**: {cals_target} kcal ({rem_cals} kcal remaining today)\n\n"
            f"How can I help you today? You can ask me about your weekly performance, squat form tips, nutrition progress, or workout motivation!"
        )
