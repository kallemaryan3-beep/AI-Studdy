import streamlit as st
from google import genai
import requests
import json
import re
import time


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="Study Buddy",
    page_icon="📚",
    layout="wide"
)


# =========================================================
# TITLE
# =========================================================

st.title("📚 Study Buddy")

st.write(
    "Your AI study assistant for questions, quizzes, "
    "flashcards, study guides, and more."
)


# =========================================================
# API KEYS
# =========================================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    GEMINI_API_KEY = None

try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except KeyError:
    OPENROUTER_API_KEY = None


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = None

if GEMINI_API_KEY:

    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception:
        gemini_client = None


# =========================================================
# MODELS
# =========================================================

GEMINI_MODEL = "gemini-3.8-flash"

OPENROUTER_MODEL = "openrouter/free"


# =========================================================
# GEMINI FUNCTION
# =========================================================

def ask_gemini(prompt):

    if gemini_client is None:
        return None

    for attempt in range(2):

        try:

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

            if response and response.text:
                return response.text

            return None

        except Exception as e:

            error_text = str(e)

            # Temporary Gemini overload
            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "high demand" in error_text.lower()
            ):

                if attempt == 0:
                    time.sleep(3)
                    continue

                return None

            # Gemini quota exceeded
            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "quota" in error_text.lower()
            ):

                return None

            # Gemini model unavailable
            if (
                "404" in error_text
                or "NOT_FOUND" in error_text
            ):

                return None

            return None

    return None


# =========================================================
# OPENROUTER FUNCTION
# =========================================================

def ask_openrouter(prompt):

    if not OPENROUTER_API_KEY:
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ai-study-buddy-ak.streamlit.app",
        "X-Title": "Study Buddy"
    }

    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=90
        )

        if response.status_code != 200:
            return None

        result = response.json()

        choices = result.get(
            "choices",
            []
        )

        if not choices:
            return None

        message = choices[0].get(
            "message",
            {}
        )

        content = message.get(
            "content"
        )

        if content:
            return content

        return None

    except Exception:

        return None


# =========================================================
# MULTI-AI FUNCTION
# =========================================================

def ask_ai(prompt):

    # Try Gemini first
    result = ask_gemini(prompt)

    if result:
        return result


    # If Gemini fails, try OpenRouter
    result = ask_openrouter(prompt)

    if result:
        return result


    # Both failed
    st.error(
        "⚠️ The AI services are temporarily unavailable."
    )

    st.info(
        "Please try again later."
    )

    return None


# =========================================================
# NOTES
# =========================================================

st.divider()

st.header("📖 Your Notes")

notes = st.text_area(
    "Paste your notes here",
    height=300,
    placeholder=(
        "Paste your class notes here..."
    )
)


# =========================================================
# ASK AI ANYTHING
# =========================================================

st.divider()

st.header("🤖 Ask Study Buddy Anything")

st.write(
    "Ask a question or give Study Buddy a task."
)

user_request = st.text_area(
    "What would you like me to do?",
    height=150,
    placeholder=(
        "Examples:\n"
        "• Explain photosynthesis in simple words.\n"
        "• Help me understand this math problem.\n"
        "• Summarize my notes.\n"
        "• Make me a study plan.\n"
        "• Create practice questions.\n"
        "• Explain this topic like I'm a beginner."
    ),
    key="user_request"
)


if st.button(
    "🤖 Ask Study Buddy",
    use_container_width=True
):

    if not user_request.strip():

        st.warning(
            "Please enter something for Study Buddy to do."
        )

    else:

        prompt = f"""
You are Study Buddy, a helpful AI assistant.

Help the student with their request.

You can help with:
- School subjects
- Explanations
- Summaries
- Study plans
- Brainstorming
- Practice questions
- Writing assistance
- General questions
- Step-by-step educational explanations
- Other reasonable tasks the user asks for

If the request involves schoolwork, explain the
reasoning clearly so the student can understand it.

If notes are provided, use them when relevant.

Do not invent information.

USER REQUEST:

{user_request}

STUDENT NOTES:

{notes if notes.strip() else "No notes were provided."}
"""

        with st.spinner(
            "🤖 Study Buddy is thinking..."
        ):

            answer = ask_ai(prompt)

        if answer:

            st.session_state.last_answer = answer


# =========================================================
# DISPLAY AI ANSWER
# =========================================================

if "last_answer" in st.session_state:

    st.divider()

    st.header("💬 Study Buddy's Answer")

    st.markdown(
        st.session_state.last_answer
    )


# =========================================================
# STUDY TOOLS
# =========================================================

st.divider()

st.header("🎓 Study Tools")

option = st.selectbox(
    "Choose a tool:",
    [
        "📝 Quiz",
        "🧠 Flashcards",
        "📚 Study Guide",
        "💡 Explain My Notes"
    ]
)


# =========================================================
# QUIZ GENERATOR
# =========================================================

def generate_quiz(notes):

    prompt = f"""
Create a 10-question multiple-choice quiz using ONLY
the information in the student's notes.

Return ONLY valid JSON.

Use exactly this format:

[
  {{
    "question": "Question here",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "answer": 0,
    "explanation": "Short explanation"
  }}
]

The answer number means:

0 = first option
1 = second option
2 = third option
3 = fourth option

Do not include markdown.
Do not include anything outside the JSON.

NOTES:

{notes}
"""

    result = ask_ai(prompt)

    if not result:
        return None

    try:

        result = result.strip()

        result = re.sub(
            r"```json|```",
            "",
            result
        ).strip()

        return json.loads(result)

    except Exception as e:

        st.error(
            "❌ The AI returned an invalid quiz."
        )

        st.code(str(e))

        return None


# =========================================================
# FLASHCARD GENERATOR
# =========================================================

def generate_flashcards(notes):

    prompt = f"""
Create 15 flashcards using ONLY the student's notes.

Return ONLY valid JSON.

Use exactly this format:

[
  {{
    "question": "Question here",
    "answer": "Answer here"
  }}
]

Make each question useful for studying.

Do not include markdown.
Do not include anything outside the JSON.

NOTES:

{notes}
"""

    result = ask_ai(prompt)

    if not result:
        return None

    try:

        result = result.strip()

        result = re.sub(
            r"```json|```",
            "",
            result
        ).strip()

        return json.loads(result)

    except Exception as e:

        st.error(
            "❌ The AI returned invalid flashcards."
        )

        st.code(str(e))

        return None


# =========================================================
# STUDY GUIDE
# =========================================================

def generate_study_guide(notes):

    return f"""
You are Study Buddy, a helpful school study assistant.

Turn the student's notes into a clear and organized
study guide.

Use these sections:

# 📌 Main Topics

# 📖 Important Vocabulary

# ⭐ Key Facts

# 🧠 Important Concepts

# ❗ Things to Remember

# 📝 Quick Review

Explain difficult ideas using simple language.

Only use information supported by the notes.

NOTES:

{notes}
"""


# =========================================================
# EXPLAIN NOTES
# =========================================================

def generate_explanation(notes):

    return f"""
You are Study Buddy, a helpful school study assistant.

Explain the student's notes in simple language.

For each major topic:

- Explain what it means.
- Explain the important idea.
- Define difficult vocabulary.
- Give a simple example when useful.
- Explain what the student should remember.

Make the explanation easy for a student to understand.

Do not invent information that is not supported by
the student's notes.

NOTES:

{notes}
"""


# =========================================================
# GENERATE STUDY TOOL
# =========================================================

if st.button(
    "✨ Generate Study Tool",
    use_container_width=True
):

    if not notes.strip():

        st.warning(
            "⚠️ Please paste your notes first."
        )

        st.stop()


    # -----------------------------------------------------
    # QUIZ
    # -----------------------------------------------------

    if option == "📝 Quiz":

        with st.spinner(
            "🤖 Creating your quiz..."
        ):

            quiz = generate_quiz(notes)

        if quiz:

            st.session_state.quiz = quiz

            st.session_state.quiz_answers = {}

            st.session_state.quiz_submitted = {}


    # -----------------------------------------------------
    # FLASHCARDS
    # -----------------------------------------------------

    elif option == "🧠 Flashcards":

        with st.spinner(
            "🤖 Creating your flashcards..."
        ):

            flashcards = generate_flashcards(notes)

        if flashcards:

            st.session_state.flashcards = flashcards


    # -----------------------------------------------------
    # STUDY GUIDE
    # -----------------------------------------------------

    elif option == "📚 Study Guide":

        with st.spinner(
            "🤖 Creating your study guide..."
        ):

            result = ask_ai(
                generate_study_guide(notes)
            )

        if result:

            st.session_state.study_guide = result


    # -----------------------------------------------------
    # EXPLAIN NOTES
    # -----------------------------------------------------

    elif option == "💡 Explain My Notes":

        with st.spinner(
            "🤖 Explaining your notes..."
        ):

            result = ask_ai(
                generate_explanation(notes)
            )

        if result:

            st.session_state.explanation = result


# =========================================================
# FLASHCARDS DISPLAY
# =========================================================

if "flashcards" in st.session_state:

    st.divider()

    st.header("🧠 Flashcards")

    st.write(
        "Click a question to reveal the answer."
    )

    for i, card in enumerate(
        st.session_state.flashcards
    ):

        with st.expander(
            f"❓ {card['question']}"
        ):

            st.success(
                f"💡 {card['answer']}"
            )


# =========================================================
# QUIZ DISPLAY
# =========================================================

if "quiz" in st.session_state:

    st.divider()

    st.header("📝 Quiz")

    quiz = st.session_state.quiz

    for i, question in enumerate(quiz):

        st.subheader(
            f"Question {i + 1} of {len(quiz)}"
        )

        st.write(
            question["question"]
        )

        submitted = (
            st.session_state.quiz_submitted.get(
                i,
                False
            )
        )

        # -------------------------------------------------
        # BEFORE ANSWER
        # -------------------------------------------------

        if not submitted:

            answer = st.radio(
                "Choose your answer:",
                question["options"],
                key=f"quiz_answer_{i}",
                index=None
            )

            if st.button(
                "Submit Answer",
                key=f"submit_{i}"
            ):

                if answer is None:

                    st.warning(
                        "Please choose an answer first."
                    )

                else:

                    selected_index = (
                        question["options"].index(
                            answer
                        )
                    )

                    st.session_state.quiz_answers[i] = (
                        selected_index
                    )

                    st.session_state.quiz_submitted[i] = (
                        True
                    )

                    st.rerun()

        # -------------------------------------------------
        # AFTER ANSWER
        # -------------------------------------------------

        else:

            selected_index = (
                st.session_state.quiz_answers[i]
            )

            correct_index = (
                question["answer"]
            )

            if selected_index == correct_index:

                st.success(
                    "✅ Correct!"
                )

            else:

                st.error(
                    "❌ Incorrect."
                )

            st.info(
                "Correct answer: "
                + question["options"][correct_index]
            )

            st.write(
                "**Explanation:** "
                + question["explanation"]
            )


# =========================================================
# QUIZ SCORE
# =========================================================

if "quiz" in st.session_state:

    quiz = st.session_state.quiz

    submitted_count = len(
        st.session_state.quiz_submitted
    )

    if submitted_count == len(quiz):

        score = 0

        for i, question in enumerate(quiz):

            if (
                st.session_state.quiz_answers.get(i)
                == question["answer"]
            ):

                score += 1

        st.divider()

        st.header("🏆 Quiz Complete!")

        st.write(
            f"You scored **{score}/{len(quiz)}**."
        )

        if st.button(
            "🔄 Make Another Quiz"
        ):

            del st.session_state.quiz

            st.session_state.quiz_answers = {}

            st.session_state.quiz_submitted = {}

            st.rerun()


# =========================================================
# STUDY GUIDE DISPLAY
# =========================================================

if "study_guide" in st.session_state:

    st.divider()

    st.header("📚 Your Study Guide")

    st.markdown(
        st.session_state.study_guide
    )


# =========================================================
# EXPLANATION DISPLAY
# =========================================================

if "explanation" in st.session_state:

    st.divider()

    st.header("💡 Explanation")

    st.markdown(
        st.session_state.explanation
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "📚 Study Buddy • AI-powered learning assistant"
)
