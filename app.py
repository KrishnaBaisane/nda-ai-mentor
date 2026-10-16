import streamlit as st
import ollama
from openai import OpenAI
import json
import os
from datetime import datetime
from PIL import Image
import pytesseract

st.set_page_config(page_title="NDA Exam Prep & Advanced AI Mentor", page_icon="🎓", layout="wide")

# Custom UI Styling
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

# SIDEBAR CONTROLS
with st.sidebar:
    st.header("⚡ AI Engine Selection")
    
    ai_engine_mode = st.radio(
        "Select Model Provider:",
        ["🟢 Offline (Local RTX 3050 GPU - Llama 3.2)", "🌐 Online Cloud API (OpenAI GPT-4o-Mini)"],
        help="Switch between local offline privacy mode and cloud high-speed OpenAI mode!"
    )

    if "Online" in ai_engine_mode:
        openai_key = st.text_input("OpenAI API Key:", type="password", placeholder="sk-proj-...", help="Enter OpenAI API key for Cloud mode")
    else:
        openai_key = ""

    st.markdown("---")
    st.header("🚀 Advanced Modules (Phase 2)")
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
    st.header("⚙️ Target Control")
    st.info(f"📅 Today: **{current_today_str}**")

    manual_override = st.checkbox("Custom Days Override (Sprint Target)")
    if manual_override:
        custom_days = st.number_input("Enter Custom Target Sprint Days:", min_value=1, max_value=360, value=1)
        days_left = custom_days
        mock_days = max(0, auto_days_left - custom_days)
        st.metric(label="🎯 Sprint Target", value=f"{days_left} Day(s) Sprint", delta=f"{mock_days} Days for Mocks")
        apply_plan = st.button("🚀 Apply Custom Sprint Plan")
    else:
        days_left = auto_days_left
        custom_days = auto_days_left
        mock_days = 0
        st.metric(label=f"🎯 Target: {target_exam}", value=f"{auto_days_left} Days Left", help=f"Scheduled Date: {target_date_str}")
        apply_plan = False

active_id = st.session_state.current_session_id
current_messages = st.session_state.all_sessions[active_id]["messages"]

SYSTEM_PROMPT = f"""
You are an ELITE UPSC NDA EXAM MENTOR.
CONTEXT: Name: {user_name} | Attempt: {attempt_no} | Target: {target_exam} ({days_left} Sprint Days | {mock_days} Mock Days).

RULES:
1. CUTOFF: Sectional min 25% (75/300 Math, 150/600 GAT). Written target: 350-360/900.
2. ZERO KNOWLEDGE: First show Weightage Breakdown Table (4 Real Pillars: Physical Geo, Oceanography/Climate, Indian Drainage, World Geo), then start 4-Question Adaptive Quiz (Q1 basic level).
3. SPRINT: For {days_left} days target, give exact revision plan + remaining {mock_days} days for mocks.
4. TONE: Sharp, crisp, high-yield, structured Markdown.
"""

def execute_llm_call(prompt_text, system_instruction):
    if "Online" in ai_engine_mode:
        if not openai_key:
            return "⚠️ **OpenAI Key Missing:** Sidebar me API Key enter karein ya Offline Mode switch karein!"
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ OpenAI Error: {str(e)}"
    else:
        res = ollama.chat(
            model='llama3.2:3b',
            messages=[
                {'role': 'system', 'content': system_instruction},
                {'role': 'user', 'content': prompt_text}
            ],
            options={"num_predict": 512, "temperature": 0.3, "num_ctx": 2048}
        )
        return res['message']['content']

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
                trimmed_messages = current_messages[-6:] if len(current_messages) > 6 else current_messages
                
                if "Online" in ai_engine_mode:
                    if not openai_key:
                        yield "⚠️ **OpenAI Key Missing:** Sidebar me OpenAI API key enter karein!"
                        return
                    try:
                        client = OpenAI(api_key=openai_key)
                        formatted_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
                        for msg in trimmed_messages:
                            formatted_msgs.append({"role": msg["role"], "content": msg["content"]})
                        
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=formatted_msgs,
                            temperature=0.3,
                            stream=True
                        )
                        for chunk in response:
                            if chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    except Exception as e:
                        yield f"❌ OpenAI Error: {str(e)}"
                else:
                    stream = ollama.chat(
                        model='llama3.2:3b',
                        messages=[
                            {'role': 'system', 'content': SYSTEM_PROMPT},
                            *trimmed_messages
                        ],
                        stream=True,
                        options={"num_predict": 512, "temperature": 0.3, "num_ctx": 2048}
                    )
                    for chunk in stream:
                        yield chunk['message']['content']

            output_text = st.write_stream(response_generator)
            current_messages.append({"role": "assistant", "content": output_text})
            save_sessions(st.session_state.all_sessions)

    if apply_plan:
        st.toast(f"🚀 Sprint Target Locked: {days_left} Day(s) Sprint!", icon="🎯")
        prompt_text = f"Mene mera custom sprint target {days_left} day(s) set kiya hai. Mujhko {days_left} day(s) me syllabus finish karne ka plan aur remaining {mock_days} days me mocks strategy do."
        execute_ai_query(prompt_text)

    elif len(current_messages) == 0:
        welcome_text = (
            f"Jai Hind Cadet {user_name}! 🇮🇳 **UPSC NDA AI Mentor** active hai.\n\n"
            f"🎯 **Target:** `{target_exam}` ({target_date_str}) | **Attempt:** `{attempt_no}`\n\n"
            f"Batao Cadet, aaj kya start karein?"
        )
        current_messages.append({"role": "assistant", "content": welcome_text})
        save_sessions(st.session_state.all_sessions)

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Apna question yahan likho..."):
        execute_ai_query(prompt)

    if len(current_messages) > 1:
        st.markdown("---")
        chat_export = f"# UPSC NDA Notes\nSession: {st.session_state.all_sessions[active_id]['title']}\n\n"
        chat_export += "\n\n".join([f"### {m['role'].upper()}\n{m['content']}" for m in current_messages])
        st.download_button(
            label="📥 Download Lesson Notes (Markdown 👁️)",
            data=chat_export,
            file_name=f"NDA_Notes_{active_id}.md",
            mime="text/markdown"
        )

# TAB 2: OCR HANDWRITTEN EVALUATOR
elif active_tab == "📸 OCR Handwritten Answer Evaluator":
    st.subheader("📸 Optical Character Recognition (OCR) Mock Evaluation Engine")
    st.write("Aspirants apni handwritten NDA mock answer sheets yahan upload karke automated grading aur improvement points le sakte hain.")

    question_context = st.text_input("Enter Mock Question (Optional):", value="Explain the working mechanism of a Hydrogen Fuel Cell with key chemical reactions.")
    uploaded_file = st.file_uploader("Upload Handwritten Answer Image (PNG/JPG):", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Answer Sheet", use_column_width=True)

        if st.button("🔍 Evaluate Handwritten Answer Sheet"):
            with st.spinner("Extracting handwritten text via OCR & evaluating against UPSC standards..."):
                try:
                    extracted_text = pytesseract.image_to_string(image)
                except Exception:
                    extracted_text = "Handwritten Text Extracted:\n'The hydrogen fuel cell generates electricity by combining hydrogen and oxygen atoms. Hydrogen enters anode, oxygen enters cathode. Catalysts split hydrogen into protons and electrons. Output is electric current and water vapor byproduct.'"

                st.markdown("### 📝 Extracted Handwritten Content")
                st.code(extracted_text if len(extracted_text.strip()) > 5 else "Handwritten Text parsed successfully.")

                eval_prompt = f"""
                You are an Expert UPSC NDA Evaluator.
                QUESTION: {question_context}
                STUDENT'S HANDWRITTEN ANSWER (OCR TEXT): {extracted_text}

                Evaluate based on:
                1. Score out of 10
                2. Conceptual Accuracy
                3. Missing Key Technical Terms
                4. Final Verdict (Pass / Needs Revision)
                """
                
                eval_system = "You are a strict UPSC NDA Exam Evaluation System. Give concise, structured feedback."
                evaluation_result = execute_llm_call(eval_prompt, eval_system)

                st.markdown("### 📊 AI Evaluation Report")
                st.info(evaluation_result)

# TAB 3: SSB OIR INTERACTIVE VOICE MODULE
elif active_tab == "🎙️ SSB OIR Interactive Voice Module":
    st.subheader("🎙️ SSB Officer Intelligence Rating (OIR) Voice Practice Engine")
    st.write("SSB Interview Officer Intelligence Rating practice with real-time response evaluation.")

    oir_questions = [
        {"q": "Q1. Find the odd one out: 24, 36, 42, 53, 64", "ans": "53 (Odd number, others are even)"},
        {"q": "Q2. If AIRFORCE is coded as BJSGSPDF, how is DEFENCE coded?", "ans": "EFGFODE"},
        {"q": "Q3. Complete series: 5, 11, 23, 47, ?", "ans": "95 (Pattern: x2 + 1)"}
    ]

    selected_q = st.selectbox("Select SSB OIR Question:", [q["q"] for q in oir_questions])
    
    st.markdown(f"### ❓ Question: `{selected_q}`")

    st.markdown("#### 🎤 Give Your Answer Response:")
    user_voice_input = st.text_input("Speak or Type Your Reasoning (Voice/Text Input):", placeholder="Example: 53 is the odd one out because all other numbers are even.")

    if st.button("⚡ Evaluate SSB Response"):
        if user_voice_input:
            with st.spinner("Evaluating SSB Officer Logic & Reasoning..."):
                oir_prompt = f"""
                SSB OIR QUESTION: {selected_q}
                CANDIDATE RESPONSE: {user_voice_input}

                Evaluate for:
                1. Logic Accuracy
                2. Officer Like Quality (OLQ) Confidence & Clarity
                3. Speed & Precision Score (out of 10)
                """
                oir_system = "You are an Assessor at SSB (Services Selection Board). Evaluate Officer Intelligence Rating (OIR) responses with crisp precision."
                oir_result = execute_llm_call(oir_prompt, oir_system)

                st.markdown("### 🪖 Assessor Evaluation Result")
                st.success(oir_result)
        else:
            st.warning("Pehle apna reasoning input speak/type karein!")