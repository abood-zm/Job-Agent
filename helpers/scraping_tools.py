from langchain_community.tools.playwright.base import BaseBrowserTool
from langchain_community.tools.playwright.utils import aget_current_page
from pydantic import BaseModel, Field
from helpers.delays import human_typing, human_delays
import random
import json

SERACH_SELECTORS = [
    "input[type='search']",
    "input[aria-label*='Search']",
    "input[placeholder*='Search']",
    "div[role='search'] input",
    "div[role='combobox'] input",
    "textarea[name='q']",
    "input[name='q']",
]

JOB_SELECTORS = [
            'a[href*="/job/"]',
            'a[href*="jobId"]',
            'a[data-automation*="job"]',
            'div[role="listitem"] a',
            'article a',
            '[class*="job"] a[href]',
        ]

async def pick_search(page):
    for selector in SERACH_SELECTORS:
            try:
                loc = page.locator(selector).first
                if await loc.is_visible(timeout=1500):
                    print(f"Found search input with selector: {selector}")
                    return loc
            except Exception as e:
                print(f"Selector '{selector}' failed: {e}")
    return None

class FillTextArgs(BaseModel):
    selector: str = Field(..., description="CSS/XPath/role selector")
    text: str = Field(..., description="Text to input")


# class SearchType(BaseBrowserTool):
#     name: str = "search_type"
#     description: str = "Intelligently finds search input on page and types query with Enter"
#     class ArgsSchema(BaseModel):
#         query: str = Field(..., description="Search query to type")
#     args_schema: type[BaseModel] = ArgsSchema

#     async def _arun(self, query: str) -> str:
#         page = await aget_current_page(self.async_browser)
#         await human_delays(500, 1000)
#         search_input = None
#         for selector in SERACH_SELECTORS:
#             try:
#                 loc = page.locator(selector).first
#                 if await loc.is_visible(timeout=1000):
#                     search_input = loc
#                     print(f"Found search locator: {search_input}")
#                     break
#             except: continue
#         if not search_input:
#             return "Error: could not find search input"
#         try:
#             await search_input.click()
#             await human_delays(200, 400)
#             await human_typing(page, query)
#             await human_delays(300, 500)
#             await page.keyboard.press("Enter")
#             print("Pressed Enter")
#             await page.wait_for_load_state('networkidle', timeout=10000)
#             await human_delays(1000, 1500)
#             return f"Searched for {query}"
#         except Exception as e:
#             return f"Error: {e}"
#     def _run(self, *args, **kwargs):
#         raise NotImplementedError("Use async version")

class FillText(BaseBrowserTool):
    name: str = "fill_text"
    description: str = "Fill text into an input/textarea using Playwright"
    args_schema: type[BaseModel] = FillTextArgs

    async def _arun(self, selector: str, text: str) -> str:
        page = await aget_current_page(self.async_browser)

        # await human_delays(300, 800)
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=5000)
        except: pass
        await human_delays(500, 1000)
        loc = None
        try:
            loc = page.locator(selector).first
            await loc.wait_for(state='visible', timeout=3000)
            if not await loc.is_visible():
                loc = None
        except Exception as e:
            print(f"Selector {selector} failed: {e}")
            loc = None
        
        if loc is None:
            print("Falling to automatic search detection...")
            loc = await pick_search(page)
        
        if loc is None:
            return f"Error: Could not find element with selector '{selector}' or any search input"
        print(loc)

        try:
            box = await loc.bounding_box()
            if box:
                x = box['x'] + random.uniform(10, box['width'] - 10)
                y = box['y'] + random.uniform(10, box['height'] - 10)
                await page.mouse.move(x, y)
                await human_delays(100, 300)
        except:
            pass
        try:
            # await loc.fill(text)
            await loc.click()
            await human_delays(200, 500)
            await human_typing(page, text)
        except Exception:
            await loc.click(force=True)
            await human_delays(200, 500)
            await human_typing(page, text)
        await page.keyboard.press("Enter")
        await human_delays(300, 700)

        return f"Filled {selector} with: {text}"

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async version (_arun).")
    
class AcceptCookies(BaseBrowserTool):
    name: str = "accept_cookies"
    description: str = "Clicks a visible 'Accept' cookie/consent button if present."

    async def _arun(self) -> str:
        page = await aget_current_page(self.async_browser)
        await human_delays(500, 1000)
        selectors = [
            'button[aria-lable*="Accept"]',
            'button:has-text("Accept all")',
            'button:has-text("Accept")',
            'button:has-text("I agree")'
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=1500):
                    try:
                        box = await btn.bounding_box()
                        if box:
                            x = box['x'] + random.uniform(5, box['width'] - 5)
                            y = box['y'] + random.uniform(5, box['width'] - 5)
                            await page.mouse.move(x, y)
                            await human_delays(200, 400)
                    except: pass

                    await btn.click()
                    await page.wait_for_timeout(400)
                    return f"Clicked consent button via {sel}"
                
            except:
                pass
        return "No consent button visible"
    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async version (_arun).")
    
class GetJobLinks(BaseBrowserTool):
    name: str = "get_job_links"
    description: str = "Return first 5 Job detail links on the page as JSON [{'title', 'url'}]."

    class ArgsSchema(BaseModel):
        limit: int = Field(5, description="Number of jobs to extract")
    
    # async def _arun(self, limit: int = 5) -> str:
    #     page = await aget_current_page(self.async_browser)
    #     await human_delays(1000, 2000)
    #     job_cards = page.locator('div.SearchJobDetailsCard, div[role="group"].ms-DocumentCard')
    #     card_count = await job_cards.count()
    #     print(f"Found {card_count} job cards")

    #     if card_count == 0:
    #         return '{"error": "No job cards found"}'
    #     jobs = []
    #     for i in range(min(card_count, limit)):
    #         try:
    #             print(f"\n=== Job {i+1}/{min(card_count, limit)} === ")
    #             job_cards = page.locator('div.SearchJobDetailsCard, div[role="group"].ms-DocumentCard')
    #             card = job_cards.nth(i)
    #             title_elem = card.locator('h1').first
    #             title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else "N/A"
    #             print(f"Title: {title}")
    #             await card.click()
    #             await human_delays(1500, 2500)
    #             content = await page.inner_text('body')
    #             location = "N/A"
    #             job_id = "N/A"
    #             lines = content.split('\n')
    #             for idx, line in enumerate(lines):
    #                 if 'location' in line.lower() and idx + 1 < len(lines):
    #                     location = lines[idx + 1].strip()
    #                 if 'job_id' in line.lower() and idx + 1 < len(lines):
    #                     job_id = lines[idx + 1].strip()
    #             jobs.append({
    #                 "title": title,
    #                 "location": location,
    #                 "job_id": job_id,
    #                 "description_snipper": content[:800].strip()
    #             })
    #             await page.go_back()
    #             await human_delays(1500, 2500)
    #             await page.wait_for_selector('div.SearchJobDetailsCard', timeout=5000)
    #         except Exception as e:
    #             print(f"Error on job {i}: {e}")
    #             try:
    #                 await page.go_back()
    #                 await human_delays(1500, 2000)
    #             except: pass
    #             continue
    #         return json.dumps(jobs, ensure_ascii=False) if jobs else '{"error": "No jobs extracted"}'
    # def _run(self, *args, **kwargs):
    #     raise NotImplementedError("Use async version")

    async def _arun(self, limit: int = 5) -> str:
        page = await aget_current_page(self.async_browser)
        await human_delays(1000, 2000)

        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass

        await human_delays(1000, 1500)

        try:
            await page.evaluate("window scrollBy(0, window.innerHeight * 0.5)")
            await human_delays(500, 800)
            await page.evaluate("window scrollBy(0, -window.innerHeight * 0.3)")
            await human_delays(500, 800)
        except: pass

        job_cards = page.locator('div.SearchJobDetailsCard, div[role="group"].ms-DocumentCard')
        card_count = await job_cards.count()
        if card_count == 0:
            job_cards = page.locator('div[role="group"]:has(h1)')
            card_count = await job_cards.count()
        jobs = []
        for i in range(min(card_count, limit)):
            try:
                card = job_cards.nth(i)
                title_elem = card.locator('h1').first

                title = await title_elem.inner_text() if await title_elem.count() > 0 else "no title"
                title = title.strip()
                print(f"Title is {title}")
                try:
                    await card.click(timeout=2000)
                    await human_delays(500, 1000)
                except Exception as e:
                    print(f"Couldn't click card: {e}")
            
                location = "N/A"
                job_id = "N/A"
                description = "N/A"

                try:
                    location_elem = card.locator('text=/location|Location|office/i').first
                    if await location_elem.count() > 0:
                        location = await location_elem.inner_text()
                        location = location.strip()
                except: pass
                
                try:
                    job_id_elem = card.locator('text=/job id|Job ID|Requisition/i').first
                    if await job_id_elem.count() > 0:
                        job_id = await job_id_elem.inner_text()
                        job_id = job_id.strip()
                except: pass

                try:
                    all_text = await card.inner_text()
                    description = all_text[:500].strip()
                    print("Agent extracted the text...")
                except: pass

                job_data = {
                    "title": title,
                    "location": location,
                    "job_id": job_id,
                    "description_snippet": description,
                    "index": i
                }
                jobs.append(job_data)
                print(f"Extract: {title}")
                try:
                    await card.scroll_into_view_if_needed()
                    print("Agent scrolled the screen...")
                    await human_delays(300, 600)
                except: pass

            except Exception as e:
                print(f"Error processing job {i}: {e}")
                try:
                    await page.go_back()
                    print("Agent went back...")
                    await human_delays(1500, 2000)
                except: pass
                continue
        await human_delays(400, 800)
            
        if len(jobs) == 0:
            return json.dumps({
                "error": "No job cards found",
                "page_url": page.url,
                "card_count": card_count,
            }, ensure_ascii=False)
        else:
            return json.dumps(jobs, ensure_ascii=False)
        
    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async version (_arun).")