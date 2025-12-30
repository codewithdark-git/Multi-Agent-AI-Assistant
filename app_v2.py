"""
Multi-Modal AI Assistant with Supervisor Agent Orchestration.

Supports:
- 💬 Text Chat
- 🎥 Video Agent with AI Avatar (Anam AI)
- 🎙️ Ultra-low latency Voice (FastRTC)
"""

import streamlit as st
import streamlit.components.v1 as components
import asyncio
import json
from typing import Optional

from services.anam_service import anam_service
from services.tools_service import mem0_service
from services.voice_service import voice_service
from services.llm_service import llm_service
from config.settings import settings

# ========================
# PAGE CONFIG
# ========================

st.set_page_config(
    page_title="Multi-Agent AI Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🤖 Multi-Agent AI Assistant")
st.caption("Supervisor-Orchestrated Specialized Agents with Multi-Modal Interactions")

# ========================
# STYLING
# ========================

st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton button {
        width: 100%;
    }
    .agent-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .agent-research { background: #e8f4f8; color: #0288d1; }
    .agent-finance { background: #f3e5f5; color: #7b1fa2; }
    .agent-travel { background: #e8f5e9; color: #388e3c; }
    .agent-shopping { background: #fff3e0; color: #f57c00; }
    .agent-jobs { background: #fce4ec; color: #c2185b; }
    .agent-recipes { background: #f1f8e9; color: #558b2f; }
</style>
""", unsafe_allow_html=True)

# ========================
# SESSION INITIALIZATION
# ========================

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "anam_session_token" not in st.session_state:
    st.session_state.anam_session_token = None
if "interaction_mode" not in st.session_state:
    st.session_state.interaction_mode = "text"
if "user_memories" not in st.session_state:
    st.session_state.user_memories = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "last_agent" not in st.session_state:
    st.session_state.last_agent = None
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# ========================
# SIDEBAR: SESSION MANAGEMENT
# ========================

with st.sidebar:
    st.header("🔧 Session Management")
    
    # User info
    user_name = st.text_input("Your Name", value="Demo User", key="user_name_input")
    
    # Initialize session
    if st.button("Initialize New Session", type="primary"):
        user_id = user_name.lower().replace(" ", "-")
        session_id = f"session-{user_id}"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create Zep user and thread
            
            # Initialize Mem0
            if settings.mem0_enabled:
                loop.run_until_complete(
                    mem0_service.add_memory(
                        user_id=user_id,
                        message=f"Session started for {user_name}",
                        metadata={"session_id": session_id}
                    )
                )
            
            st.session_state.user_id = user_id
            st.session_state.session_id = session_id
            st.session_state.anam_session_token = None
            st.session_state.conversation_history = []
            st.session_state.user_memories = []
            
            st.success(f"✅ Session initialized for {user_name}!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    # Display session info
    if st.session_state.session_id:
        st.divider()
        st.info(f"""
        **👤 Active User:** {st.session_state.user_id}
        
        **📍 Session:** {st.session_state.session_id}
        
        **🧠 Memory:** {'Enabled' if settings.mem0_enabled else 'Disabled'}
        """)
        
        if st.button("End Session", type="secondary"):
            st.session_state.session_id = None
            st.session_state.user_id = None
            st.session_state.anam_session_token = None
            st.success("Session ended")
            st.rerun()

# ========================
# MAIN CONTENT
# ========================

if st.session_state.session_id:
    # Tabs for different views
    tab_chat, tab_agents, tab_memory = st.tabs([
        "💬 Chat",
        "🤖 Agent Info",
        "🧠 Memory"
    ])
    
    # -------- TAB 1: CHAT --------
    with tab_chat:
        st.subheader("💬 Multi-Modal Agent Chat")
        
        # Display conversation history
        if st.session_state.conversation_history:
            st.markdown("### Conversation")
            for msg in st.session_state.conversation_history:
                if msg["role"] == "user":
                    st.chat_message("user").write(msg["content"])
                else:
                    with st.chat_message("assistant"):
                        if "summary" in msg:
                            tab_sum, tab_det = st.tabs(["📝 Summary", "📄 Full Detail"])
                            with tab_sum:
                                st.write(msg["summary"])
                            with tab_det:
                                st.write(msg["content"])
                        else:
                            st.write(msg["content"])
                        
                        if "agent" in msg:
                            agent_name = msg.get("agent", "unknown")
                            st.caption(f"Agent: {agent_name}")
        

        # --- UNIFIED INPUT AREA ---
        # Place voice input just above the bottom text input
        st.divider()
        col_voice, col_spacer = st.columns([0.2, 0.8])
        with col_voice:
            voice_audio = st.audio_input("Record Voice", key="unified_voice_input")
        
        # Text Input (Fixed at bottom)
        text_input_val = st.chat_input("Ask me anything...")

        # --- INPUT PROCESSING ---
        user_input = None
        is_voice = False

        # Check Voice
        if voice_audio:
             # Check hash to prevent re-processing same audio on rerun
            audio_id = hash(voice_audio.getvalue())
            if audio_id != st.session_state.last_processed_audio:
                with st.spinner("Transcribing Voice..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    transcription = loop.run_until_complete(
                        voice_service.transcribe_audio(voice_audio.getvalue())
                    )
                
                if transcription:
                    user_input = transcription
                    is_voice = True
                    st.session_state.last_processed_audio = audio_id
        
        # Check Text (Override voice if both present? Usually handle one)
        if text_input_val:
            user_input = text_input_val
            is_voice = False 

        # --- RESPONSE GENERATION ---
        if user_input:

            # Add user message to history
            st.session_state.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Re-render to show user message immediately (optional, or just rely on loop next rerun)
            # st.rerun() # Typically better to flow through, but Streamlit reruns on input.
            # We are already in the rerun triggered by input.
            # So just display it now visually or let the history loop handle it (it already ran above).
            # We need to render it locally if history loop ran *before* we appended? Yes.
            st.chat_message("user").write(user_input)
            
            # Get response from backend
            try:
                import httpx

                # Show processing message
                processing_placeholder = st.empty()
                processing_placeholder.write("🤔 Processing...")

                payload = {
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id,
                    "message": user_input,
                    "mode": "voice" if is_voice else "text",
                    "conversation_history": [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in st.session_state.conversation_history[:-1]
                    ]
                }

                # Stream from /multi-agent/stream endpoint
                stream_state = {"text": "", "agent": "unknown"}

                async def stream_response():
                    try:
                        async with httpx.AsyncClient(timeout=180.0) as client:
                            async with client.stream(
                                "POST",
                                "http://localhost:8000/multi-agent/stream",
                                json=payload
                            ) as response:
                                async for line in response.aiter_lines():
                                    if line.startswith("data: "):
                                        data = json.loads(line[6:])
                                        if "content" in data:
                                            stream_state["text"] += data.get("content", "")
                                            stream_state["agent"] = data.get("agent", stream_state["agent"])
                    except Exception as stream_error:
                        # Set a fallback response for testing
                        stream_state["text"] = f"Backend connection failed: {stream_error}. This is a test response to verify the UI works."
                        stream_state["agent"] = "test_agent"

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(stream_response())

                response_text = stream_state["text"]
                agent_used = stream_state["agent"]

                # Clear processing message and show simple response in chat
                processing_placeholder.empty()
                with st.chat_message("assistant"):
                    st.write(f"Response from {agent_used} agent:")
                    # Show a truncated preview
                    preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
                    st.write(preview)
                    if len(response_text) > 200:
                        st.info("📋 Full response and audio available in tabs below")
                    
                    # Generate Summary for TTS and display
                    summary_text = ""
                    if response_text and response_text.strip():
                        with st.spinner("📝 Generating summary..."):
                            try:
                                summary_text = loop.run_until_complete(
                                    llm_service.summarize_text(response_text)
                                )
                                if not summary_text:
                                    summary_text = response_text[:300] + "..."
                            except Exception as sum_err:
                                print(f"Summarization error: {sum_err}")
                                summary_text = response_text[:300] + "..."
                    else:
                        summary_text = "No response received."

                    # TTS Logic - Generate audio for the summary BEFORE creating tabs
                    # Always try to generate audio, even if it might fail
                    audio_bytes = None
                    tts_error_message = None
                    tts_success = False

                    # Check TTS configuration
                    openai_configured = bool(settings.openai_api_key)
                    groq_configured = bool(settings.groq_api)

                    # Generate audio for summary
                    try:
                        audio_bytes = loop.run_until_complete(
                            voice_service.text_to_speech(summary_text)
                        )
                        tts_success = audio_bytes is not None and len(audio_bytes) >= 1000

                    except Exception as tts_err:
                        tts_success = False
                        audio_bytes = None

                    # Display Tabs with Summary, Full Detail, and Audio
                    st.divider()
                    st.subheader("📋 Response Details & Audio")
                    tab_sum, tab_det, tab_audio = st.tabs(["📝 Summary", "📄 Full Detail", "🔊 Audio"])

                    with tab_sum:
                        st.write(summary_text)

                    with tab_det:
                        st.write(response_text)

                    with tab_audio:
                        if audio_bytes and tts_success:
                            st.audio(audio_bytes, format="audio/mp3", autoplay=False)
                        else:
                            st.info("Audio not available")
                    
                    st.caption(f"🤖 Agent: {agent_used}")

                    # Add to history
                    st.session_state.conversation_history.append({
                        "role": "assistant",
                        "content": response_text,
                        "agent": agent_used,
                        "summary": summary_text
                    })
                    
                    st.session_state.last_agent = agent_used

                    # Don't rerun immediately - let the tabs render first
                    # st.rerun()  # Commented out to allow tabs to display
                    
            except Exception as e:
                st.error(f"Error: {e}")
                st.caption("Make sure the backend server is running: `uvicorn backend:app --port 8000 --reload`")
        
        # Legacy modes cleanup
        if st.session_state.interaction_mode not in ["text", "voice"]:
             st.session_state.interaction_mode = "text"
             st.rerun()
    
    # -------- TAB 2: AGENT INFO --------
    with tab_agents:
        st.subheader("🤖 Available Specialized Agents")
        
        agents_info = {
            "research": {
                "icon": "🔍",
                "description": "Web research, articles, and information gathering",
                "tools": ["News search", "ChromaDB RAG", "Document retrieval"]
            },
            "finance": {
                "icon": "💰",
                "description": "Financial information, stocks, and investment advice",
                "tools": ["Financial news", "Market data", "Investment guidance"]
            },
            "travel": {
                "icon": "✈️",
                "description": "Flights, hotels, and trip planning",
                "tools": ["Flight search", "Hotel booking", "Travel guides"]
            },
            "shopping": {
                "icon": "🛍️",
                "description": "Product recommendations and shopping assistance",
                "tools": ["Product search", "Price comparison", "Recommendations"]
            },
            "jobs": {
                "icon": "💼",
                "description": "Job search and career advice",
                "tools": ["Google Jobs search", "Resume tips", "Career guidance"]
            },
            "recipes": {
                "icon": "👨🍳",
                "description": "Recipe discovery with ratings and ingredients",
                "tools": ["Recipe search", "Ingredient lookup", "Cooking tips"]
            }
        }
        
        cols = st.columns(2)
        for idx, (agent_name, info) in enumerate(agents_info.items()):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### {info['icon']} {agent_name.title()}")
                    st.write(info['description'])
                    st.caption("Available tools:")
                    for tool in info['tools']:
                        st.caption(f"• {tool}")
        
        # Show last used agent
        if st.session_state.last_agent:
            st.divider()
            st.info(f"Last agent used: **{st.session_state.last_agent}**")
    
    # -------- TAB 3: MEMORY --------
    with tab_memory:
        st.subheader("🧠 User Memories")
        
        if settings.mem0_enabled:
            # Retrieve user memories
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                memories = loop.run_until_complete(
                    mem0_service.retrieve_memories(
                        user_id=st.session_state.user_id,
                        limit=10
                    )
                )
                
                if memories:
                    st.write(f"📚 Found {len(memories)} memories:")
                    for i, memory in enumerate(memories, 1):
                        with st.expander(f"Memory {i}"):
                            st.write(memory.get("message", ""))
                            if "metadata" in memory:
                                st.caption(f"Metadata: {memory['metadata']}")
                else:
                    st.info("No memories stored yet. Start chatting to create memories!")
            
            except Exception as e:
                st.warning(f"Could not retrieve memories: {e}")
        else:
            st.info("💾 Mem0 integration not enabled. Enable in settings to use long-term memory.")

else:
    st.info("👈 Please initialize a session from the sidebar to start.")


    # Show feature overview
    st.divider()
    st.markdown("""
    ## 🚀 Features
    
    ### Multi-Modal Interactions
    - **💬 Text Chat:** Talk to specialized agents
    - **🎙️ Voice Agent:** Ultra-low latency voice with Groq & OpenAI
    
    ### Supervisor Agent Architecture
    - Intelligent routing to specialized domain agents
    - Automatic intent detection
    - Context-aware responses
    
    ### Specialized Agents
    - 🔍 **Research:** Web research and information gathering
    - 💰 **Finance:** Financial advice and market data
    - ✈️ **Travel:** Flight and hotel booking assistance
    - 🛍️ **Shopping:** Product recommendations
    - 💼 **Jobs:** Job search and career guidance
    - 👨🍳 **Recipes:** Recipe discovery with ratings
    
    ### Advanced Features
    - **🧠 Long-term Memory:** Mem0 integration never forgets
    - **📚 RAG:** ChromaDB + Groq for multi-PDF context
    - **⚡ Parallel Processing:** Fast, concurrent agent execution
    
    ### Tech Stack
    - **LangGraph:** Multi-agent orchestration
    - **Cerebras GPT-OSS-120B:** Main reasoning model
    - **Mem0:** Persistent memory
    - **SerpApi:** Job, flight, and recipe search
    - **ChromaDB:** Vector embeddings
    """)
