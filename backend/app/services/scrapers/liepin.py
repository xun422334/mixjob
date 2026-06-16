import os
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)

CITY_CODE_LIEPIN = {
    "北京": "010", "上海": "020", "广州": "050", "深圳": "060",
    "杭州": "080", "成都": "120", "武汉": "160", "南京": "040",
    "苏州": "035", "西安": "210",
}

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "browser_states", "liepin_state.json")


class LiepinScraper(BaseScraper):
    source_name = "猎聘"
    base_url = "https://www.liepin.com"
    rate_limit_delay = 2.0

    async def scrape(self) -> list[dict]:
        jobs = []
        city_code = CITY_CODE_LIEPIN.get(self.city, "010")
        search_url = f"{self.base_url}/zhaopin/?city={city_code}&key={self.keyword}"

        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                context_kwargs = {"viewport": {"width": 1280, "height": 800}}

                if os.path.exists(STATE_FILE):
                    context_kwargs["storage_state"] = STATE_FILE

                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()

                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".job-card-pc-container, .job-detail-box")
                logger.info(f"[LIEPIN] Found {len(cards)} cards")

                for card in cards[:30]:
                    try:
                        text = card.get_text(" ", strip=True)
                        if not text or len(text) < 10:
                            continue

                        title_el = card.select_one(".job-title-wrapper .job-title, h3, [class*='job-title']")
                        company_el = card.select_one(".company-name, [class*='company-name']")
                        salary_el = card.select_one(".salary, [class*='salary'], .text-warning")
                        area_el = card.select_one(".job-area, .job-dq, [class*='area'], [class*='location']")
                        link_el = card.select_one("a[href*='/job/']")

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
                            lines = [l.strip() for l in text.split(" ") if l.strip()]
                            if len(lines) >= 2:
                                if not title:
                                    title = lines[0]
                                if not company:
                                    for line in lines:
                                        if any(kw in line for kw in ["有限公司", "科技", "集团", "股份", "网络", "信息", "软件"]):
                                            if not any(skip in line for skip in ["人", "最佳雇主", "已上市"]):
                                                company = line
                                                break

                        if title and company and len(company) >= 4 and not company.endswith(("区", "县", "市")):
                            company = self._clean_company(company)
                            salary = self._clean_salary(salary)

                            city = self.city
                            if area:
                                for c in CITY_CODE_LIEPIN:
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
                        logger.debug(f"猎聘解析单条失败: {e}")
                        continue

                await browser.close()

        except Exception as e:
            logger.warning(f"猎聘抓取失败: {e}")

        return jobs
