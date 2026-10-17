import streamlit as st
import ollama
import google.generativeai as genai
import json
import os
from datetime import datetime
from PIL import Image
import pytesseract

st.set_page_config(page_title="NDA Exam Prep & Advanced AI Mentor", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 NDA Exam Prep & Adaptive Dual-Engine AI Mentor")
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

# SIDEBAR
with st.sidebar:
    st.header("⚡ AI Engine Selection")
    ai_engine_mode = st.radio(
        "Select Model Provider:",
        ["🟢 Offline (Local RTX 3050 GPU - Llama 3.2)", "🌐 Online Cloud API (Google Gemini)"],
        index=1
    )

    if "Online" in ai_engine_mode:
        gemini_key = st.text_input("Gemini API Key (Optional Override):", type="password", placeholder="Paste Key...")
    else:
        gemini_key = ""

    st.markdown("---")
    st.header("🚀 Advanced Modules")
    active_tab = st.radio(
        "Select Feature Mode:",
        ["💬 Adaptive AI Chat Mentor", "📸 OCR Handwritten Answer Evaluator", "🎙️ SSB OIR Interactive Voice Module"]
    )

    st.markdown("---")
    st.header("👤 Cadet Profile")
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
    days_left = auto_days_left
    mock_days = 0
    st.metric(label=f"🎯 Target: {target_exam}", value=f"{auto_days_left} Days Left")

active_id = st.session_state.current_session_id
current_messages = st.session_state.all_sessions[active_id]["messages"]

SYSTEM_PROMPT = f"You are an ELITE UPSC NDA EXAM MENTOR for Cadet {user_name} ({attempt_no}). Provide structured, high-yield guidance."

def get_gemini_model():
    """Auto-detect available Gemini model to bypass 404 errors"""
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if available:
            model_name = available[0].replace("models/", "")
            return genai.GenerativeModel(model_name=model_name)
    except Exception:
        pass
    return genai.GenerativeModel(model_name="gemini-1.5-flash")

def execute_llm_call(prompt_text, system_instruction):
    if "Online" in ai_engine_mode:
        active_key = gemini_key or st.secrets.get("GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        if not active_key:
            return "⚠️ Gemini API Key Missing!"
        try:
            genai.configure(api_key=active_key)
            model = get_gemini_model()
            response = model.generate_content(f"{system_instruction}\n\n{prompt_text}")
            return response.text
        except Exception as e:
            return f"❌ Gemini Error: {str(e)}"
    else:
        try:
            res = ollama.chat(model='llama3.2:3b', messages=[{'role': 'system', 'content': system_instruction}, {'role': 'user', 'content': prompt_text}])
            return res['message']['content']
        except Exception as e:
            return f"❌ Local Ollama Error: {str(e)}"

# TAB 1: CHAT MENTOR
if active_tab == "💬 Adaptive AI Chat Mentor":
    if len(current_messages) == 0:
        welcome_text = f"Jai Hind Cadet {user_name}! 🇮🇳 NDA AI Mentor is active. Target: `{target_exam}`."
        current_messages.append({"role": "assistant", "content": welcome_text})
        save_sessions(st.session_state.all_sessions)

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask your NDA prep question..."):
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            active_key = gemini_key or st.secrets.get("GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
            if "Online" in ai_engine_mode and active_key:
                try:
                    genai.configure(api_key=active_key)
                    model = get_gemini_model()
                    response = model.generate_content(prompt)
                    ans = response.text
                except Exception as e:
                    ans = f"❌ Gemini Error: {str(e)}"
            else:
                ans = execute_llm_call(prompt, SYSTEM_PROMPT)

            st.markdown(ans)
            current_messages.append({"role": "assistant", "content": ans})
            save_sessions(st.session_state.all_sessions)

# TAB 2: OCR EVALUATOR
elif active_tab == "📸 OCR Handwritten Answer Evaluator":
    st.subheader("📸 OCR Mock Answer Sheet Evaluator")
    uploaded_file = st.file_uploader("Upload Image:", type=["png", "jpg", "jpeg"])
    if uploaded_file and st.button("Evaluate"):
        st.info(execute_llm_call("Evaluate this answer sheet.", "You are a UPSC NDA Evaluator."))

# TAB 3: SSB OIR
elif active_tab == "🎙️ SSB OIR Interactive Voice Module":
    st.subheader("🎙️ SSB OIR Practice Module")
    user_input = st.text_input("Your Response:")
    if user_input and st.button("Evaluate Logic"):
        st.success(execute_llm_call(user_input, "You are an SSB OIR Assessor."))
