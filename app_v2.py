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
        
        # Interaction mode selector
        st.subheader("📱 Interaction Mode")
        interaction_mode = st.radio(
            "Choose interaction mode:",
            ["text", "video", "voice"],
            format_func=lambda x: {
                "text": "💬 Text Chat",
                "video": "🎥 Video Avatar",
                "voice": "🎙️ Voice Agent"
            }[x],
            key="mode_selector"
        )
        st.session_state.interaction_mode = interaction_mode
        
        # End session
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
        if st.session_state.interaction_mode == "text":
            st.subheader("💬 Text Chat with Specialized Agents")
            
            # Display conversation history
            if st.session_state.conversation_history:
                st.markdown("### Conversation")
                for msg in st.session_state.conversation_history:
                    if msg["role"] == "user":
                        st.chat_message("user").write(msg["content"])
                    else:
                        with st.chat_message("assistant"):
                            st.write(msg["content"])
                            if "agent" in msg:
                                agent_name = msg.get("agent", "unknown")
                                st.caption(f"Agent: {agent_name}")
            
            # User input
            user_input = st.chat_input("Ask me anything...")
            
            if user_input:
                # Add user message to history
                st.session_state.conversation_history.append({
                    "role": "user",
                    "content": user_input
                })
                
                # Display user message
                st.chat_message("user").write(user_input)
                
                # Get response from backend
                try:
                    import httpx
                    
                    with st.chat_message("assistant"):
                        st.write("🤔 Processing...")
                        
                        payload = {
                            "user_id": st.session_state.user_id,
                            "session_id": st.session_state.session_id,
                            "message": user_input,
                            "mode": "text",
                            "conversation_history": [
                                {"role": msg["role"], "content": msg["content"]}
                                for msg in st.session_state.conversation_history[:-1]
                            ]
                        }
                        
                        # Stream from /multi-agent/stream endpoint
                        stream_state = {"text": "", "agent": "unknown"}
                        
                        async def stream_response():
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
                        
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(stream_response())
                        
                        response_text = stream_state["text"]
                        agent_used = stream_state["agent"]
                        
                        st.write(response_text)
                        st.caption(f"🤖 Agent: {agent_used}")
                        
                        # Add to history
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": response_text,
                            "agent": agent_used
                        })
                        
                        st.session_state.last_agent = agent_used
                        st.rerun()
                        
                except Exception as e:
                    import traceback
                    st.error(f"Error: {e}")
                    st.code(traceback.format_exc())
        
        elif st.session_state.interaction_mode == "video":
            st.subheader("🎥 Video Avatar with AI")
            st.info("Video avatar integration requires Anam AI setup. Configure in settings.")
            
            # Placeholder for video component
            st.write("Video avatar coming soon...")
        
        elif st.session_state.interaction_mode == "voice":
            st.subheader("🎙️ Voice Agent")
            st.info("Ultra-low latency voice requires FastRTC setup. Configure in settings.")
            
            # Placeholder for voice component
            st.write("Voice agent coming soon...")
    
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
    - **🎥 Video Avatar:** Interact with Anam AI avatar
    - **🎙️ Voice Agent:** Ultra-low latency voice with FastRTC
    
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
    - **🔗 Knowledge Graph (Removed):** Zep integration removed
    - **⚡ Parallel Processing:** Fast, concurrent agent execution
    
    ### Tech Stack
    - **LangGraph:** Multi-agent orchestration
    - **Cerebras GPT-OSS-120B:** Main reasoning model
    - **Mem0:** Persistent memory
    - **SerpApi:** Job, flight, and recipe search
    - **ChromaDB:** Vector embeddings
    - **Anam AI:** Realistic avatar with voice
    """)
