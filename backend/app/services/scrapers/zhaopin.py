from .base import BaseScraper
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


class ZhaopinScraper(BaseScraper):
    source_name = "智联招聘"
    base_url = "https://sou.zhaopin.com"
    rate_limit_delay = 3.0

    async def scrape(self) -> list[dict]:
        jobs = []
        search_url = f"{self.base_url}/?jl={self.city}&kw={self.keyword}&p=1"

        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                page = await browser.new_page()
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                cards = await page.query_selector_all(".positionlist .job-list-box, .joblist-box__item, [class*='joblist'] > div")
                body_text = await page.inner_text("body")
                print(f"[ZHAOPIN] url={page.url} cards={len(cards)} body_len={len(body_text)} body_preview={body_text[:300]}")

                for card in cards[:30]:
                    try:
                        title_el = await card.query_selector(".job-name, .job-title, [class*='job-name'], a[href*='job']")
                        company_el = await card.query_selector(".company-name, .complay-name, [class*='company']")
                        salary_el = await card.query_selector(".salary, .job-salary, [class*='salary']")
                        date_el = await card.query_selector(".time, [class*='time'], [class*='date'], .publish-time")
                        link_el = await card.query_selector("a[href*='jobdetail']")

                        text = (await card.inner_text()).strip()
                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        salary = (await salary_el.inner_text()).strip() if salary_el else ""
                        posted_date = (await date_el.inner_text()).strip() if date_el else ""
                        job_url = ""
                        if link_el:
                            href = await link_el.get_attribute("href")
                            if href:
                                job_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        if title and company:
                            company = self._clean_company(company)
                            salary = self._clean_salary(salary)
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
                        logger.debug(f"智联招聘解析单条失败: {e}")
                        continue

                await browser.close()
        except Exception as e:
            logger.warning(f"智联招聘Playwright抓取失败: {e}")

        return jobs
