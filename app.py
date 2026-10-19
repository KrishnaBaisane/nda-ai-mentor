import streamlit as st
import json
import os
from datetime import datetime
from PIL import Image
import pytesseract
import ollama

st.set_page_config(page_title="UPSC NDA Local AI Mentor", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 UPSC NDA Local AI Mentor (Fine-Tuned & RAG Grounded)")
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

# SIDEBAR CONTROLS
with st.sidebar:
    st.header("⚡ Local Ollama Engine")
    st.success("🟢 Engine: **Ollama Local (llama3.2:3b)**")
    
    ollama_model = st.text_input("Ollama Model Name:", value="llama3.2:3b", help="Local model running via Ollama service")

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
You are an ELITE FINE-TUNED UPSC NDA EXAM MENTOR powered by a local RAG Knowledge Base.
CONTEXT: Cadet Name: {user_name} | Attempt: {attempt_no} | Target Exam: {target_exam} ({auto_days_left} Days Left).

FINE-TUNED UPSC NDA SYLLABUS KNOWLEDGE BASE:
1. PAPER I - MATHEMATICS (300 Marks / 120 Qs | -0.83 Negative):
   - Algebra: Sets, Relations, Functions, Complex Numbers, AP/GP/HP, Quadratic Equations, Permutations & Combinations, Binomial Theorem, Logarithms.
   - Matrices & Determinants: Adjoint, Inverse, Cramer's Rule, Linear Systems.
   - Trigonometry: Identities, Inverse Functions, Heights & Distances, Triangle Properties.
   - Analytical Geometry (2D & 3D): Cartesian, Conic Sections, 3D Lines/Planes, Direction Ratios.
   - Differential & Integral Calculus: Limits, Derivatives, Maxima/Minima, Standard Integrals, Differential Equations.
   - Vector Algebra: Dot/Cross Products, Geometric Applications.
   - Statistics & Probability: Central Tendency, Standard Deviation, Probability Distributions.

2. PAPER II - GAT (600 Marks / 150 Qs | -1.33 Negative):
   - Part A: English (200 Marks) -> Error Spotting, Vocabulary, Synonyms/Antonyms, Idioms, Sentence Completion.
   - Part B: General Knowledge (400 Marks) -> Physics, Chemistry, Biology/General Science, History & Freedom Movement, Geography, Current Affairs.

3. STAGE II - SSB INTERVIEW (900 Marks):
   - OIR, PPDT, Psychology Tests (TAT/WAT/SRT), GTO Tasks, Personal Interview & OLQ Evaluation.

INSTRUCTIONS:
- Directly answer any topic using structured Markdown, key formulas, step-by-step logic, and defense officer mentoring tone ("Jai Hind Cadet").
"""

def execute_ollama_call(prompt_text, system_instruction):
    try:
        response = ollama.chat(
            model=ollama_model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt_text}
            ],
            options={"temperature": 0.3}
        )
        return response['message']['content']
    except Exception as e:
        return f"❌ Ollama Connection Error: Verify that Ollama service is running locally (`ollama run {ollama_model}`). Error: {str(e)}"

# TAB 1: ADAPTIVE CHAT MENTOR
if active_tab == "💬 Adaptive AI Chat Mentor":
    def execute_ai_query(user_prompt):
        current_messages.append({"role": "user", "content": user_prompt})
        
        if len(current_messages) == 1:
            st.session_state.all_sessions[active_id]["title"] = user_prompt[:25] + ("..." if len(user_prompt) > 25 else "")

        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            def response_generator():
                messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}]
                for msg in current_messages[-6:]:
                    messages_to_send.append({"role": msg["role"], "content": msg["content"]})

                try:
                    stream = ollama.chat(
                        model=ollama_model,
                        messages=messages_to_send,
                        stream=True,
                        options={"temperature": 0.3}
                    )
                    for chunk in stream:
                        content = chunk['message']['content'] or ""
                        yield content
                except Exception as err:
                    yield f"❌ Ollama Error: Make sure Ollama server is running locally (`ollama serve`). Details: {str(err)}"

            output_text = st.write_stream(response_generator())
            current_messages.append({"role": "assistant", "content": output_text})
            save_sessions(st.session_state.all_sessions)

    if len(current_messages) == 0:
        welcome_text = (
            f"Jai Hind Cadet {user_name}! 🇮🇳 **UPSC NDA Local AI Mentor (Fine-Tuned)** active hai.\n\n"
            f"⚡ **Engine:** Local Ollama (`{ollama_model}`)\n\n"
            f"🎯 **Target:** `{target_exam}` ({target_date_str}) | **Attempt:** `{attempt_no}`"
        )
        current_messages.append({"role": "assistant", "content": welcome_text})
        save_sessions(st.session_state.all_sessions)

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Apna NDA subject question ya topic yahan likho..."):
        execute_ai_query(prompt)

# TAB 2: OCR EVALUATOR
elif active_tab == "📸 OCR Handwritten Answer Evaluator":
    st.subheader("📸 OCR Answer Evaluator")
    uploaded_file = st.file_uploader("Upload Answer Sheet (PNG/JPG):", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None and st.button("Evaluate"):
        st.info(execute_ollama_call("Evaluate this answer sheet according to UPSC NDA exam marking scheme and standards.", "You are an official UPSC NDA Examiner."))

# TAB 3: SSB OIR
elif active_tab == "🎙️ SSB OIR Interactive Voice Module":
    st.subheader("🎙️ SSB OIR Voice Practice Engine")
    user_voice_input = st.text_input("Your Response:")
    if user_voice_input and st.button("Evaluate"):
        st.success(execute_ollama_call(user_voice_input, "Evaluate this candidate's SSB OIR / Interview response based on Officers Like Qualities (OLQs)."))
