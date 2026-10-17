import streamlit as st
import json
import os
from datetime import datetime
from PIL import Image
import pytesseract
from groq import Groq

st.set_page_config(page_title="NDA Exam Prep & Debug AI Mentor", page_icon="🎓", layout="wide")

# Custom UI Styling
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 NDA Exam Prep & AI Mentor (Direct Key Mode)")
st.markdown("---")

HISTORY_FILE = "nda_chat_sessions.json"

def load_sessions():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sessions(sessions):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def get_nda_exam_details():
    today = datetime.now()
    year = today.year
    nda_1_date = datetime(year, 4, 19)
    nda_2_date = datetime(year, 9, 6)

    if today <= nda_1_date:
        target_exam = f"UPSC NDA I {year}"
        exam_date_str = nda_1_date.strftime("%d %B %Y")
        days_left = (nda_1_date - today).days
    elif today <= nda_2_date:
        target_exam = f"UPSC NDA II {year}"
        exam_date_str = nda_2_date.strftime("%d %B %Y")
        days_left = (nda_2_date - today).days
    else:
        target_exam = f"UPSC NDA I {year + 1}"
        next_nda_1 = datetime(year + 1, 4, 19)
        exam_date_str = next_nda_1.strftime("%d %B %Y")
        days_left = (next_nda_1 - today).days

    return target_exam, exam_date_str, max(1, days_left), today.strftime("%d %B %Y")

target_exam, target_date_str, auto_days_left, current_today_str = get_nda_exam_details()

if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = load_sessions()

if "current_session_id" not in st.session_state:
    default_id = f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state.current_session_id = default_id
    if default_id not in st.session_state.all_sessions:
        st.session_state.all_sessions[default_id] = {"title": "General NDA Prep", "messages": []}
        save_sessions(st.session_state.all_sessions)

if "active_groq_key" not in st.session_state:
    st.session_state.active_groq_key = ""

# SIDEBAR CONTROLS
with st.sidebar:
    st.header("🔑 Direct Key Auth")
    
    # Key Input & Proceed Button
    groq_key_input = st.text_input("Enter Groq API Key:", type="password", placeholder="gsk_...", value=st.session_state.active_groq_key, help="Paste your Groq Key here and click Proceed!")
    
    if st.button("🚀 Proceed & Connect Key"):
        if groq_key_input.strip():
            st.session_state.active_groq_key = groq_key_input.strip()
            st.success("✅ Key Locked & Ready!")
            st.rerun()
        else:
            st.error("⚠️ Pehle Key enter karein!")

    if st.session_state.active_groq_key:
        st.info("🟢 Groq Engine Connected")
    else:
        st.warning("🔴 Engine Disconnected (Key Needed)")

    st.markdown("---")
    st.header("🚀 Advanced Modules")
    active_tab = st.radio(
        "Select Feature Mode:",
        ["💬 Adaptive AI Chat Mentor", "📸 OCR Handwritten Answer Evaluator", "🎙️ SSB OIR Interactive Voice Module"]
    )

    st.markdown("---")
    st.header("👤 Cadet Profile & Sessions")
    user_name = st.text_input("Cadet Name:", value="Aspirant")
    attempt_no = st.selectbox("Attempt Status:", ["1st Attempt", "2nd Attempt (Repeater)", "3rd Attempt (Repeater)", "Last Attempt"])
    
    if st.button("➕ Start New Subject Session"):
        new_id = f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.current_session_id = new_id
        st.session_state.all_sessions[new_id] = {"title": f"Session {len(st.session_state.all_sessions) + 1}", "messages": []}
        save_sessions(st.session_state.all_sessions)
        st.rerun()

    session_options = {sid: data["title"] for sid, data in st.session_state.all_sessions.items()}
    selected_session = st.selectbox(
        "Switch Subject Chat:",
        options=list(session_options.keys()),
        format_func=lambda sid: session_options[sid],
        index=list(session_options.keys()).index(st.session_state.current_session_id)
    )
    
    if selected_session != st.session_state.current_session_id:
        st.session_state.current_session_id = selected_session
        st.rerun()

    st.markdown("---")
    st.info(f"📅 Today: **{current_today_str}**")
    st.metric(label=f"🎯 Target: {target_exam}", value=f"{auto_days_left} Days Left", help=f"Scheduled Date: {target_date_str}")

active_id = st.session_state.current_session_id
current_messages = st.session_state.all_sessions[active_id]["messages"]

SYSTEM_PROMPT = f"""
You are an ELITE UPSC NDA EXAM MENTOR powered by Groq.
CONTEXT: Name: {user_name} | Attempt: {attempt_no} | Target: {target_exam} ({auto_days_left} Days Left).

RULES:
1. CUTOFF: Sectional min 25% (75/300 Math, 150/600 GAT). Written target: 350-360/900.
2. Provide structured, sharp, high-yield Markdown responses for NDA preparation.
"""

def get_active_groq_model(client):
    preferred_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768"
    ]
    try:
        available = [m.id for m in client.models.list().data]
        for model in preferred_models:
            if model in available:
                return model
        if available:
            return available[0]
    except Exception:
        pass
    return "llama-3.1-8b-instant"

# TAB 1: ADAPTIVE CHAT MENTOR
if active_tab == "💬 Adaptive AI Chat Mentor":
    def execute_ai_query(user_prompt):
        if not st.session_state.active_groq_key:
            st.error("👈 Pehle Sidebar mein apni Groq API Key daal kar 'Proceed' button dabayein!")
            return

        current_messages.append({"role": "user", "content": user_prompt})
        
        if len(current_messages) == 1:
            st.session_state.all_sessions[active_id]["title"] = user_prompt[:25] + ("..." if len(user_prompt) > 25 else "")

        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            def response_generator():
                try:
                    client = Groq(api_key=st.session_state.active_groq_key)
                    chosen_model = get_active_groq_model(client)
                    
                    messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}]
                    for msg in current_messages[-6:]:
                        messages_to_send.append({"role": msg["role"], "content": msg["content"]})
                    
                    completion = client.chat.completions.create(
                        model=chosen_model,
                        messages=messages_to_send,
                        stream=True
                    )
                    for chunk in completion:
                        content = chunk.choices[0].delta.content or ""
                        yield content
                except Exception as e:
                    yield f"❌ Debug Error: {str(e)}"

            output_text = st.write_stream(response_generator())
            current_messages.append({"role": "assistant", "content": output_text})
            save_sessions(st.session_state.all_sessions)

    if len(current_messages) == 0:
        welcome_text = (
            f"Jai Hind Cadet {user_name}! 🇮🇳 **UPSC NDA Groq AI Mentor** active hai.\n\n"
            f"👈 **Sidebar mein Key paste karke 'Proceed' button dabayein.**\n\n"
            f"🎯 **Target:** `{target_exam}` ({target_date_str}) | **Attempt:** `{attempt_no}`"
        )
        current_messages.append({"role": "assistant", "content": welcome_text})
        save_sessions(st.session_state.all_sessions)

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Apna question yahan likho..."):
        execute_ai_query(prompt)

# TAB 2: OCR EVALUATOR
elif active_tab == "📸 OCR Handwritten Answer Evaluator":
    st.subheader("📸 OCR Answer Evaluator")
    if not st.session_state.active_groq_key:
        st.warning("👈 Sidebar mein Groq API Key daal kar Proceed karein!")

# TAB 3: SSB OIR
elif active_tab == "🎙️ SSB OIR Interactive Voice Module":
    st.subheader("🎙️ SSB OIR Voice Practice")
    if not st.session_state.active_groq_key:
        st.warning("👈 Sidebar mein Groq API Key daal kar Proceed karein!")
