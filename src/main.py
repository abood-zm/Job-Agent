from langchain.agents import create_agent
from dotenv import load_dotenv
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.chat_models import init_chat_model
from playwright.async_api import async_playwright, Playwright
from langchain.messages import SystemMessage, HumanMessage
import os
import asyncio
import pandas as pd
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import (create_async_playwright_browser, aget_current_page)
from langchain_community.tools.playwright.base import BaseBrowserTool
from helpers import FillText, AcceptCookies, GetJobLinks
"""
What needs to be fixed:
1. Fix the prompt to make it more focused on navigation + link discovery
2. Add timeouts to make it seem realistic.


Step 1. navigate -> accept cookies -> list job links
"""
load_dotenv()

SYSTEM_PROMPT = """
You are a helpful and professional job hunter. Your goal is for each job description, analyze it, retrieve relevant parts of his experience, and summarize the match in concise bullet points.”

Here is your task in steps:
    Step 1: Extract and fetch the job descriptions according to the inputs.
    Step 2: Summarize the jobs in bullet point as the following: [Job title] at [Company name]: [Consice summary].
        Example: Machine Learning Engineer (LLM) at Bjak (London, UK): This role offers hands-on experience with LLM fine-tuning, prompt engineering, and deployment, directly leveraging your MSc in Robotics and AI and LLMs/RAG experience. You'll utilize Python and PyTorch in a startup-like project environment focused on real-world impact.
    Step 3: Write a good message that will be sent via Slack.
    Step 4: Send the message to the targetted user through Slack.

DO:
    1. Make sure that the summary is relevant to the input.
    2. Write the summaries in bullet points for each extracted job.
    3. Output only short, clear points. Highlight missing skills or experience gaps if applicable.
    4. Always prioritize accuracy of comparison over creative writing.

DO NOT:
    1. Rewrite the job descriptions.
    2. Mention anything else other than the job description such as info about the company, benefits, etc.

This is a tough task so make sure you do your job correctly. Explain what you're doing. Good luck!
"""

STEP1_PROMPT = """
You are a careful web agent.

Task: Given a careers URL, do the following steps:
(1) Navigate to the URL.
(2) accept cookie/consent if visible using accept_cookies tool
(3) Search for "Software Engineering" roles in the search bar using fill_text tool.
(4) Find the first job description and extract using get_job_links.
(5) Once the first job is extracted, go back using previous_tool.
(6) Keep extracting until you reach 5 jobs. return them as JSON.

Rules:
- If you see a cookie/consent banner, click an 'Accept' buttin if present, then continue.
- Extract job detail links by finding achors whose href contain '/job/' (site-specific detail pages).
- Return a compact JSON array of {title, url}. No prose.
- You will need to go back when you extract for each job.
- Keep the number of jobs 5 only. 
"""
        
async def launch_async_browser(headless: bool = True, args = None):
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless, args=args)
    return browser

async def launch_playwright(playWright: Playwright):
    chromium = playWright.chromium
    browser = await chromium.launch(headless=False)
    return browser

async def main():
    file_path = "source/companies.csv"
    company_file = pd.read_csv(file_path)
    # async with async_playwright() as playWright:
    #     async_browser = await launch_playwright(playWright)
    async_browser = await launch_async_browser(headless=False)

    # ===================== TOOLS ===================
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    custom_tools = [
        FillText(async_browser=async_browser),
        AcceptCookies(async_browser=async_browser),
        GetJobLinks(async_browser=async_browser)
    ]
    tools = tools + custom_tools
    
    # ===================== PROMPTS ===================
    career_url = "https://jobs.careers.microsoft.com/global/en/search?l=en_us&pg=1&pgSz=20&o=Relevance&flt=true&ref=cms"
    message = [
        SystemMessage(STEP1_PROMPT),
        HumanMessage("{input}")
    ]

    # ===================== MODEL ===================
    model = init_chat_model("openai:gpt-4o-mini",
                        temperature=0.3,
                        timeout=60,
                        max_tokens=800)
    agent = create_agent(model=model, system_prompt=STEP1_PROMPT, tools=tools)

    #  ===================== AGENT ===================
    # for value in company_file.iloc[:, 0]:
    async for step in agent.astream({
        'messages': [{"role": "user", "content":f"Navigate to {career_url}, call accept_cookies, then call fill_text, return first 5 job descriptions. Return the JSON only. "}]}, stream_mode="updates"):
        for _node, data in step.items():
            data["messages"][-1].pretty_print()
    # try:
    #     # response = await agent.ainvoke({
    #     #     "message": [{
    #     #         "role": "user", 
    #     #         "content": f"Navigate to {career_url}, call accept_cookies, then call fill_text, return first 5 job descriptions. Return the JSON only."
    #     #     }]
    #     # })
        
    #     # Extract AI response
    #     messages = response['messages']
    #     ai_messages = [m for m in messages if m.__class__.__name__ == "AIMessage"]
        
    #     if ai_messages:
    #         response_text = ai_messages[-1].content
    #         print("\n=== RESULT ===")
    #         print(response_text)
            
    #         # Optionally parse and format the JSON
    #         try:
    #             import json
    #             jobs = json.loads(response_text)
    #             print(f"\n✓ Successfully extracted {len(jobs)} jobs")
    #             for i, job in enumerate(jobs, 1):
    #                 print(f"\n{i}. {job.get('title', 'N/A')}")
    #                 print(f"   Location: {job.get('location', 'N/A')}")
    #                 print(f"   Job ID: {job.get('job_id', 'N/A')}")
    #         except:
    #             pass
        
    # except Exception as e:
    #     print(f"Error: {e}")
    # finally:
    await async_browser.close()
    print("\nBrowser Closed")
    # async_browser.close()

if __name__ == "__main__":
    asyncio.run(main())