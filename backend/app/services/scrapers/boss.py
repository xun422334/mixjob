import os
import json
import httpx
from bs4 import BeautifulSoup
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
        search_url = f"{self.base_url}/web/geek/jobs?query={self.keyword}&city={city_code}&page=1"

        if not os.path.exists(STATE_FILE):
            raise Exception('BOSS直聘未登录，请点击导航栏[登录招聘网站]按钮，选择BOSS直聘完成登录后再抓取')

        try:
            with open(STATE_FILE) as f:
                state = json.load(f)

            cookies = {}
            for c in state.get("cookies", []):
                cookies[c["name"]] = c["value"]

            headers = self._headers()
            headers["Referer"] = self.base_url

            async with httpx.AsyncClient(
                cookies=cookies,
                headers=headers,
                timeout=httpx.Timeout(20.0),
                follow_redirects=True,
            ) as client:
                resp = await client.get(search_url)
                print(f"[BOSS] status={resp.status_code} url={resp.url} len={len(resp.text)} preview={resp.text[:300]}")

                if resp.status_code != 200:
                    raise Exception(f"BOSS直聘返回HTTP {resp.status_code}")

                if any(kw in str(resp.url).lower() for kw in ["login", "register", "passport"]):
                    raise Exception("BOSS直聘登录状态已过期，请重新登录")

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(".job-card-box") or soup.select("[class*='job-card']")
                print(f"[BOSS] cards={len(cards)}")

                for card in cards[:30]:
                    try:
                        text = card.get_text().strip()
                        if not text or len(text) < 10:
                            continue

                        title_el = card.select_one(".job-name, .job-title")
                        company_el = card.select_one(".boss-name, .company-name")
                        salary_el = card.select_one(".job-salary, .salary")
                        area_el = card.select_one(".company-location, .job-area")
                        date_el = card.select_one(".job-time, [class*='time'], [class*='date'], .publish-time")
                        link_el = card.select_one("a[href*='job_detail']")

                        title = title_el.get_text().strip() if title_el else ""
                        company = company_el.get_text().strip() if company_el else ""
                        salary = salary_el.get_text().strip() if salary_el else ""
                        area = area_el.get_text().strip() if area_el else ""
                        posted_date = date_el.get_text().strip() if date_el else ""
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
                                    if not company:
                                        for i, line in enumerate(lines):
                                            if "·" in line and len(line) > 4:
                                                if i > 0 and len(lines[i-1]) >= 4:
                                                    company = lines[i-1]
                                                    break

                        if title and company:
                            title = title.split("\n")[0].strip()
                            company = self._clean_company(company)
                            salary = self._clean_salary(salary)

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
                                "source_url": job_url or str(resp.url),
                                "posted_date": posted_date,
                            })
                    except Exception as e:
                        logger.debug(f"BOSS直聘解析单条失败: {e}")
                        continue

        except Exception as e:
            logger.warning(f"BOSS直聘抓取失败: {e}")

        return jobs
