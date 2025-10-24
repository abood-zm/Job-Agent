from langchain.agents import create_agent
from dotenv import load_dotenv
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.chat_models import init_chat_model
from playwright.async_api import async_playwright
import os
import asyncio
import pandas as pd
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import (create_async_playwright_browser, aget_current_page)
from langchain_community.tools.playwright.base import BaseBrowserTool

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

Task: Given a careers URL,  (1) open it -> (2) accept cookie/consent if visible -> (3) List the first 5 job detail links (title + absolute URL).

Rules:
- If you see a cookie/consent banner, click an 'Accept' buttin if present, then continue.
- Extract job detail links by finding achors whose href contain '/job/' (site-specific detail pages).
- Return a compact JSON array of {title, url}. No prose.
"""

class FillText(BaseBrowserTool):
    name: str = "fill_text"
    description: str = "Fill text into a website box using Playwright"

    async def _arun(self, selector: str, text: str) -> str:
        print(f"🔧 FILL_TEXT CALLED: selector={selector}, text={text}")
        page = await aget_current_page(self.async_browser)
        page.fill(selector, text)
        return f"Filled {selector} with {text}."
    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async version (_arun).")
        
async def launch_async_browser(headless: bool = True, args = None):
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless, args=args)
    return browser

async def main_async():
    file_path = "source/companies.csv"
    company_file = pd.read_csv(file_path)
    async_broswer = await launch_async_browser(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_broswer)
    tools = toolkit.get_tools()
    fill_text = FillText(async_browser=async_broswer)
    tools.append(fill_text)
    model = init_chat_model("openai:gpt-4o-mini",
                        temperature=0.5,
                        timeout=10,
                        max_tokens=1000)
    agent = create_agent(model=model,system_prompt=SYSTEM_PROMPT, tools=tools)
    # for value in company_file.iloc[:, 0]:
    response = await agent.ainvoke({'messages': [{"role": "user", "content":"Navigate to https://jobs.careers.microsoft.com/global/en/search?l=en_us&pg=1&pgSz=20&o=Relevance&flt=true&ref=cms, Fill the search bar Search for 'Software Engineer' jobs in 'Seattle' Extract all job postings"}]})
    print(response['structured_response'])
    # async_browser.close()

if __name__ == "__main__":
    asyncio.run(main_async())