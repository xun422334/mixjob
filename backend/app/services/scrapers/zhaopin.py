import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)


class ZhaopinScraper(BaseScraper):
    source_name = "智联招聘"
    base_url = "https://sou.zhaopin.com"
    rate_limit_delay = 2.0

    async def scrape(self) -> list[dict]:
        jobs = []
        search_url = f"{self.base_url}/?jl={self.city}&kw={self.keyword}&p=1"

        try:
            headers = self._headers()
            headers["Referer"] = self.base_url

            async with httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(20.0),
                follow_redirects=True,
            ) as client:
                resp = await client.get(search_url)
                print(f"[ZHAOPIN] status={resp.status_code} url={resp.url} len={len(resp.text)} preview={resp.text[:300]}")

                if resp.status_code != 200:
                    raise Exception(f"智联招聘返回HTTP {resp.status_code}")

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = (
                    soup.select(".positionlist .job-list-box") or
                    soup.select(".joblist-box__item") or
                    soup.select("[class*='joblist'] > div")
                )
                print(f"[ZHAOPIN] cards={len(cards)}")

                for card in cards[:30]:
                    try:
                        title_el = card.select_one(".job-name, .job-title, [class*='job-name'], a[href*='job']")
                        company_el = card.select_one(".company-name, .complay-name, [class*='company']")
                        salary_el = card.select_one(".salary, .job-salary, [class*='salary']")
                        date_el = card.select_one(".time, [class*='time'], [class*='date'], .publish-time")
                        link_el = card.select_one("a[href*='jobdetail']")

                        text = card.get_text().strip()
                        title = title_el.get_text().strip() if title_el else ""
                        company = company_el.get_text().strip() if company_el else ""
                        salary = salary_el.get_text().strip() if salary_el else ""
                        posted_date = date_el.get_text().strip() if date_el else ""
                        job_url = ""
                        if link_el:
                            href = link_el.get("href", "")
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
                                "source_url": job_url or str(resp.url),
                                "posted_date": posted_date,
                            })
                    except Exception as e:
                        logger.debug(f"智联招聘解析单条失败: {e}")
                        continue

        except Exception as e:
            logger.warning(f"智联招聘抓取失败: {e}")

        return jobs
