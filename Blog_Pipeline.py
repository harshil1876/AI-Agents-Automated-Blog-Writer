from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Callable
import asyncio
import os
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from google.ai.generativelanguage_v1beta.types import Tool, GoogleSearchRetrieval
from browser_use import Agent, Browser
from pydantic import ConfigDict

load_dotenv()

# === Configuration ===
# === Configuration ===
# Load specific API Keys for each stage to manage limits
# Fallback to GOOGLE_API_KEY if specific key is not set
DEFAULT_KEY = os.getenv("GOOGLE_API_KEY", "")
KEY_FETCH = os.getenv("GOOGLE_API_KEY_FETCH", DEFAULT_KEY)
KEY_RESEARCH = os.getenv("GOOGLE_API_KEY_RESEARCH", DEFAULT_KEY)
KEY_WRITE = os.getenv("GOOGLE_API_KEY_WRITE", DEFAULT_KEY)
KEY_PUBLISH = os.getenv("GOOGLE_API_KEY_PUBLISH", KEY_WRITE)

def get_api_key(type: str) -> str:
    if type == "FETCH": return KEY_FETCH
    if type == "RESEARCH": return KEY_RESEARCH
    if type == "WRITE": return KEY_WRITE
    if type == "PUBLISH": return KEY_PUBLISH
    return DEFAULT_KEY 

# Gemini Model Configuration
# Using gemini-1.5-flash as the standard. Update this if you have access to newer models like gemini-2.0-flash-exp
GEMINI_MODEL = "gemini-2.5-flash"

# Common Chrome Paths on Windows
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# If not found, try x86
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

# Browser Configuration
# Passing arguments directly as BrowserConfig is no longer used in newer versions
browser = Browser(
    executable_path=CHROME_PATH if os.path.exists(CHROME_PATH) else None,
    headless=False  # Must be false to see the agent working and for login
)

# Fix for Browser-Use Pydantic Incompatibility
# Browser-use patches the LLM object, which standard Pydantic models forbid.
class ChatGoogleGenerativeAI_Fixed(ChatGoogleGenerativeAI):
    model_config = ConfigDict(extra='allow')
    
    @property
    def provider(self):
        return "google"
        
    @property
    def model_name(self):
        return self.model

# Validating API Keys
if not DEFAULT_KEY and not KEY_FETCH:
    print("WARNING: GOOGLE_API_KEY is not set. Please set it in the code or environment.")

# === Agents & Tools ===

async def fetch_daily_news(topic: str = "Artificial Intelligence", status_callback: Callable[[str], None] = None) -> List[str]:
    """
    Searches for trending news using Gemini Grounding (Google Search).
    Returns a list of headlines.
    """
    query = f"latest trending news, events, and developments in {topic} from today"
    if status_callback:
        status_callback(f"🔍 Searching & Extracting news for: {query} using Gemini Grounding...")
    else:
        print(f"🔍 Searching news for: {query}")
    
    try:
        # We use a specialized instance with search tool enabled
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=get_api_key("FETCH"),
            temperature=0.7
        )
        
        # Binding the Google Search tool for grounding implies the model can access the web.
        # For ChatGoogleGenerativeAI, typically valid tools are passed via bind_tools or in the constructor if supported.
        # However, for 2.0 Flash / 1.5 Pro, we can trust the native grounding capability if we explicitly ask for it 
        # or use the 'google_search_retrieval' tool name if using the official tool binding.
        # Let's try simple prompting first which often triggers grounding in recent models if configured, 
        # but to be sure we bind the tool.
        # Note: 'google_search_retrieval' is the internal tool name for grounding.
        
        # Alternative: We make a strong prompt asking for search.
        
        prompt = f"""
        You have access to Google Search. Find the latest trending news about "{topic}" from today.
        Extract the top 5 distinct news headlines from the search results.
        Return ONLY the headlines, one per line. Do not include introductory text.
        """
        
        # Use the official Tool object for Grounding
        # This prevents LangChain from misinterpreting it as a Function Declaration
        tool = Tool(google_search_retrieval=GoogleSearchRetrieval())
        llm_with_tools = llm.bind(tools=[tool])

        # IMPORTANT: 'bind' returns a runnable.
        response = llm_with_tools.invoke(prompt)
        
        headlines = [h.strip() for h in response.content.split('\n') if h.strip()]
        return headlines
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        return [f"Failed to fetch news for {topic}: {e}"]

def research_topic(topic: str, status_callback: Callable[[str], None] = None) -> str:
    """
    Performs deep research on a specific topic using Gemini Grounding.
    """
    if status_callback:
        status_callback(f"🕵️ Researching with Gemini Grounding: {topic}")
    else:
        print(f"🕵️ Researching: {topic}")
    
    try:
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=get_api_key("RESEARCH"),
            temperature=0.3
        )
        # Bind search tool
        tool = Tool(google_search_retrieval=GoogleSearchRetrieval())
        llm_with_search = llm.bind(tools=[tool])
        
        if status_callback: status_callback("🌐 Running grounded search analysis...")
        
        prompt = f"""
        Research the following topic in depth: "{topic}".
        Provide a comprehensive summary including:
        1. Key details and context.
        2. Analysis and expert opinions.
        3. Recent developments.
        
        Use Google Search to ensure up-to-date and accurate information.
        """
        
        response = llm_with_search.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Research failed: {e}"

def write_blog_post(topic: str, research_data: str, status_callback: Callable[[str], None] = None) -> str:
    """
    Writes a full blog post using Gemini.
    """
    if status_callback:
        status_callback(f"✍️ Writing blog post for: {topic}")
    else:
        print(f"✍️ Writing blog for: {topic}")
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=get_api_key("WRITE"))
    
    prompt = f"""
    You are an expert tech blooger. Write a comprehensive, engaging blog post about: "{topic}".
    
    Use the following research data to ensure accuracy:
    {research_data}
    
    Format the blog post in Markdown with:
    - Catchy Title
    - Introduction
    - Key Takeaways (Bullet points)
    - In-depth Analysis
    - Conclusion
    
    Tone: Professional yet accessible.
    """
    response = llm.invoke(prompt)
    return response.content

async def draft_to_medium(title: str, content: str, status_callback: Callable[[str], None] = None) -> str:
    """
    Uses Browser-Use to draft the article on Medium.
    Assumes user is logged in or will log in quickly.
    """
    if status_callback:
        status_callback("🚀 Initializing Browser Agent for Medium...")
    else:
        print("🚀 Auto-Drafting on Medium...")
    
    # Simple prompt for the browser agent
    task = f"""
    1. Go to https://medium.com/new-story
    2. Wait for the page to load.
    3. If there is a Title field, type "{title}" into it.
    4. Type the following content into the main story area:
    
    {content[:500]}... (Content truncated for agent instructions, but full content should be pasted)
    
    (Note: For this demo, just pasting the beginning to show it works. In production, we'd paste the whole thing)
    """
    
    # Note: Passing the full content to the agent prompt might be too long. 
    # A better approach for the agent is to copy-paste. 
    # For now, let's keep it simple and just create a draft with the basics.
    
    # Use the Fixed class that allows monkey-patching by browser-use
    llm = ChatGoogleGenerativeAI_Fixed(model=GEMINI_MODEL, google_api_key=get_api_key("PUBLISH"))
    
    # We create a new agent for this specific task
    agent = Agent(
        task=f"Go to medium.com/new-story. Type '{title}' in the title. Type 'Draft created by AI Agent. Content to be inserted.' in the body.",
        llm=llm,
        browser=browser
    )
    
    try:
        if status_callback: status_callback("🤖 Agent running... (Check opened browser)")
        await agent.run()
        return "Draft Created on Medium (Check your browser)"
    except Exception as e:
        return f"Failed to draft on Medium: {e}"

# === Shared State ===
class BlogState(TypedDict):
    topic_category: str # "AI", "Stocks", "Tech"
    headlines: List[str]
    selected_headline: Optional[str]
    research_data: Optional[str]
    blog_post: Optional[str]
    status: str
    status_callback: Optional[Callable[[str], None]]

# === Node Functions ===
async def node_fetch_news(state: BlogState) -> BlogState:
    news = await fetch_daily_news(state["topic_category"], state.get("status_callback"))
    return {**state, "headlines": news}

async def node_research(state: BlogState) -> BlogState:
    data = research_topic(state["selected_headline"], state.get("status_callback"))
    return {**state, "research_data": data}

async def node_write(state: BlogState) -> BlogState:
    post = write_blog_post(state["selected_headline"], state["research_data"], state.get("status_callback"))
    return {**state, "blog_post": post}

async def node_publish(state: BlogState) -> BlogState:
    # Extract title (first line usually)
    lines = state["blog_post"].split('\n')
    title = lines[0].replace('#', '').strip()
    
    status = await draft_to_medium(title, state["blog_post"], state.get("status_callback"))
    return {**state, "status": status}

# === LangGraph Definition ===
workflow = StateGraph(BlogState)
workflow.add_node("fetch_news", node_fetch_news)
workflow.add_node("research", node_research)
workflow.add_node("write", node_write)
workflow.add_node("publish", node_publish)

workflow.set_entry_point("fetch_news")
workflow.add_edge("fetch_news", "research") # In the UI we'll break here to let user select
workflow.add_edge("research", "write")
workflow.add_edge("write", "publish")
workflow.add_edge("publish", END)

app = workflow.compile()

# For testing functionality directly
if __name__ == "__main__":
    import asyncio
    
    # Default topic for standalone run
    DEFAULT_TOPIC = "Artificial Intelligence"
    
    print(f"🚀 Launching Standard Blog Pipeline for topic: {DEFAULT_TOPIC}...")
    
    initial_state = {
        "topic_category": DEFAULT_TOPIC,
        "headlines": [],
        "selected_headline": None,
        "research_data": None,
        "blog_post": None,
        "status": "Starting",
        "status_callback": None
    }
    
    # The standard pipeline starts with 'fetch_news', so we can just invoke it.
    app.invoke(initial_state)