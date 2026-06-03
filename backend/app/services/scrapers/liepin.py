from .base import BaseScraper
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

CITY_CODE_LIEPIN = {
    "北京": "010", "上海": "020", "广州": "050", "深圳": "060",
    "杭州": "080", "成都": "120", "武汉": "160", "南京": "040",
    "苏州": "035", "西安": "210",
}


class LiepinScraper(BaseScraper):
    source_name = "猎聘"
    base_url = "https://www.liepin.com"
    rate_limit_delay = 3.0

    async def scrape(self) -> list[dict]:
        jobs = []
        city_code = CITY_CODE_LIEPIN.get(self.city, "010")
        search_url = f"{self.base_url}/zhaopin/?city={city_code}&key={self.keyword}"

        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                page = await browser.new_page()
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)

                # 猎聘的岗位在 .job-list-box 内，每个岗位是一个包含 .job-title 等信息的元素
                cards = await page.query_selector_all("[class*='job-list-item'], .job-list-box [class*='job'], .job-list-box > div, .job-list-box > li")
                if not cards:
                    cards = await page.query_selector_all("[class*='job-card']")

                for card in cards[:30]:
                    try:
                        text = (await card.inner_text()).strip()
                        if not text or len(text) < 10:
                            continue

                        title_el = await card.query_selector(".job-title, [class*='job-title'], h3, .title")
                        company_el = await card.query_selector(".company-name, [class*='company-name'], .company")
                        salary_el = await card.query_selector(".job-salary, [class*='salary'], .text-warning")
                        date_el = await card.query_selector(".time, [class*='time'], [class*='date'], .publish-time")
                        link_el = await card.query_selector("a[href*='/job/']")

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        salary = (await salary_el.inner_text()).strip() if salary_el else ""
                        posted_date = (await date_el.inner_text()).strip() if date_el else ""
                        job_url = ""
                        if link_el:
                            href = await link_el.get_attribute("href")
                            if href:
                                job_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        if not title or not company:
                            lines = [l.strip() for l in text.split("\n") if l.strip()]
                            if len(lines) >= 2:
                                if not title:
                                    title = lines[0]
                                if not company:
                                    for line in lines:
                                        if any(kw in line for kw in ["有限公司", "科技", "集团", "股份", "网络", "信息", "软件", "数据", "技术"]):
                                            if not any(skip in line for skip in ["人", "最佳雇主", "已上市"]):
                                                company = line
                                                break

                        # Only accept if we have both and company looks reasonable
                        if title and company and len(company) >= 4 and not company.endswith(("区", "县", "市")):
                            company = self._clean_company(company)
                            salary = self._clean_salary(salary)
                            # Extract description from remaining text (not title/company/salary)
                            desc = self._extract_description(text, title, company, salary, posted_date)
                            jobs.append({
                                "title": title,
                                "company": company,
                                "city": self.city,
                                "salary": salary,
                                "description": desc,
                                "requirements": "",
                                "location": "",
                                "source_url": job_url or search_url,
                                "posted_date": posted_date,
                            })
                    except Exception as e:
                        logger.debug(f"猎聘解析单条失败: {e}")
                        continue

                await browser.close()
        except Exception as e:
            logger.warning(f"猎聘Playwright抓取失败: {e}")

        return jobs
