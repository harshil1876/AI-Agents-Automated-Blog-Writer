import streamlit as st
import asyncio
import nest_asyncio
import os
import sys
from dotenv import load_dotenv

# MUST be the very first thing for Windows asyncio support with subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()

# Import Standard Pipeline Components
from Blog_Pipeline import (
    fetch_daily_news,
    node_research as std_node_research,
    node_write as std_node_write,
    node_publish as std_node_publish,
    BlogState as StandardBlogState
)

# Import Technical Pipeline Components
try:
    from tech_blog_pipeline import (
        get_medium_output,
        select_ideas as tech_select_ideas,
        pick_next_idea as tech_pick_next,
        research_agent as tech_research,
        blog_writer_agent as tech_write,
        ghost_drafter_agent as tech_draft,
        BlogState as TechBlogState
    )
except ImportError as e:
    # Fallback/Placeholder if import fails
    print(f"Error importing tech_blog_pipeline: {e}")
    def get_medium_output(): return ["Error importing pipeline"]
    def tech_select_ideas(s): return s
    def tech_pick_next(s): return s
    def tech_research(s): return s
    def tech_write(s): return s
    def tech_draft(s): return s
    TechBlogState = dict

nest_asyncio.apply()
st.set_page_config(layout="wide", page_title="AI Blog Writer Hub")

# === Helper Functions ===

def init_session_state():
    if "mode" not in st.session_state:
        st.session_state.mode = None
    
    # Standard Pipeline State
    if "std_status" not in st.session_state:
        st.session_state.std_status = {step: "⏳ Pending" for step in ["fetch_news", "select_headline", "research", "write", "publish"]}
    if "std_pipeline_data" not in st.session_state:
        st.session_state.std_pipeline_data = {
            "topic_category": "Artificial Intelligence",
            "headlines": [],
            "selected_headline": None,
            "research_data": "",
            "blog_post": "",
            "publish_status": ""
        }

    # Technical Pipeline State
    if "tech_pipeline_data" not in st.session_state:
        st.session_state.tech_pipeline_data = {
            "ideas": [],           
            "selected_ideas": [],  
            "current_idea": None,
            "research_data": None,
            "blog_post": None,
            "draft_status": None,
            "completed_blogs": {},
            # Tracking status for each step: 'pending', 'running', 'done'
            "status": {
                "initial_ideas": "pending",
                "select_ideas": "pending",
                "pick_next": "pending",
                "research": "pending",
                "write": "pending",
                "draft": "pending"
            }
        }

# === Renderers ===

def render_landing_page():
    # Force some dark mode aesthetics for landing page too, or keep neutral
    st.title("🤖 AI Blog Writer Hub")
    st.markdown("### Choose your writing companion:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.header("📝 Standard Blog Writer")
            st.write("Fetch news, researching, writing, and publishing for general topics.")
            if st.button("Launch Standard Writer", use_container_width=True):
                st.session_state.mode = "standard"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.header("💻 Technical Blog Writer")
            st.write("Deep research, autonomous agents, and technical content generation.")
            if st.button("Launch Technical Writer", use_container_width=True):
                st.session_state.mode = "technical"
                st.rerun()

def render_standard_pipeline():
    # ... (Keep existing Standard Pipeline as is, or minimize changes)
    st.title("📰 Daily AI News Blog Writer")
    if st.sidebar.button("🏠 Switch Mode"):
        st.session_state.mode = None
        st.rerun()
    
    # Re-using the previous code for standard pipeline briefly
    # (To save space, I'm pasting the logic from previous step for standard_pipeline)
    with st.sidebar:
        topic = st.selectbox("Select Topic", ["Artificial Intelligence", "Stock Market", "Technology", "Crypto", "Space Exploration"])
        st.session_state.std_pipeline_data["topic_category"] = topic

    async def run_fetch():
        with st.status("🌍 Fetching News...", expanded=True) as status:
            news = await fetch_daily_news(topic)
            st.session_state.std_pipeline_data["headlines"] = news
            status.update(label="✅ News Fetched", state="complete")
        st.session_state.std_status["fetch_news"] = "✅ Done"
        st.rerun()

    async def run_research():
        with st.status("researching...", expanded=True):
            # simplified for brevity in this specific tool call, assuming standard pipeline logic is largely static
            current_state = {
                "selected_headline": st.session_state.std_pipeline_data["selected_headline"],
                "topic_category": topic,
                "headlines": [], "research_data": None, "blog_post": None, "status": None
            }
            res = await std_node_research(current_state)
            st.session_state.std_pipeline_data["research_data"] = res["research_data"]
        st.session_state.std_status["research"] = "✅ Done"
        st.rerun()

    async def run_write():
        with st.status("writing...", expanded=True):
            current_state = {
                "selected_headline": st.session_state.std_pipeline_data["selected_headline"],
                "research_data": st.session_state.std_pipeline_data["research_data"],
                "topic_category": topic, "headlines": [], "blog_post": None, "status": None
            }
            res = await std_node_write(current_state)
            st.session_state.std_pipeline_data["blog_post"] = res["blog_post"]
        st.session_state.std_status["write"] = "✅ Done"
        st.rerun()

    async def run_publish():
        with st.status("publishing...", expanded=True):
            current_state = {
                "blog_post": st.session_state.std_pipeline_data["blog_post"],
                "selected_headline": st.session_state.std_pipeline_data["selected_headline"],
                "topic_category": "", "headlines": [], "research_data": "", "status": ""
            }
            res = await std_node_publish(current_state)
            st.session_state.std_pipeline_data["publish_status"] = res["status"]
        st.session_state.std_status["publish"] = "✅ Done"
        st.rerun()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.subheader("1. Headlines")
        if st.button("Fetch"): asyncio.run(run_fetch())
        if st.session_state.std_pipeline_data["headlines"]:
            sel = st.radio("Story", st.session_state.std_pipeline_data["headlines"])
            st.session_state.std_pipeline_data["selected_headline"] = sel
            if st.button("Select"): st.session_state.std_status["select_headline"] = "✅ Done"
    with col2:
        st.subheader("2. Research")
        if st.button("Research"): asyncio.run(run_research())
        if st.session_state.std_pipeline_data["research_data"]: st.info("Research Done")
    with col3:
        st.subheader("3. Write")
        if st.button("Write"): asyncio.run(run_write())
        if st.session_state.std_pipeline_data["blog_post"]: st.info("Blog Written")
    with col4:
        st.subheader("4. Publish")
        if st.button("Publish"): asyncio.run(run_publish())
        if st.session_state.std_pipeline_data["publish_status"]: st.success("Published")

# === Technical Pipeline Custom UI ===

def render_technical_pipeline():
    # Custom CSS for Dark Mode Cards
    st.markdown("""
    <style>
    /* Main container background is handled by Streamlit theme, assuming user sets it to dark or we force some colors */
    
    .tech-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        height: 500px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
    }
    
    .tech-header {
        font-size: 1.1em;
        font-weight: bold;
        color: #FFFFFF;
        margin-bottom: 10px;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
        margin-bottom: 10px;
    }
    
    .status-done { background-color: #28a745; color: white; }
    .status-pending { background-color: #6c757d; color: white; }
    .status-running { background-color: #ffc107; color: black; }
    
    .output-area {
        background-color: #2D2D2D;
        color: #E0E0E0;
        padding: 10px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.85em;
        flex-grow: 1;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        /* gap: 10px; */
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("💻 Technical Blog Agent Pipeline")
    
    if st.sidebar.button("🏠 Switch Mode"):
        st.session_state.mode = None
        st.rerun()

    data = st.session_state.tech_pipeline_data
    status_map = data["status"]

    # --- ACTION HANDLERS ---
    # We define them here to keep the render logic clean
    
    async def run_initial_ideas():
        status_map["initial_ideas"] = "running"
        st.rerun() # updates UI to show running
        
    # Since we can't easily do partial reruns in the middle of a script execution without 'st.rerun', 
    # we'll use a specific logic block at the bottom matching the button press.
    
    # --- UI LAYOUT ---
    
    cols = st.columns(6, gap="small")
    
    titles = ["Initial Ideas", "Select Ideas", "Pick Next", "Research", "Write", "Draft"]
    keys = ["ideas", "selected_ideas", "current_idea", "research_data", "blog_post", "draft_status"]
    status_keys = ["initial_ideas", "select_ideas", "pick_next", "research", "write", "draft"]
    
    # Helper to determine badge class
    def get_badge(s):
        if s == "done": return "status-done", "✅ Done"
        if s == "running": return "status-running", "⚠️ Running"
        return "status-pending", "⏳ Pending"

    for i, col in enumerate(cols):
        with col:
            s_key = status_keys[i]
            current_status = status_map[s_key]
            badge_class, badge_text = get_badge(current_status)
            
            # Content formatting
            content = data.get(keys[i])
            if content is None: content = ""
            if isinstance(content, list): content = "\\n".join(str(x) for x in content)
            if not isinstance(content, str): content = str(content)
            
            # Truncate for display if massive? Or let it scroll. 
            # The CSS 'overflow-y: auto' handles scrolling.
            
            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">{titles[i]}</div>
                <div><span class="status-badge {badge_class}">{badge_text}</span></div>
                <div class="output-area">{content if content else "Waiting for input..."}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- CONTROL PANEL ---
    # Smart button that activates the next logical step
    
    # Logic to decide what the main button does
    button_label = "Start Agent"
    next_action = "initial_ideas"
    
    if status_map["initial_ideas"] == "pending":
        button_label = "🚀 Start Agent (Fetch Ideas)"
        next_action = "initial_ideas"
    elif status_map["initial_ideas"] == "done" and status_map["select_ideas"] == "pending":
        button_label = "🤔 Select Best Ideas"
        next_action = "select_ideas"
    elif status_map["select_ideas"] == "done" and (status_map["pick_next"] == "pending" or (status_map["draft"] == "done" and data["selected_ideas"])):
        # If we just finished drafting, or haven't picked yet, we pick next
        button_label = "📌 Pick Next Idea"
        next_action = "pick_next"
    elif status_map["pick_next"] == "done" and status_map["research"] == "pending":
        button_label = "🕵️ Run Research"
        next_action = "research"
    elif status_map["research"] == "done" and status_map["write"] == "pending":
        button_label = "✍️ Write Blog"
        next_action = "write"
    elif status_map["write"] == "done" and status_map["draft"] == "pending":
        button_label = "📤 Draft to Medium"
        next_action = "draft"
    elif status_map["draft"] == "done":
        if data["selected_ideas"]:
            button_label = "🔄 Process Next Idea"
            next_action = "pick_next"
        else:
            button_label = "🎉 All Done! (Restart?)"
            next_action = "restart"

    if st.button(button_label, use_container_width=False):
        if next_action == "restart":
            # Reset
            st.session_state.tech_pipeline_data["status"] = {k: "pending" for k in status_map}
            st.session_state.tech_pipeline_data["ideas"] = []
            st.rerun()
            
        elif next_action == "initial_ideas":
            with st.spinner("Link Scraper Agent Running..."):
                status_map["initial_ideas"] = "running"
                raw = asyncio.run(get_medium_output()) # async call
                if isinstance(raw, list): data["ideas"] = raw
                else: data["ideas"] = [line for line in raw.split('\\n') if line.strip()]
                status_map["initial_ideas"] = "done"
                st.rerun()
                
        elif next_action == "select_ideas":
            with st.spinner("Selection Agent Running..."):
                status_map["select_ideas"] = "running"
                temp = {"ideas": data["ideas"]}
                res = tech_select_ideas(temp)
                data["selected_ideas"] = res.get("selected_ideas", [])
                status_map["select_ideas"] = "done"
                st.rerun()
                
        elif next_action == "pick_next":
            if data["selected_ideas"]:
                status_map["pick_next"] = "running"
                temp = {"selected_ideas": data["selected_ideas"], "current_idea": None}
                res = tech_pick_next(temp)
                data["current_idea"] = res["current_idea"]
                data["selected_ideas"] = res["selected_ideas"]
                # Reset downstream
                data["research_data"] = None
                data["blog_post"] = None
                data["draft_status"] = None
                status_map["research"] = "pending"
                status_map["write"] = "pending"
                status_map["draft"] = "pending"
                status_map["pick_next"] = "done"
                st.rerun()
            else:
                st.warning("No more ideas to pick!")
                
        elif next_action == "research":
            with st.spinner("Deep Research Agent Running..."):
                status_map["research"] = "running"
                temp = {"current_idea": data["current_idea"]}
                res = tech_research(temp)
                data["research_data"] = res["research_data"]
                status_map["research"] = "done"
                st.rerun()

        elif next_action == "write":
            with st.spinner("Writer Agent Running..."):
                status_map["write"] = "running"
                temp = {"research_data": data["research_data"]}
                res = tech_write(temp)
                data["blog_post"] = res["blog_post"]
                status_map["write"] = "done"
                st.rerun()
                
        elif next_action == "draft":
            with st.spinner("Ghost Drafter Agent Running..."):
                status_map["draft"] = "running"
                temp = {
                    "blog_post": data["blog_post"],
                    "completed_blogs": data.get("completed_blogs", {}),
                    "current_idea": data["current_idea"]
                }
                # async call
                res = asyncio.run(tech_draft(temp)) 
                data["completed_blogs"] = res["completed_blogs"]
                data["draft_status"] = "Draft Created on Medium"
                status_map["draft"] = "done"
                st.rerun()

# === Main Execution ===

init_session_state()

if st.session_state.mode == "standard":
    render_standard_pipeline()
elif st.session_state.mode == "technical":
    render_technical_pipeline()
else:
    render_landing_page()