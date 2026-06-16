import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)


class GuopinScraper(BaseScraper):
    source_name = "国聘"
    base_url = "https://www.iguopin.com"
    rate_limit_delay = 2.0

    async def scrape(self, browser=None) -> list[dict]:
        jobs = []
        search_url = f"{self.base_url}/job?keyword={self.keyword}&city={self.city}"

        own_browser = browser is None
        try:
            if own_browser:
                p = await async_playwright().__aenter__()
                browser = await p.firefox.launch(headless=True)

            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            left_parts = soup.select(".job-left")
            right_parts = soup.select(".job-right")
            logger.info(f"[GUOPIN] Found {len(left_parts)} job-left / {len(right_parts)} job-right")

            for i, left in enumerate(left_parts[:30]):
                try:
                    left_text = left.get_text(" ", strip=True)
                    if not left_text or len(left_text) < 5:
                        continue

                    title_match = re.match(r'^(.+?)「', left_text)
                    title = title_match.group(1).strip() if title_match else left_text.split(" ")[0]

                    loc_match = re.search(r'「(.+?)」', left_text)
                    area = loc_match.group(1) if loc_match else ""

                    salary_match = re.search(r'(\d+~\d+[Kk万]|面议)[^\s]*', left_text)
                    salary = salary_match.group(1) if salary_match else ""

                    company = ""
                    if i < len(right_parts):
                        right_text = right_parts[i].get_text(" ", strip=True)
                        company_parts = right_text.split(" ")
                        if company_parts:
                            company = company_parts[0]

                    city = self.city
                    if area:
                        for c in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "苏州", "西安", "重庆", "天津"]:
                            if c in area:
                                city = c
                                break

                    if title and company and len(company) >= 4:
                        company = self._clean_company(company)
                        salary = self._clean_salary(salary)
                        jobs.append({
                            "title": title,
                            "company": company,
                            "city": city,
                            "salary": salary,
                            "description": "",
                            "requirements": "",
                            "location": area,
                            "source_url": str(page.url),
                            "posted_date": "",
                        })
                except Exception as e:
                    logger.debug(f"国聘解析单条失败: {e}")
                    continue

            await context.close()

        except Exception as e:
            logger.warning(f"国聘抓取失败: {e}")
        finally:
            if own_browser and browser:
                await browser.close()

        return jobs
