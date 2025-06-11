import streamlit as st
import google.generativeai as genai
import textwrap
from login import login_page
from database import add_message, get_messages, create_conversation, get_user_conversations, update_conversation_title

# --- HELPER: GENERATE TITLE FOR CHAT ---
def generate_chat_title(first_user_message, first_ai_response, model):
    prompt = f"""Summarize the following brief exchange into a 5-word-or-less title. Do not use quotes.
    User: "{first_user_message}"
    Assistant: "{first_ai_response}"
    Title:"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "Chat" # Fallback title

# --- 1. MAIN CHATBOT APPLICATION ---
def chatbot_app():
    user_id = st.session_state.user_id
    model = configure_gemini()
    initialize_chatbot_session() # Initializes session state variables

    # --- SIDEBAR: CHAT HISTORY & CONTROLS ---
    st.sidebar.title(f"Welcome, {st.session_state['username']}!")

    if st.sidebar.button("➕ New Chat", use_container_width=True):
        initialize_chatbot_session() # Resets session state for a new chat
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### History")

    # Load and display conversation history
    conversations = get_user_conversations(user_id)
    for conv in conversations:
        if st.sidebar.button(f"💬 {conv['title']}", key=f"conv_{conv['id']}", use_container_width=True):
            # Load selected conversation
            st.session_state.conversation_id = conv['id']
            st.session_state.messages = get_messages(conv['id'])
            st.session_state.assessment_active = False # Reset assessment state
            st.session_state.show_initial_buttons = False
            st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- MAIN CHAT UI ---
    st.title("Mental Health Companion")
    st.markdown("""
    <style>
        .stApp {
            background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%) !important;
            background-attachment: fixed !important;
            background-size: cover !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Display initial message if it's a new, empty chat
    if not st.session_state.messages:
        initial_message = "👋 Hello! I'm your **Mental Health Companion**.<br><br>I can help you with a quick PHQ-9 depression screening.<br><br>Would you like to begin? 😊"
        st.markdown(f"""<div style="display: flex; align-items: flex-start; justify-content: flex-start; margin-bottom: 1rem;"><img src="https://www.iconpacks.net/icons/2/free-robot-icon-2760-thumb.png" alt="Assistant" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px; margin-top: 5px;"><div style="background-color: #f0f2f6; color: #31333F; border-radius: 1rem; padding: 1rem; max-width: 80%; word-wrap: break-word; box-shadow: 0 4px 8px rgba(0,0,0,0.06);">{initial_message}</div></div>""", unsafe_allow_html=True)

    # Display chat history from the active conversation
    for msg in st.session_state.messages:
        # Display logic is the same, just a different source for `messages`
        if msg["role"] == "user":
            st.markdown(f"""<div style="display: flex; align-items: flex-start; justify-content: flex-end; margin-bottom: 1rem;"><div style="background-color: #0b93f6; color: white; border-radius: 1rem; padding: 1rem; max-width: 80%; word-wrap: break-word; box-shadow: 0 4px 8px rgba(0,0,0,0.06);">{msg['content']}</div><img src="https://img.icons8.com/?size=100&id=rrtYnzKMTlUr&format=png&color=000000" alt="User" style="width: 40px; height: 40px; border-radius: 50%; margin-left: 10px; margin-top: 5px;"></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="display: flex; align-items: flex-start; justify-content: flex-start; margin-bottom: 1rem;"><img src="https://img.icons8.com/?size=100&id=rYb1JFR9WLSh&format=png&color=000000" alt="Assistant" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px; margin-top: 5px;"><div style="background-color: #f0f2f6; color: #31333F; border-radius: 1rem; padding: 1rem; max-width: 80%; word-wrap: break-word; box-shadow: 0 4px 8px rgba(0,0,0,0.06);">{msg['content']}</div></div>""", unsafe_allow_html=True)

    # --- CHAT INPUT & RESPONSE LOGIC ---
    def handle_message(user_input):
        # 1. If this is the first message, create a new conversation in the DB
        if st.session_state.conversation_id is None:
            st.session_state.conversation_id = create_conversation(user_id)
        
        # 2. Add user message to session and DB
        st.session_state.messages.append({"role": "user", "content": user_input})
        add_message(st.session_state.conversation_id, "user", user_input)

        # 3. Generate and add AI response
        with st.spinner("Thinking..."):
            if detect_assessment_intent(user_input, model) and not st.session_state.assessment_active:
                st.session_state.assessment_active = True
                response = "It sounds like you'd like to start the assessment. Let's begin!"
            else:
                response = handle_conversation(user_input, model)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            add_message(st.session_state.conversation_id, "assistant", response)

            # 4. If it was the first exchange, generate and update the title
            if len(st.session_state.messages) == 2:
                new_title = generate_chat_title(user_input, response, model)
                update_conversation_title(st.session_state.conversation_id, new_title)

        st.rerun()

    # --- UI Elements for Interaction ---
    if st.session_state.get("show_initial_buttons", False):
        col1, col2, _ = st.columns([1.2, 1, 3])
        if col1.button("Yes, let's start!"):
            st.session_state.show_initial_buttons, st.session_state.assessment_active = False, True
            handle_message("Yes, let's start the assessment.")
        if col2.button("No, thanks"):
            st.session_state.show_initial_buttons = False
            handle_message("No, thanks.")
    
    if st.session_state.assessment_active:
        run_assessment(model)
    else:
        if user_input := st.chat_input("Type your message..."):
            st.session_state.show_initial_buttons = False
            handle_message(user_input)

# --- 2. HELPER FUNCTIONS ---
def configure_gemini():
    try:
        genai.configure(api_key=st.secrets.api_keys.google)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        st.error(f"Failed to configure Gemini: {e}. Ensure GOOGLE_API_KEY is in st.secrets.")
        st.stop()

def initialize_chatbot_session():
    """Initializes or resets session state for a conversation."""
    if "messages" not in st.session_state: st.session_state.messages = []
    if "conversation_id" not in st.session_state: st.session_state.conversation_id = None
    if "show_initial_buttons" not in st.session_state: st.session_state.show_initial_buttons = True
    if "assessment_active" not in st.session_state: st.session_state.assessment_active = False
    if "current_question" not in st.session_state: st.session_state.current_question = 0
    if "answers" not in st.session_state: st.session_state.answers = []

# All other helper functions (run_assessment, store_answer, show_results, etc.)
# are updated to use the active conversation_id from session_state.

def store_answer(q_index, score, user_response):
    conv_id = st.session_state.conversation_id
    st.session_state.answers.append(score)
    user_msg_content = f"Q{q_index+1} Response: '{user_response}'"
    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    add_message(conv_id, "user", user_msg_content)
    st.session_state.current_question += 1
    st.rerun()

def show_results():
    conv_id = st.session_state.conversation_id
    total_score = sum(st.session_state.answers)
    severity, feedback_details = "", "" # Logic for this is unchanged
    if total_score <= 4: severity, feedback_details = "Minimal or None", textwrap.dedent("""*   **Positive Reinforcement:** You're doing great! Keep it up! 🌱 *   **Continued Self-Care:** Continue to prioritize activities that support your well-being.""")
    elif 5 <= total_score <= 9: severity, feedback_details = "Mild", textwrap.dedent("""*   **Lifestyle Suggestions:** Consider focusing on areas like sleep hygiene or a healthy balance with screen time. *   **Self-Care Techniques:** This is a good time to be proactive with journaling or relaxation exercises.""")
    elif 10 <= total_score <= 14: severity, feedback_details = "Moderate", textwrap.dedent("""*   **Stress Management:** Your score suggests notable stress. Techniques from CBT can be very effective. *   **Encourage Connection:** Please consider talking to a trusted friend or family member.""")
    elif 15 <= total_score <= 19: severity, feedback_details = "Moderately Severe", textwrap.dedent("""*   **Encourage Professional Help:** I strongly encourage you to consider speaking with a therapist or counselor. *   **Guided Exercises:** Structured exercises like guided meditations can provide stability.""")
    else: severity, feedback_details = "Severe", """<div style="border: 2px solid #FF4B4B; border-radius: 10px; padding: 1rem; background-color: #FFF0F0;"><h3 style="color: #D32F2F;">A Gentle Check-In...</h3><p>Your answers suggest you might be going through a particularly tough time. The most important thing is your safety.</p><p><strong>You are not alone, and immediate help is available. Please connect with someone right away:</strong></p><ul><li><strong>Talk or Text:</strong> Call or text <b>999</b> anytime in the Malaysia.</li><li><strong>Medical Support:</strong> Contact a doctor or therapist.</li></ul></div>"""
    final_feedback_content = f"## 📊 Assessment Complete\n\n**Your total PHQ-9 score is: {total_score}/27**\n\n**Interpretation:** {severity}\n\n---\n\n### Suggestions & Next Steps\n\n{feedback_details}\n\n---\n**Disclaimer:** I am an AI, not a medical professional. Please consult a healthcare provider for medical advice."
    st.session_state.messages.append({"role": "assistant", "content": final_feedback_content})
    add_message(conv_id, "assistant", final_feedback_content)
    reset_assessment()
    st.rerun()

def run_assessment(model):
    # This function's logic is largely unchanged, it just calls the updated store_answer
    questions = ["Little interest or pleasure in doing things", "Feeling down, depressed, or hopeless", "Trouble falling/staying asleep, or sleeping too much", "Feeling tired or having little energy", "Poor appetite or overeating", "Feeling bad about yourself or that you're a failure", "Trouble concentrating on things", "Moving/speaking slowly or being fidgety/restless", "Thoughts that you would be better off dead or hurting yourself"]
    q_index = st.session_state.current_question
    if q_index < len(questions):
        current_q = questions[q_index]
        question_text = f"**Question {q_index + 1}/{len(questions)}:** Over the last 2 weeks, how often have you been bothered by... <br><br>> {current_q}"
        st.markdown(f"""<div style="display: flex; align-items: flex-start; justify-content: flex-start; margin-bottom: 1rem;"><img src="https://www.iconpacks.net/icons/2/free-robot-icon-2760-thumb.png" alt="Assistant" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px; margin-top: 5px;"><div style="background-color: #f0f2f6; color: #31333F; border-radius: 1rem; padding: 1rem; max-width: 80%; word-wrap: break-word; box-shadow: 0 4px 8px rgba(0,0,0,0.06);">{question_text}</div></div>""", unsafe_allow_html=True)
        number_input = st.radio("Select how often:", options=["0", "1", "2", "3"], index=None, key=f"radio_{q_index}", format_func=lambda x: ["0: Not at all", "1: Several days", "2: More than half", "3: Nearly every day"][int(x)], horizontal=True)
        text_input = st.text_input("Or, describe your experience:", key=f"text_{q_index}", placeholder="e.g., 'Constantly' or 'Not really'")
        if number_input is not None: store_answer(q_index, int(number_input), number_input)
        elif text_input:
            with st.spinner("Analyzing..."): score = interpret_response(current_q, text_input, model)
            if score is not None: store_answer(q_index, score, text_input)
            else: st.error("I had trouble understanding that.")
    else: show_results()

# --- Unchanged Helper Functions ---
def detect_assessment_intent(query, model):
    prompt = f"""Analyze the user's intent. Does their message indicate they want to start a test, screening, or assessment? Respond with a single word: 'yes' or 'no'. User message: "{query}" """
    try: return model.generate_content(prompt).text.strip().lower() == "yes"
    except Exception: return False
def interpret_response(question, text, model):
    prompt = f"""Analyze this response to: "{question}". Map it to a score from 0-3 where 0=Not at all, 1=Several days, 2=More than half the days, 3=Nearly every day. User's description: "{text}". Respond ONLY with the number."""
    try: return int(model.generate_content(prompt).text.strip())
    except Exception: return None
def handle_conversation(query, model):
    # Use only messages from the current session for context
    context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
    prompt = f"You are a friendly and empathetic Mental Health Companion. Given the context, provide a caring response to the user's message. Context:\n{context}\nUser's message: \"{query}\""
    return model.generate_content(prompt).text
def reset_assessment():
    st.session_state.assessment_active = False
    st.session_state.current_question = 0
    st.session_state.answers = []

# --- 3. MAIN ORCHESTRATOR ---
def main():
    st.set_page_config(page_title="Mental Health Companion", layout="centered", initial_sidebar_state="auto")
    if not st.session_state.get("logged_in", False):
        login_page()
    else:
        chatbot_app()

if __name__ == "__main__":
    main()
