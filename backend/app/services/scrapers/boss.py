import os
import json
import asyncio
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

    async def scrape(self, browser=None) -> list[dict]:
        jobs = []
        city_code = CITY_CODE_MAP.get(self.city, "101010100")
        search_url = f"{self.base_url}/web/geek/job?query={self.keyword}&city={city_code}"

        if not os.path.exists(STATE_FILE):
            logger.warning("BOSS直聘未登录，请先点击导航栏[登录招聘网站]完成登录后再抓取")
            return jobs

        own_browser = browser is None
        try:
            if own_browser:
                p = await async_playwright().__aenter__()
                browser = await p.firefox.launch(headless=True)

            context_kwargs = {"viewport": {"width": 1280, "height": 800}}
            if os.path.exists(STATE_FILE):
                context_kwargs["storage_state"] = STATE_FILE

            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)

            api_data_future = asyncio.get_event_loop().create_future()

            async def on_response(response):
                if api_data_future.done():
                    return
                if "joblist.json" not in response.url:
                    return
                try:
                    body = await response.text()
                    data = json.loads(body)
                    if data.get("code") == 0:
                        api_data_future.set_result(data)
                except Exception:
                    pass

            page.on("response", on_response)

            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")

            try:
                data = await asyncio.wait_for(api_data_future, timeout=20)
            except asyncio.TimeoutError:
                logger.warning("BOSS直聘搜索API未返回数据（超时）")
                await context.close()
                if own_browser:
                    await browser.close()
                return jobs

            await context.close()

            zp = data.get("zpData", {})
            job_list = zp.get("jobList", [])
            logger.info(f"[BOSS] Found {len(job_list)} jobs from API (total: {zp.get('resCount', 0)})")

            for job in job_list:
                try:
                    title = job.get("jobName", "").strip()
                    company = job.get("brandName", "").strip()
                    salary = job.get("salaryDesc", "").strip()
                    city = job.get("cityName", "") or self.city
                    area = job.get("areaDistrict", "")
                    experience = job.get("jobExperience", "")
                    degree = job.get("jobDegree", "")
                    skills = job.get("skills", [])
                    boss_name = job.get("bossName", "")
                    boss_title = job.get("bossTitle", "")
                    encrypt_id = job.get("encryptId", "")

                    if not title or not company:
                        continue

                    company = self._clean_company(company)
                    salary = self._clean_salary(salary)

                    desc_parts = []
                    if experience:
                        desc_parts.append(f"经验: {experience}")
                    if degree:
                        desc_parts.append(f"学历: {degree}")
                    if boss_name:
                        desc_parts.append(f"HR: {boss_name}({boss_title})" if boss_title else f"HR: {boss_name}")

                    source_url = ""
                    if encrypt_id:
                        source_url = f"{self.base_url}/job_detail/{encrypt_id}.html"

                    jobs.append({
                        "title": title,
                        "company": company,
                        "city": city,
                        "salary": salary,
                        "description": " | ".join(desc_parts),
                        "requirements": ", ".join(skills) if skills else "",
                        "location": area,
                        "source_url": source_url or str(search_url),
                        "posted_date": "",
                    })
                except Exception as e:
                    logger.debug(f"BOSS直聘解析单条失败: {e}")
                    continue

        except Exception as e:
            logger.warning(f"BOSS直聘抓取失败: {e}")
        finally:
            if own_browser and browser:
                await browser.close()

        return jobs
