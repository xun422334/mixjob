import os
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "browser_states", "zhaopin_state.json")


class ZhaopinScraper(BaseScraper):
    source_name = "智联招聘"
    base_url = "https://sou.zhaopin.com"
    rate_limit_delay = 2.0

    async def scrape(self, browser=None) -> list[dict]:
        jobs = []
        search_url = f"{self.base_url}/?jl={self.city}&kw={self.keyword}&p=1"

        own_browser = browser is None
        try:
            if own_browser:
                p = await async_playwright().__aenter__()
                browser = await p.firefox.launch(headless=True)

            context_kwargs = {"viewport": {"width": 1280, "height": 800}}
            if os.path.exists(STATE_FILE):
                context_kwargs["storage_state"] = STATE_FILE

            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".joblist-box__item")
            logger.info(f"[ZHAOPIN] Found {len(cards)} cards")

            for card in cards[:30]:
                try:
                    text = card.get_text(" ", strip=True)
                    if not text or len(text) < 10:
                        continue

                    title_el = card.select_one(".jobinfo__name, [class*='job-name'], [class*='job-title']")
                    company_el = card.select_one(".company-name, [class*='company-name']")
                    salary_el = card.select_one(".jobinfo__salary, [class*='salary']")
                    area_el = card.select_one(".jobinfo__other-info-item, [class*='area'], [class*='location']")
                    link_el = card.select_one("a[href*='jobdetail'], a[href*='jobs.zhaopin.com']")

                    title = title_el.get_text().strip() if title_el else ""
                    company = company_el.get_text().strip() if company_el else ""
                    salary = salary_el.get_text().strip() if salary_el else ""
                    area = area_el.get_text().strip() if area_el else ""
                    job_url = ""
                    if link_el:
                        href = link_el.get("href", "")
                        if href:
                            job_url = href if href.startswith("http") else f"{self.base_url}{href}"

                    if not title or not company:
                        tokens = text.split()
                        if not title and tokens:
                            title = tokens[0]
                        if not company:
                            for t in tokens:
                                if any(kw in t for kw in ["有限公司", "科技", "集团", "股份", "网络", "信息"]):
                                    company = t
                                    break

                    if title and company:
                        company = self._clean_company(company)
                        salary = self._clean_salary(salary)

                        city = self.city
                        if area:
                            for c in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "苏州", "西安"]:
                                if c in area:
                                    city = c
                                    break

                        jobs.append({
                            "title": title,
                            "company": company,
                            "city": city,
                            "salary": salary,
                            "description": "",
                            "requirements": "",
                            "location": area,
                            "source_url": job_url or str(page.url),
                            "posted_date": "",
                        })
                except Exception as e:
                    logger.debug(f"智联招聘解析单条失败: {e}")
                    continue

            await context.close()

        except Exception as e:
            logger.warning(f"智联招聘抓取失败: {e}")
        finally:
            if own_browser and browser:
                await browser.close()

        return jobs
