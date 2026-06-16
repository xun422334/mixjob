import os
import json
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)

CITY_CODE_MAP = {
    "北京": "101010100", "上海": "101020100", "广州": "101280100",
    "深圳": "101280600", "杭州": "101210100", "成都": "101270100",
    "武汉": "101200100", "南京": "101190100", "苏州": "101190400",
    "西安": "101110100",
}

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "browser_states", "boss_state.json")


class BossZhipinScraper(BaseScraper):
    source_name = "BOSS直聘"
    base_url = "https://www.zhipin.com"
    rate_limit_delay = 2.0

    async def scrape(self) -> list[dict]:
        jobs = []
        city_code = CITY_CODE_MAP.get(self.city, "101010100")
        search_url = f"{self.base_url}/web/geek/job?query={self.keyword}&city={city_code}"

        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                context_kwargs = {"viewport": {"width": 1280, "height": 800}}

                if os.path.exists(STATE_FILE):
                    context_kwargs["storage_state"] = STATE_FILE
                else:
                    raise Exception("BOSS直聘未登录，请先点击导航栏[登录招聘网站]完成登录后再抓取")

                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()

                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                current_url = page.url
                if any(kw in current_url.lower() for kw in ["login", "register", "passport"]):
                    await browser.close()
                    raise Exception("BOSS直聘登录状态已过期，请重新登录")

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".job-card-wrap, .job-card-box, li[class*='job-card']")
                logger.info(f"[BOSS] Found {len(cards)} cards")

                for card in cards[:30]:
                    try:
                        text = card.get_text().strip()
                        if not text or len(text) < 10:
                            continue

                        title_el = card.select_one(".job-name, [class*='job-name'], .job-title, [class*='job-title']")
                        company_el = card.select_one(".company-name, [class*='company-name']")
                        salary_el = card.select_one(".salary, [class*='salary'], .red")
                        area_el = card.select_one(".job-area, [class*='job-area'], .area")
                        link_el = card.select_one("a[href*='job_detail']")

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
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            if lines:
                                if not title:
                                    title = lines[0]
                                if not company:
                                    for line in lines:
                                        if any(kw in line for kw in ["有限公司", "科技", "集团", "网络", "信息", "软件"]):
                                            company = line
                                            break

                        if title and company:
                            title = title.split("\n")[0].strip()
                            company = self._clean_company(company)
                            salary = self._clean_salary(salary)

                            city = self.city
                            if area:
                                for c in CITY_CODE_MAP:
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
                                "source_url": job_url or str(current_url),
                                "posted_date": "",
                            })
                    except Exception as e:
                        logger.debug(f"BOSS直聘解析单条失败: {e}")
                        continue

                await browser.close()

        except Exception as e:
            logger.warning(f"BOSS直聘抓取失败: {e}")

        return jobs
