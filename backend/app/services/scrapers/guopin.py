import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)


class GuopinScraper(BaseScraper):
    source_name = "国聘"
    base_url = "https://www.iguopin.com"
    rate_limit_delay = 2.0

    async def scrape(self) -> list[dict]:
        jobs = []
        search_url = f"{self.base_url}/job?keyword={self.keyword}"

        try:
            headers = self._headers()
            headers["Referer"] = self.base_url

            async with httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(20.0),
                follow_redirects=True,
            ) as client:
                resp = await client.get(search_url)
                print(f"[GUOPIN] status={resp.status_code} url={resp.url} len={len(resp.text)} preview={resp.text[:300]}")

                if resp.status_code != 200:
                    raise Exception(f"国聘返回HTTP {resp.status_code}")

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("[class*='card']")
                print(f"[GUOPIN] cards={len(cards)}")

                for card in cards[:30]:
                    try:
                        text = card.get_text().strip()
                        if not text or len(text) < 15:
                            continue

                        lines = [l.strip() for l in text.split("\n") if l.strip()]
                        if len(lines) < 2:
                            continue

                        title = lines[0]

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

                        salary = ""
                        for line in lines:
                            if "面议" in line or "K" in line or "万" in line:
                                salary = line
                                break

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

                        link_el = card.select_one("a[href]")
                        job_url = str(resp.url)
                        if link_el:
                            href = link_el.get("href", "")
                            if href:
                                job_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        desc = self._extract_description(text, title, company or "", salary, "")

                        if title and company and len(company) >= 4:
                            company = self._clean_company(company)
                            salary_clean = self._clean_salary(salary)
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

        except Exception as e:
            logger.warning(f"国聘抓取失败: {e}")

        return jobs
