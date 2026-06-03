import os
from .base import BaseScraper
from playwright.async_api import async_playwright
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
    rate_limit_delay = 3.0

    async def scrape(self) -> list[dict]:
        jobs = []
        city_code = CITY_CODE_MAP.get(self.city, "101010100")
        search_url = f"{self.base_url}/web/geek/jobs?query={self.keyword}&city={city_code}&page=1"

        has_login = os.path.exists(STATE_FILE)
        if not has_login:
            raise Exception('BOSS直聘未登录，请点击导航栏[登录招聘网站]按钮，选择BOSS直聘完成登录后再抓取')

        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                context = await browser.new_context(
                    storage_state=STATE_FILE,
                    viewport={"width": 1280, "height": 800},
                    locale="zh-CN",
                )
                page = await context.new_page()

                # Anti-detection
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                # Visit home page first to establish session
                await page.goto(self.base_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                # Navigate to search page
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)

                # Check if redirected to login/passport
                if any(kw in page.url.lower() for kw in ["login", "register", "passport"]):
                    await browser.close()
                    raise Exception("BOSS直聘登录状态已过期，请重新登录")

                cards = await page.query_selector_all(".job-card-box")

                for card in cards[:30]:
                    try:
                        text = (await card.inner_text()).strip()
                        if not text or len(text) < 10:
                            continue

                        title_el = await card.query_selector(".job-name, .job-title")
                        company_el = await card.query_selector(".boss-name, .company-name")
                        salary_el = await card.query_selector(".job-salary, .salary")
                        area_el = await card.query_selector(".company-location, .job-area")
                        date_el = await card.query_selector(".job-time, [class*='time'], [class*='date'], .publish-time")
                        link_el = await card.query_selector("a[href*='job_detail']")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        salary = (await salary_el.inner_text()).strip() if salary_el else ""
                        area = (await area_el.inner_text()).strip() if area_el else ""
                        posted_date = (await date_el.inner_text()).strip() if date_el else ""
                        job_url = ""
                        if link_el:
                            href = await link_el.get_attribute("href")
                            if href:
                                job_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        # Fallback: parse from full text (BOSS format: title, salary, exp, edu, company, location)
                        if not title or not company:
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            if lines:
                                if not title:
                                    title = lines[0]
                                if not company and len(lines) > 1:
                                    # BOSS format: company is typically line before the last (location)
                                    for line in lines:
                                        if any(kw in line for kw in ["有限公司", "科技", "集团", "网络", "信息", "软件"]):
                                            company = line
                                            break
                                    if not company:
                                        # Use the line before the location (which has · separator)
                                        for i, line in enumerate(lines):
                                            if "·" in line and len(line) > 4:
                                                if i > 0 and len(lines[i-1]) >= 4:
                                                    company = lines[i-1]
                                                    break

                        if title and company:
                            # Clean title: remove embedded salary/newlines
                            title = title.split("\n")[0].strip()
                            company = self._clean_company(company)
                            salary = self._clean_salary(salary)

                            # Extract city from area
                            city = self.city
                            if area:
                                for c in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "苏州", "西安"]:
                                    if c in area:
                                        city = c
                                        break

                            desc = self._extract_description(text, title, company, salary, posted_date)
                            jobs.append({
                                "title": title,
                                "company": company,
                                "city": city,
                                "salary": salary,
                                "description": desc,
                                "requirements": "",
                                "location": area,
                                "source_url": job_url or search_url,
                                "posted_date": posted_date,
                            })
                    except Exception as e:
                        logger.debug(f"BOSS直聘解析单条失败: {e}")
                        continue

                await browser.close()
        except Exception as e:
            logger.warning(f"BOSS直聘Playwright抓取失败: {e}")

        return jobs
