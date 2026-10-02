import streamlit as st
from google import genai
import requests
import time


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide"
)


# =========================================================
# APP TITLE
# =========================================================

st.title("🤖 AI Assistant")

st.caption(
    "Ask questions, have conversations, write, code, "
    "learn, brainstorm, and more."
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
# CHAT MEMORY
# =========================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


# =========================================================
# SYSTEM INSTRUCTIONS
# =========================================================

SYSTEM_PROMPT = """
You are a helpful, intelligent general-purpose AI assistant.

Your job is to help the user with a wide variety of tasks.

You can help with:

- General questions
- School subjects
- Mathematics
- Science
- History
- Writing
- Rewriting
- Summarizing
- Brainstorming
- Coding
- Debugging
- Explanations
- Planning
- Creative ideas
- Research assistance
- Productivity
- Learning

Be clear, helpful, and accurate.

When solving a problem, explain the important reasoning
rather than simply giving an unexplained answer.

If the user asks you to write something, provide a polished
version they can use.

If you are uncertain about something, say so rather than
inventing facts.

Do not claim to have performed actions that you cannot
actually perform.

Keep responses reasonably organized and easy to read.
"""


# =========================================================
# GEMINI
# =========================================================

def ask_gemini(messages):

    if gemini_client is None:
        return None

    conversation = SYSTEM_PROMPT + "\n\n"

    for message in messages:

        role = message["role"]
        content = message["content"]

        conversation += (
            f"{role.upper()}:\n{content}\n\n"
        )

    for attempt in range(2):

        try:

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=conversation
            )

            if response and response.text:

                return response.text

            return None

        except Exception as e:

            error_text = str(e)

            # Temporary Gemini outage
            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "high demand" in error_text.lower()
            ):

                if attempt == 0:

                    time.sleep(3)

                    continue

                return None

            # Gemini quota
            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "quota" in error_text.lower()
            ):

                return None

            # Model unavailable
            if (
                "404" in error_text
                or "NOT_FOUND" in error_text
            ):

                return None

            return None

    return None


# =========================================================
# OPENROUTER
# =========================================================

def ask_openrouter(messages):

    if not OPENROUTER_API_KEY:

        return None

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",
        "X-Title": "AI Assistant"
    }

    openrouter_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    for message in messages:

        openrouter_messages.append(
            {
                "role": message["role"],
                "content": message["content"]
            }
        )

    data = {
        "model": OPENROUTER_MODEL,
        "messages": openrouter_messages
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
# AI ROUTER
# =========================================================

def ask_ai(messages):

    # Try Gemini first
    result = ask_gemini(messages)

    if result:

        return result, "Gemini"


    # Try OpenRouter
    result = ask_openrouter(messages)

    if result:

        return result, "OpenRouter"


    return None, None


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("⚙️ Settings")

    st.write(
        "AI providers:"
    )

    if GEMINI_API_KEY:

        st.success(
            "🟢 Gemini connected"
        )

    else:

        st.warning(
            "🟡 Gemini not configured"
        )


    if OPENROUTER_API_KEY:

        st.success(
            "🟢 OpenRouter connected"
        )

    else:

        st.warning(
            "🟡 OpenRouter not configured"
        )


    st.divider()


    if st.button(
        "🗑️ Clear Conversation",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.rerun()


    st.divider()

    st.caption(
        "AI Assistant"
    )


# =========================================================
# DISPLAY PREVIOUS MESSAGES
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# CHAT INPUT
# =========================================================

user_prompt = st.chat_input(
    "Message your AI assistant..."
)


# =========================================================
# PROCESS USER MESSAGE
# =========================================================

if user_prompt:

    # Add user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_prompt
        }
    )


    # Display user message
    with st.chat_message("user"):

        st.markdown(
            user_prompt
        )


    # Ask AI
    with st.chat_message("assistant"):

        with st.spinner(
            "Thinking..."
        ):

            answer, provider = ask_ai(
                st.session_state.messages
            )


        if answer:

            st.markdown(
                answer
            )

            # Save response
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

            # Small provider indicator
            st.caption(
                f"Powered by {provider}"
            )

        else:

            st.error(
                "⚠️ I couldn't get a response "
                "from the available AI providers."
            )

            st.info(
                "Please try again later."
            )
