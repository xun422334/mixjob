import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper
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
    rate_limit_delay = 2.0

    async def scrape(self) -> list[dict]:
        jobs = []
        city_code = CITY_CODE_LIEPIN.get(self.city, "010")
        search_url = f"{self.base_url}/zhaopin/?city={city_code}&key={self.keyword}"

        try:
            headers = self._headers()
            headers["Referer"] = self.base_url

            async with httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(20.0),
                follow_redirects=True,
            ) as client:
                resp = await client.get(search_url)
                print(f"[LIEPIN] status={resp.status_code} url={resp.url} len={len(resp.text)} preview={resp.text[:300]}")

                if resp.status_code != 200:
                    raise Exception(f"猎聘返回HTTP {resp.status_code}")

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = (
                    soup.select("[class*='job-list-item']") or
                    soup.select(".job-list-box [class*='job']") or
                    soup.select(".job-list-box > div") or
                    soup.select(".job-list-box > li") or
                    soup.select("[class*='job-card']")
                )
                print(f"[LIEPIN] cards={len(cards)}")

                for card in cards[:30]:
                    try:
                        text = card.get_text().strip()
                        if not text or len(text) < 10:
                            continue

                        title_el = card.select_one(".job-title, [class*='job-title'], h3, .title")
                        company_el = card.select_one(".company-name, [class*='company-name'], .company")
                        salary_el = card.select_one(".job-salary, [class*='salary'], .text-warning")
                        date_el = card.select_one(".time, [class*='time'], [class*='date'], .publish-time")
                        link_el = card.select_one("a[href*='/job/']")

                        title = title_el.get_text().strip() if title_el else ""
                        company = company_el.get_text().strip() if company_el else ""
                        salary = salary_el.get_text().strip() if salary_el else ""
                        posted_date = date_el.get_text().strip() if date_el else ""
                        job_url = ""
                        if link_el:
                            href = link_el.get("href", "")
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

                        if title and company and len(company) >= 4 and not company.endswith(("区", "县", "市")):
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
                        logger.debug(f"猎聘解析单条失败: {e}")
                        continue

        except Exception as e:
            logger.warning(f"猎聘抓取失败: {e}")

        return jobs
