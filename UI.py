import streamlit as st
import asyncio
import nest_asyncio
import os
import sys

# MUST be the very first thing for Windows asyncio support with subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv

load_dotenv()

from Blog_Pipeline import (
    fetch_daily_news,
    node_research,
    node_write,
    node_publish,
    BlogState
)

nest_asyncio.apply()
st.set_page_config(layout="wide", page_title="AI News Writer")
st.title("📰 Daily AI News Blog Writer")

# Sidebar for Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    # API Key is now loaded from .env
    with st.expander("🔑 API Key Info"):
        st.info("The app supports multiple API keys for high limits via .env:\n- GOOGLE_API_KEY_FETCH\n- GOOGLE_API_KEY_RESEARCH\n- GOOGLE_API_KEY_WRITE\n- GOOGLE_API_KEY_PUBLISH")
    
    topic = st.selectbox("Select Topic", ["Artificial Intelligence", "Stock Market", "Technology", "Crypto", "Space Exploration"])

steps = ["fetch_news", "select_headline", "research", "write", "publish"]

# === Session State Setup ===
if "status" not in st.session_state:
    st.session_state.status = {step: "⏳ Pending" for step in steps}
if "pipeline_data" not in st.session_state:
    st.session_state.pipeline_data = {
        "topic_category": topic,
        "headlines": [],
        "selected_headline": None,
        "research_data": "",
        "blog_post": "",
        "publish_status": ""
    }

# === UI Styling ===
st.markdown("""
<style>
.step-card {
    background-color: #f0f2f6;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 20px;
    border: 1px solid #e0e0e0;
}
.success { color: #0f5132; background-color: #d1e7dd; padding: 5px; border-radius: 5px; }
.running { color: #664d03; background-color: #fff3cd; padding: 5px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# === Main Pipeline Logic ===

async def run_fetch():
    with st.status("🌍 Fetching News...", expanded=True) as status:
        st.write("Initializing search...")
        
        def log_callback(msg):
            st.write(msg)
            
        news = await fetch_daily_news(topic, status_callback=log_callback)
        st.session_state.pipeline_data["headlines"] = news
        status.update(label="✅ News Fetched", state="complete", expanded=False)
    
    st.session_state.status["fetch_news"] = "✅ Done"
    st.session_state.status["select_headline"] = "🟡 Waiting for User"
    st.rerun()

async def run_research():
    with st.status("🕵️ Researching Topic...", expanded=True) as status:
        def log_callback(msg):
            st.write(msg)
            
        # Create a pseudo-state for the node function
        current_state = {
            "selected_headline": st.session_state.pipeline_data["selected_headline"],
            "topic_category": topic,
            "headlines": [],
            "research_data": None,
            "blog_post": None,
            "status": None,
            "status_callback": log_callback
        }
        
        result_state = await node_research(current_state)
        st.session_state.pipeline_data["research_data"] = result_state["research_data"]
        status.update(label="✅ Research Complete", state="complete", expanded=False)

    st.session_state.status["research"] = "✅ Done"
    st.session_state.status["write"] = "⏳ Pending" # Ready to write
    st.rerun()

async def run_write():
    with st.status("✍️ Writing Article...", expanded=True) as status:
        def log_callback(msg):
            st.write(msg)

        current_state = {
            "selected_headline": st.session_state.pipeline_data["selected_headline"],
            "research_data": st.session_state.pipeline_data["research_data"],
            "topic_category": topic,
            "headlines": [],
            "blog_post": None,
            "status": None,
            "status_callback": log_callback
        }
        
        result_state = await node_write(current_state)
        st.session_state.pipeline_data["blog_post"] = result_state["blog_post"]
        status.update(label="✅ Writing Complete", state="complete", expanded=False)

    st.session_state.status["write"] = "✅ Done"
    st.session_state.status["publish"] = "⏳ Pending"
    st.rerun()

async def run_publish():
    with st.status("🚀 Publishing to Medium...", expanded=True) as status:
        def log_callback(msg):
            st.write(msg)

        current_state = {
            "blog_post": st.session_state.pipeline_data["blog_post"],
            "selected_headline": st.session_state.pipeline_data["selected_headline"],
            "topic_category": topic, # dummy
            "headlines": [], # dummy
            "research_data": "", # dummy
            "status": "",
            "status_callback": log_callback
        }
        
        result_state = await node_publish(current_state)
        st.session_state.pipeline_data["publish_status"] = result_state["status"]
        status.update(label="✅ Published / Drafted", state="complete", expanded=False)

    st.session_state.status["publish"] = "✅ Done"
    st.rerun()

# === Dashboard Layout ===

col1, col2, col3, col4 = st.columns(4)

# 1. Fetch News
with col1:
    st.subheader("1. 🌍 Headlines")
    status = st.session_state.status["fetch_news"]
    st.write(f"Status: **{status}**")
    
    if st.button("🔍 Start Agent", disabled=status == "✅ Done"):
        asyncio.run(run_fetch())
        
    if st.session_state.pipeline_data["headlines"]:
        # Allow user to select
        selected = st.radio("Choose a story:", st.session_state.pipeline_data["headlines"])
        st.session_state.pipeline_data["selected_headline"] = selected
        
        if st.session_state.status["select_headline"] == "🟡 Waiting for User" and selected:
             if st.button("Confirm Selection"):
                 st.session_state.status["select_headline"] = "✅ Done"
                 st.session_state.status["research"] = "⏳ Pending"
                 st.rerun()

# 2. Research
with col2:
    st.subheader("2. 🕵️ Research")
    status = st.session_state.status["research"]
    st.write(f"Status: **{status}**")
    
    if status == "⏳ Pending" and st.session_state.status["select_headline"] == "✅ Done":
        if st.button("Start Research"):
            asyncio.run(run_research())
            
    if st.session_state.pipeline_data["research_data"]:
        with st.expander("View Research Data"):
            st.text(st.session_state.pipeline_data["research_data"])

# 3. Write
with col3:
    st.subheader("3. ✍️ Write")
    status = st.session_state.status["write"]
    st.write(f"Status: **{status}**")
    
    if status == "⏳ Pending" and st.session_state.status["research"] == "✅ Done":
        if st.button("Write Article"):
            asyncio.run(run_write())
            
    if st.session_state.pipeline_data["blog_post"]:
        with st.expander("View Blog Post"):
            st.markdown(st.session_state.pipeline_data["blog_post"])

# 4. Publish
with col4:
    st.subheader("4. 📤 Publish")
    status = st.session_state.status["publish"]
    st.write(f"Status: **{status}**")
    
    if status == "⏳ Pending" and st.session_state.status["write"] == "✅ Done":
        st.info("Make sure you are logged into Medium in Chrome!")
        if st.button("Draft on Medium"):
            asyncio.run(run_publish())
            
    if st.session_state.pipeline_data["publish_status"]:
        st.success(st.session_state.pipeline_data["publish_status"])

# Reset
if st.sidebar.button("Reset Pipeline"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()