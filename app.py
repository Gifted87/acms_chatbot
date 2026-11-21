import streamlit as st
import google.generativeai as genai
from acms_client import ACMSClient
import json
import hashlib

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="ACMS Legal Analyst", layout="wide", page_icon="⚖️")

# Global CSS for a polished, production-grade look
st.markdown("""
<style>
/* Global layout adjustments */
body, div, span, p, h1, h2, h3, h4, h5, h6, li, a {
    color: #eee !important;
}
body {background-color: #1a1a1a !important;}
.block-container {padding-top: 5rem; padding-bottom: 6rem; max-width: 1200px; margin: auto;}
.header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 60px;
    background-color: #222;
    border-bottom: 1px solid #333;
    display: flex;
    align-items: center;
    padding: 0 2rem;
    z-index: 1000;
    box-shadow: 0 2px 4px rgba(0,0,0,0.5);
}
.header h1 {margin: 0; font-size: 1.4rem; font-weight: 600; color: #fff;}
.header .logo {font-size: 1.6rem; margin-right: 0.5rem;}
.footer {
    text-align: center;
    color: #aaa;
    font-size: 0.9rem;
    padding: 1rem 0;
    border-top: 1px solid #333;
    margin-top: 2rem;
}

/* Sidebar tweaks */
.stSidebar {background-color: #212121; color: #eee;}

/* Evidence panel style */
.evidence-panel {background: #2a2a2a; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.6);}

/* Chat styling */
.chat-container {min-height: 200px; max-height: 70vh; overflow-y: auto; padding: 1rem; background: #252525; color: #eee !important; border-radius: 8px;}
.chat-container.empty {background: transparent; color: #ccc !important; min-height: auto; padding: 0.5rem;}
.stChatMessage {background-color: transparent !important; margin-bottom: 1rem; display: flex;}
.stChatMessage .message-content {padding: 0.75rem 1rem; border-radius: 12px; display: inline-block; max-width: 80%; font-size: 0.95rem; line-height: 1.4; color: #eee !important;}
.stChatMessage.user .message-content {background: #004b74 !important; color: #e0f7ff !important; align-self: flex-end; border: 1px solid #0082b3 !important;}
.stChatMessage.assistant .message-content {background: #333 !important; color: #eee !important; align-self: flex-start; border: 1px solid #444 !important;}

/* Buttons & inputs */
.stButton>button {border-radius: 8px;}

/* Citation badge */
.citation-badge {
    background-color: #f0f2f6;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 0.85em;
    font-weight: bold;
    color: #4b5563;
    margin-right: 5px;
}

/* Expanders reuse earlier styles */
.stExpander {
    border: 1px solid #444;
    border-radius: 5px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    background-color: #2a2a2a !important;
    color: #eee !important;
}
.stExpander details summary {
    font-family: 'Source Sans Pro', sans-serif;
    font-weight: 600;
    color: #eee;
}
/* when expander is open, its content also needs dark background */
.stExpander > div, .stExpander .stMarkdown {
    background-color: #2a2a2a !important;
    color: #eee !important;
}
</style>
""", unsafe_allow_html=True)

# --- 2. STATE MANAGEMENT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_evidence" not in st.session_state:
    # This stores the docs retrieved for the LAST question asked
    st.session_state.current_evidence = [] 
if "current_unknowns" not in st.session_state:
    # Holds any "unknown unknowns" returned by ACMS for the latest query
    st.session_state.current_unknowns = []

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚖️ ACMS Control")
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    
    # Initialize Client
    try:
        client = ACMSClient()
        if client.health_check():
            st.success("ACMS Neural Memory: Online")
            st.caption("Ready to retrieve atomic contract nodes from neural memory.")
        else:
            st.error("ACMS Neural Memory: Offline")
    except Exception as e:
        st.error(f"Client Error: {e}")

    st.divider()
    if st.button("Clear Memory", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_evidence = []
        st.rerun()

    st.markdown("---")
    with st.expander("❓ Usage Tips"):
        st.write("• Paste your Gemini API key at the top of the sidebar.")
        st.write("• Ask questions about contract clauses, governing law, liability, dates, etc.")
        st.write("• The evidence panel will surface the sources retrieved from ACMS.")

# --- 4. UTILITY FUNCTIONS ---

def format_node_for_llm(nodes):
    """
    Transforms raw ACMS nodes into a structured string with IDs for the LLM to cite.
    Returns: (formatted_string, list_of_structured_sources)
    """
    llm_context = ""
    structured_sources = []
    
    for idx, node in enumerate(nodes, 1):
        # Extract meaningful content from the ACMS payload
        payloads = node.get("data", [])
        
        # Try to find a title or meaningful identifier in the data
        source_title = f"Document Node #{node.get('id', idx)}"
        content_block = ""
        
        for p in payloads:
            if p.get("type") == "object":
                data_dict = p.get("data", {})
                # Attempt to grab a title if it exists in the raw json
                if 'title' in data_dict:
                    source_title = data_dict['title']
                elif 'file_name' in data_dict:
                    source_title = data_dict['file_name']
                    
                content_block += json.dumps(data_dict, default=str)
            elif p.get("type") == "text":
                content_block += p.get("content", "")

        # Create the text prompt for the LLM
        llm_context += f"--- SOURCE [{idx}] ({source_title}) ---\n{content_block}\n\n"
        
        # Save structured data for the UI
        structured_sources.append({
            "id": idx,
            "title": source_title,
            "content": content_block,
            "raw_node": node
        })
        
    return llm_context, structured_sources

# --- 5. UI HELPERS ---
def render_header():
    st.markdown("""
    <div class="header">
        <span class="logo">⚖️</span>
        <h1>ACMS Legal Memory Analyst</h1>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    st.markdown("""
    <div class="footer">
        © 2026 LegalTech Corp. All rights reserved. 
        <br/>Powered by ACMS & Gemini.
    </div>
    """, unsafe_allow_html=True)

# --- 6. MAIN LAYOUT ---

# fixed header at top
render_header()

# spacer title to push content below header
st.title("")

# Layout: 60% Chat, 40% Evidence Panel
col_chat, col_evidence = st.columns([3, 2], gap="large")

# --- RIGHT COLUMN: EVIDENCE PANEL ---
with col_evidence:
    st.subheader("🗂️ Retrieved Evidence")
    with st.container():
        if not st.session_state.current_evidence and not st.session_state.current_unknowns:
            st.info("Ask a question to retrieve contract clauses from ACMS.")
        else:
            if st.session_state.current_evidence:
                st.markdown(f"**{len(st.session_state.current_evidence)} Sources Found**")
                for source in st.session_state.current_evidence:
                    # Create a card for each source
                    with st.expander(f"📄 {source['id']}. {source['title']}", expanded=True):
                        st.caption("Raw Content Preview:")
                        st.code(source['content'][:800] + ("..." if len(source['content'])>800 else ""), language="json")
                        if st.checkbox(f"Show full JSON node", key=f"raw_{source['id']}"):
                            st.json(source['raw_node'])
            if st.session_state.current_unknowns:
                st.markdown("---")
                st.subheader("🤔 Additional Signals (unknown unknowns)")
                for idx, unk in enumerate(st.session_state.current_unknowns, 1):
                    with st.expander(f"🔍 Signal {idx}", expanded=False):
                        st.write(unk)

# --- LEFT COLUMN: CHAT INTERFACE ---
with col_chat:
    # message history container (shown only when messages exist)
    if st.session_state.messages:
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            st.markdown(f"<div class='stChatMessage {role}'><div class='message-content'>{content}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # empty placeholder to avoid large grey box
        st.markdown("<div class='chat-container empty'>\n<p style='color:#ccc;text-align:center;margin-top:2rem;'>Start the conversation by asking a question below.</p>\n</div>", unsafe_allow_html=True)

    # Input Handling
    if prompt := st.chat_input("Ask about governing law, liability, or dates..."):
        if not api_key:
            st.error("Please enter your Gemini API Key in the sidebar.")
            st.stop()

        # 1. User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Sending query…"):
            with st.chat_message("user"):
                st.markdown(prompt)

        # 2. Retrieval & Processing
        with st.spinner("Analyzing ACMS neural memory…"):
            raw_results, unknowns = client.query_memory(prompt)
            context_str, structured_sources = format_node_for_llm(raw_results)
            st.session_state.current_evidence = structured_sources
            st.session_state.current_unknowns = unknowns

        # 3. LLM Generation
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')

        system_instruction = f"""
        Your goal is to answer the user's question based ONLY on the provided Context Sources
        and any additional "unknown unknown" signals returned by the memory system.

        CITATION RULES:
        1. You must support your claims by citing the specific Source ID provided in the context.
        2. Format citations like this: **[Source 1]**, **[Source 3]**.
        3. Do not invent facts not present in the sources or in the unknowns.

        You are an Insight Engine. You possess a set of "Memory Fragments" retrieved in response to a user's request.
        The Logic:
        The Memory Fragments provided to you contain both Direct Answers (what the user asked for) and Associative Context (hidden risks, prerequisites, or conflicting truths that the system retrieved automatically).
        Your Instructions:
        Satisfy the Ask: First, provide a clear, direct answer to the user's question using the most relevant Memory Fragments.
        Find the "Unknown Unknowns": Scan the remaining Memory Fragments that you did not use for the direct answer. These fragments were retrieved because they are causally or structurally linked to the topic. You must interpret why they are there.
        Look for fragments that imply prerequisites (e.g., "You can't do X without Y").
        Look for fragments that suggest contradictions or conflicts (e.g., "Method A is deprecated" or "Method B is safer").
        Look for fragments that warn of consequences (e.g., "Doing X causes high memory usage").
        The "Shadow" Section: After your main answer, add a section called "Critical Context & Hidden Needs."
        In this section, tell the user what they didn't ask but need to know based on those associative fragments.
        Use phrases like: "The system also retrieved context suggesting..." or "Be aware that this topic is strongly linked to..."

        CONTEXT SOURCES:
        {context_str}

        """
        if unknowns:
            system_instruction += f"\nADDITIONAL SIGNALS (unknown unknowns):\n{json.dumps(unknowns, indent=2)}\n\n"
        system_instruction += f"USER QUESTION: {prompt}\n"

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                response_stream = model.generate_content(system_instruction, stream=True)
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.rerun()
            except Exception as e:
                st.error(f"Generation Error: {e}")

render_footer()