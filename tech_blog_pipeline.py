from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
from playwright.async_api import async_playwright
import asyncio
import time
import requests
# Removed OpenAI imports
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, BrowserConfig, Browser, BrowserSession
import ast
from dotenv import load_dotenv
import os

load_dotenv()

'''
Team of 5 AI Agents writing technical blogs (Gemini Powered):

Agent 1: Medium Scraper (Browser Agent)
Agent 2: Content Selector (Gemini LLM)
Agent 3: Perplexity Deep Research (API)
Agent 4: Blog Writer (Gemini LLM)
Agent 5: Medium Drafter (Browser Agent)
'''

browser_session = BrowserSession(user_data_dir= None) #for 1st step
browser_session1 = BrowserSession(allowed_domains=['https://dev.to/'], user_data_dir= None) #for last step

# === Configuration ===
gemini_key = os.getenv("GEMINI_KEY")
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

sensitive_data = {
    'https://dev.to': {
        'email': os.getenv("EMAIL"),
        'password': "outskill50@", # Helper: Ensure this is flexible or env var in future
    },
}

# Model to use
GEMINI_MODEL = "gemini-2.0-flash-exp" # Using capable model for agents

# === Medium Output (Browser Agent) ===
async def get_medium_output() -> str:
    user_task = ('''go to https://dev.to/ and then search for AI Agents in the search bar and press enter and then print the title''')
    print("🚀 Running Medium Agent (Gemini)...")
    execution_result = await run_agent_with_retry(user_task)

    if execution_result:
        extraction_prompt = f"""
        You are an AI assistant analyzing the full result of a browser automation agent run.
        Given the full execution result below, extract and return only the **final output** of the agent - typically the `extracte
        Execution Result: {execution_result}
        Respond with just the final output content. No prefix text. No suffix text.
        """
        extraction_llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, api_key=gemini_key)
        response = extraction_llm.invoke(extraction_prompt)
        final_output = response.content.strip()
        return final_output
    else:
        return ""

async def run_agent_with_retry(task_plan: str, max_retries: int = 3):
    """
    Uses Gemini to run the browser automation agent.
    """
    retries = 0
    async with async_playwright() as playwright:
        while retries < max_retries:
            try:
                llm_local = ChatGoogleGenerativeAI(model=GEMINI_MODEL, api_key=gemini_key)
                agent = Agent(task=task_plan, llm=llm_local, browser=Browser, browser_session=browser_session)
                result = await agent.run()  # Capture the final output of the agent run
                return result
            except Exception as e:
                print(f" [Medium Agent Attempt {retries+1}] Task failed: {e}")
                retries += 1
        print(f"❌ Medium Agent failed after {max_retries} retries. Aborting.")
        return None

# === Blog Pipeline Functions ===
def content_selector(ideas, api_key=None) -> list:
    # api_key arg kept for signature compatibility but unused
    print("Here are the ideas raw", ideas)
    
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, api_key=gemini_key)
    
    prompt = f"""
    You are a Content Strategy Agent.
    Here is a list of potential blog topics/titles found on the web:
    {ideas}
    
    Select the top 3-5 most engaging, technical, and relevant ideas for an implementation-focused AI blog.
    Return ONLY a Python list of strings. Do not explain.
    Example: ["Idea 1", "Idea 2"]
    """
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"❌ Content Selector failed: {e}")
        return []

def run_perplexity_agent(idea: str) -> str:
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "Be precise and concise."},
            {"role": "user", "content": f"Provide in-depth research on the following topic: {idea}"}
        ],
        "max_tokens": 500, # Increased for better research
        "temperature": 0.2,
        "top_p": 0.9,
        "return_images": False,
        "return_related_questions": False,
        "stream": False,
        "presence_penalty": 0,
        "frequency_penalty": 1
    }
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            # Parse properly to get content
            try:
                data = response.json()
                return data['choices'][0]['message']['content']
            except:
                return response.text
        else:
            print("❌ Error from Perplexity:", response.status_code, response.text)
            return ""
    except Exception as e:
        print(f"❌ Perplexity Request failed: {e}")
        return ""

def blog_writer(research_data: str, api_key=None) -> str:
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, api_key=gemini_key)
    
    prompt = f"""
    You are an expert Technical Blog Writer Agent.
    Write a complete, high-quality technical blog post based strictly on this research:
    
    {research_data}
    
    Format:
    - Markdown (headers, code blocks if needed)
    - Engaging Title
    - Introduction
    - Technical Depth
    - Conclusion
    
    Do not mention 'Based on the research'. Just write the blog.
    """
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"❌ Blog Writer failed: {e}")
        return ""

async def ghost_draft(blog_post: str) -> str:
    async with async_playwright():
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, api_key=gemini_key)
        user_task = f"go to https://dev.to/ and login with email and password then click on create post and paste the article below:\n\n{blog_post}"
        # Truncate if too long for prompt or allow agent to handle it. 
        # For browser-use, passing giant text in task string can be iffy, but we'll stick to original logic.
        
        agent = Agent(task=user_task, llm=llm, sensitive_data=sensitive_data, browser_session=browser_session1, use_vision=False)
        result = await agent.run()
        return result


# === Shared State ===
class BlogState(TypedDict):
    ideas: List[str]
    selected_ideas: List[str]
    current_idea: Optional[str]
    research_data: Optional[str]
    blog_post: Optional[str]
    completed_blogs: dict

# === Node Functions ===
def select_ideas(state: BlogState) -> BlogState:
    raw_selected = content_selector(state["ideas"])
    print("this is raw selected", raw_selected)

    parsed_selected = []

    if isinstance(raw_selected, str):
        try:
            # Clean up markdown code blocks if Gemini adds them
            clean_str = raw_selected.replace("```python", "").replace("```json", "").replace("```", "").strip()
            parsed_selected = ast.literal_eval(clean_str)
        except Exception as e:
            print("Error parsing selected ideas:", e)
            # Fallback: try splitting lines
            parsed_selected = [line.strip("- *") for line in clean_str.split('\n') if line.strip()]
            
    elif isinstance(raw_selected, list):
        parsed_selected = raw_selected

    cleaned = [item for item in parsed_selected if isinstance(item, str) and item.strip()]

    print(f"🧠 Selected ideas (cleaned): {cleaned}")
    return {**state, "selected_ideas": cleaned, "completed_blogs": {}}

def pick_next_idea(state: BlogState) -> BlogState:
    if state["selected_ideas"]:
        next_idea = state["selected_ideas"].pop(0)
        print(f"📌 Picking next idea: {next_idea}")
        return {**state, "current_idea": next_idea}
    return state

def research_agent(state: BlogState) -> BlogState:
    research = run_perplexity_agent(state["current_idea"])
    return {**state, "research_data": research}

def blog_writer_agent(state: BlogState) -> BlogState:
    blog = blog_writer(state["research_data"])
    return {**state, "blog_post": blog}

async def ghost_drafter_agent(state: BlogState) -> BlogState:
    await ghost_draft(state["blog_post"]) # ✅ Proper async
    updated_completed = {
        **state["completed_blogs"],
        state["current_idea"]: {
            "blog_post": state["blog_post"]
        }
    }
    return {
        **state,
        "completed_blogs": updated_completed,
        "blog_post": None,
        "current_idea": None,
        "research_data": None
    }

def has_more_ideas(state: BlogState) -> str:
    return "pick_next" if state["selected_ideas"] else END

# === LangGraph Definition ===
workflow = StateGraph(BlogState)
workflow.add_node("select_ideas", select_ideas)
workflow.add_node("pick_next", pick_next_idea)
workflow.add_node("research", research_agent)
workflow.add_node("write", blog_writer_agent)
workflow.add_node("draft", ghost_drafter_agent)
workflow.set_entry_point("select_ideas")
workflow.add_edge("select_ideas", "pick_next")
workflow.add_edge("pick_next", "research")
workflow.add_edge("research", "write")
workflow.add_edge("write", "draft")
workflow.add_conditional_edges("draft", has_more_ideas, {"pick_next": "pick_next", END: END})
app = workflow.compile()

# === Execute ===
if __name__ == "__main__":
    import asyncio
    medium_raw = asyncio.run(get_medium_output())

    if not medium_raw:
        print("❌ Failed to fetch Medium output. Exiting.")
        exit()
    
    # Handle potential list or string output from get_medium_output
    ideas_list = medium_raw if isinstance(medium_raw, list) else medium_raw.strip().split("\n")

    initial_state = {
        "ideas": ideas_list,
        "selected_ideas": [],
        "current_idea": None,
        "research_data": None,
        "blog_post": None,
        "completed_blogs": {}
    }
    print("🚀 Launching LangGraph Blog Orchestrator (Gemini Powered)...")
    app.invoke(initial_state)