from .base import BaseScraper
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


class GuopinScraper(BaseScraper):
    source_name = "国聘"
    base_url = "https://www.iguopin.com"
    rate_limit_delay = 3.0

    async def scrape(self) -> list[dict]:
        jobs = []
        search_url = f"{self.base_url}/job?keyword={self.keyword}"

        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(search_url, timeout=60000, wait_until="networkidle")
                await page.wait_for_timeout(4000)

                cards = await page.query_selector_all("[class*='card']")
                body_text = await page.inner_text("body")
                print(f"[GUOPIN] url={page.url} cards={len(cards)} body_len={len(body_text)} body_preview={body_text[:300]}")

                for card in cards[:30]:
                    job_url = search_url
                    popup_url = None

                    try:
                        # Extract job detail URL by clicking .job-name and capturing popup
                        name_el = await card.query_selector(".job-name")
                        if name_el:
                            async with page.expect_popup(timeout=5000) as popup_info:
                                await name_el.click()
                            popup = await popup_info.value
                            popup_url = popup.url
                            await popup.close()
                            await page.wait_for_timeout(500)

                        text = (await card.inner_text()).strip()
                        if not text or len(text) < 15:
                            continue

                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if len(lines) < 2:
                            continue

                        title = lines[0]

                        # Location: look for line with 「...」
                        location = ""
                        city = self.city
                        for line in lines:
                            if line.startswith("「") and line.endswith("」"):
                                location = line.strip("「」")
                                for c in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "苏州", "西安", "重庆", "天津"]:
                                    if c in location:
                                        city = c
                                        break
                                break

                        # Salary/experience/education line
                        salary = ""
                        for line in lines:
                            if "面议" in line or "K" in line or "万" in line:
                                salary = line
                                break

                        # Company name: look for company indicators
                        company = ""
                        for line in lines:
                            if any(kw in line for kw in ["有限公司", "科技", "集团", "股份", "网络", "信息", "软件", "数据", "技术"]):
                                if not any(skip in line for skip in ["人", "最佳雇主", "已上市", "软件和信息技术", "专业技术"]):
                                    company = line
                                    break
                        if not company and len(lines) > 3:
                            for i, line in enumerate(lines):
                                if line == salary and i + 1 < len(lines):
                                    candidate = lines[i + 1]
                                    if "不限" not in candidate and len(candidate) >= 4:
                                        company = candidate
                                        break

                        # Extract description from remaining text
                        desc = self._extract_description(text, title, company or "", salary, "")

                        if title and company and len(company) >= 4:
                            company = self._clean_company(company)
                            salary_clean = self._clean_salary(salary)
                            if popup_url:
                                job_url = popup_url
                            jobs.append({
                                "title": title,
                                "company": company,
                                "city": city,
                                "salary": salary_clean,
                                "description": desc,
                                "requirements": "",
                                "location": location,
                                "source_url": job_url,
                                "posted_date": "",
                            })
                    except Exception as e:
                        logger.debug(f"国聘解析单条失败: {e}")
                        continue

                await browser.close()
        except Exception as e:
            logger.warning(f"国聘Playwright抓取失败: {e}")

        return jobs
