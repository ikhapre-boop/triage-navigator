import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from agent.safety import assess_safety, is_veteran_context, RiskLevel
from agent.triage_agent import build_agent, format_history

st.set_page_config(
    page_title="Community Triage Navigator",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }
.stApp { background: #faf8f5; }

.disclaimer-box {
    background: #fff8e7;
    border-left: 4px solid #f0a500;
    border-radius: 4px;
    padding: 0.8rem 1.2rem;
    margin: 1rem 0;
    font-size: 0.88rem;
    color: #555;
}
</style>
""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    with st.spinner("Loading navigator..."):
        st.session_state.agent = build_agent()

# Sidebar
with st.sidebar:
    st.markdown("### 🆘 Crisis Lines — Always Free")
    st.markdown("""
| Situation | Contact |
|-----------|---------|
| **Suicide / Mental Health** | Call or text **988** |
| **Emergency** | Call **911** |
| **Domestic Violence** | **1-800-799-7233** |
| **Any Resource** | Call **211** |
| **Crisis Text** | Text HOME to **741741** |
    """)
    st.divider()
    st.markdown("### About")
    st.markdown(
        "This tool helps you find free community resources. "
        "It is **not** a substitute for licensed professional advice. "
        "In an emergency, call 911."
    )
    st.divider()
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

# Header
st.markdown("""
<div style="text-align:center; padding: 2rem 0 1rem 0;">
    <h1 style="font-family: DM Serif Display; font-size: 2.2rem; color: #1a1a2e;">🧭 Community Triage Navigator</h1>
    <p style="color: #666;">Tell me what you're dealing with — I'll help you find free local support.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer-box">
    ⚠️ <strong>This is a free resource-finding tool, not a licensed service.</strong>
    For emergencies, call 911.
</div>
""", unsafe_allow_html=True)

# Chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                st.button("👍", key=f"up_{i}")
            with col2:
                st.button("👎", key=f"dn_{i}")

# Input
user_input = st.chat_input("Tell me what's going on — I'm here to help find resources...")

if user_input and user_input.strip():
    user_msg = user_input.strip()
    st.session_state.messages.append({"role": "user", "content": user_msg})

    with st.chat_message("user"):
        st.markdown(user_msg)

    assessment = assess_safety(user_msg)
    vet_context = is_veteran_context(user_msg)

    with st.chat_message("assistant"):
        with st.spinner("Finding resources for you..."):
            response_parts = []

            if assessment.risk_level == RiskLevel.CRITICAL:
                response = assessment.escalation_message
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.stop()

            if assessment.risk_level == RiskLevel.HIGH and assessment.escalation_message:
                response_parts.append(assessment.escalation_message)

            if vet_context:
                response_parts.append(
                    "🎖️ I noticed you may be a veteran or service member. "
                    "The **Veterans Crisis Line** (call 988 → press 1) may also be available to you.\n"
                )

            try:
                history = format_history(st.session_state.messages[:-1])
                result = st.session_state.agent.invoke({
                    "input": user_msg,
                    "chat_history": history,
                })
                agent_response = result.get("output", "I wasn't able to find results. Please try calling 211.")
                response_parts.append(agent_response)
            except Exception as e:
                response_parts.append(
                    "I'm having trouble searching right now. "
                    "Please try **calling 211** — they can connect you with local resources for almost any need."
                )

            final_response = "\n\n".join(response_parts)
            st.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})

# Empty state
if not st.session_state.messages:
    st.markdown("---")
    st.markdown("**Not sure where to start? Try clicking one of these:**")
    cols = st.columns(3)
    examples = [
        ("🍎 Food", "I need help finding food for my family"),
        ("🏠 Housing", "I'm worried about being evicted"),
        ("🧠 Mental Health", "I'm struggling with anxiety and can't afford therapy"),
        ("⚡ Utilities", "My electricity is about to be shut off"),
        ("⚖️ Legal Help", "I need free legal advice"),
        ("💊 Healthcare", "I need healthcare but don't have insurance"),
    ]
    for i, (label, prompt) in enumerate(examples):
        with cols[i % 3]:
            if st.button(label, key=f"example_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.rerun()