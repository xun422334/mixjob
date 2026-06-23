from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..models.database import get_db, JobListing

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Map English source keys to Chinese display names (as stored in DB)
SOURCE_KEY_TO_NAME = {
    "boss": "BOSS直聘",
    "liepin": "猎聘",
    "zhaopin": "智联招聘",
    "guopin": "国聘",
}


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, description="岗位名称")
    company: str = ""
    description: str = ""
    requirements: str = ""
    source: str = "manual"
    source_url: str = ""
    salary: str = ""
    city: str = ""
    location: str = ""
    posted_date: str = ""


class ScrapeRequest(BaseModel):
    city: str
    keyword: str
    sources: Optional[List[str]] = None


@router.post("")
async def create_job(job: JobCreate, db: Session = Depends(get_db)):
    db_job = JobListing(
        title=job.title,
        company=job.company,
        description=job.description,
        requirements=job.requirements,
        source=job.source,
        source_url=job.source_url,
        salary=job.salary,
        city=job.city,
        location=job.location,
        posted_date=job.posted_date,
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return {"job": _job_to_dict(db_job)}


@router.get("")
async def list_jobs(
    city: str = "",
    keyword: str = "",
    source: str = "",
    db: Session = Depends(get_db),
):
    from sqlalchemy import or_
    query = db.query(JobListing)
    if city:
        query = query.filter(JobListing.city == city)
    if source:
        source_name = SOURCE_KEY_TO_NAME.get(source, source)
        query = query.filter(JobListing.source == source_name)
    if keyword:
        keywords = [k.strip() for k in keyword.split('/') if k.strip()]
        if keywords:
            filters = []
            for kw in keywords:
                like = f"%{kw}%"
                filters.append(JobListing.title.like(like))
                filters.append(JobListing.description.like(like))
            query = query.filter(or_(*filters))
    jobs = query.order_by(JobListing.created_at.desc()).limit(100).all()
    return {"jobs": [_job_to_dict(j) for j in jobs], "city": city, "keyword": keyword}


@router.post("/scrape")
async def scrape_jobs_api(req: ScrapeRequest, db: Session = Depends(get_db)):
    import traceback
    from ..services.job_scraper import scrape_jobs as run_scrape, acquire_scrape_lock, release_scrape_lock

    if not acquire_scrape_lock():
        return {
            "error": "已有抓取任务正在进行中，请等待完成后重试",
            "total_found": 0, "after_dedup": 0, "new_added": 0,
            "duplicates_skipped": 0, "per_source": {},
        }

    try:
        keywords = [k.strip() for k in req.keyword.split('/') if k.strip()]
        if not keywords:
            keywords = [req.keyword]

        all_results = []
        for kw in keywords:
            try:
                result = await run_scrape(
                    city=req.city,
                    keyword=kw,
                    sources=req.sources,
                    db=db,
                )
            except Exception as e:
                return {"error": str(e), "traceback": traceback.format_exc()}
            all_results.append(result)
    finally:
        release_scrape_lock()

    # Merge results from multiple keywords
    merged_new = sum(r["new_added"] for r in all_results)
    merged_dup = sum(r["duplicates_skipped"] for r in all_results)
    merged_total = sum(r["total_found"] for r in all_results)
    merged_per_source = {}
    for r in all_results:
        for src_key, src_data in r["per_source"].items():
            if src_key not in merged_per_source:
                merged_per_source[src_key] = {"status": "ok", "count": 0}
            if src_data["status"] == "ok":
                merged_per_source[src_key]["count"] += src_data["count"]
            elif src_data["status"] == "error":
                if merged_per_source[src_key]["status"] == "ok" and merged_per_source[src_key]["count"] == 0:
                    merged_per_source[src_key] = src_data

    return {
        "city": req.city,
        "keyword": req.keyword,
        "total_found": merged_total,
        "after_dedup": 0,
        "new_added": merged_new,
        "duplicates_skipped": merged_dup,
        "per_source": merged_per_source,
    }


@router.post("/ocr")
async def ocr_job_image(image_data: dict, db: Session = Depends(get_db)):
    """OCR: extract job info from an image using DeepSeek vision"""
    import base64
    from ..services.ai_service import chat as ai_chat

    image_url = image_data.get("image_url", "")
    if not image_url:
        raise HTTPException(status_code=400, detail="缺少图片数据")

    prompt = """你是一个招聘信息识别助手。请从这张图片中识别岗位信息，返回纯JSON：

{
  "title": "岗位名称",
  "company": "公司名称",
  "description": "岗位描述",
  "requirements": "任职要求",
  "salary": "薪资范围",
  "city": "工作城市",
  "location": "具体地点",
  "posted_date": "发布时间"
}

规则：
1. 只返回JSON，不要有其他文字
2. 识别不到的字段填空字符串""
3. 尽量完整地提取所有可见信息"""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }
    ]

    try:
        import httpx
        from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": "deepseek-chat", "messages": messages, "temperature": 0.3},
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]

        import json
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
    except Exception as e:
        import traceback
        print(f"[OCR] failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"图片识别失败: {str(e)}")


@router.post("/search-on-platform")
async def search_on_platform(req: dict, db: Session = Depends(get_db)):
    """Search for a specific job on a recruitment platform"""
    from ..services.scrapers import SCRAPER_REGISTRY
    import asyncio

    source = req.get("source", "")
    job_title = req.get("job_title", "")
    company = req.get("company", "")
    city = req.get("city", "")

    if not source or not job_title:
        raise HTTPException(status_code=400, detail="缺少必要参数")

    scraper_cls = SCRAPER_REGISTRY.get(source)
    if not scraper_cls:
        raise HTTPException(status_code=400, detail=f"不支持的来源: {source}")

    scraper = scraper_cls(city=city, keyword=f"{job_title} {company}".strip())
    try:
        raw_jobs = await scraper.scrape()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

    # Filter by job title similarity (simple contains match)
    matched = []
    for j in raw_jobs:
        if job_title.lower() in j.get("title", "").lower() or (
            company and company.lower() in j.get("company", "").lower()
        ):
            matched.append(j)

    # Auto-insert top match if found
    inserted = None
    if matched:
        best = matched[0]
        existing = (
            db.query(JobListing)
            .filter(
                JobListing.title == best["title"],
                JobListing.company == best["company"],
                JobListing.city == best.get("city", city),
            )
            .first()
        )
        if not existing:
            job = JobListing(
                title=best["title"],
                company=best["company"],
                description=best.get("description", ""),
                requirements=best.get("requirements", ""),
                source=source,
                source_url=best.get("source_url", ""),
                salary=best.get("salary", ""),
                city=best.get("city", city),
                location=best.get("location", ""),
                posted_date=best.get("posted_date", ""),
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            inserted = _job_to_dict(job)

    return {
        "source": source,
        "found": len(matched),
        "matched_jobs": matched[:10],
        "inserted": inserted,
    }


@router.get("/{job_id}")
async def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return {"job": _job_to_dict(job)}


@router.post("/{job_id}/fetch-detail")
async def fetch_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Fetch job detail page from platform and extract description & requirements."""
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")

    # Detect if source_url is a search page (not a specific job detail page)
    is_search_url = False
    if job.source_url:
        search_indicators = ["keyword=", "query=", "?kw=", "?key=", "?jl=", "/search?", "/zhaopin/", "/web/geek/job"]
        is_search_url = any(ind in job.source_url for ind in search_indicators)

    if not job.source_url or job.source == "manual" or is_search_url:
        # Try to search for the job on the platform
        detail, actual_url = await _search_and_fetch_detail(job, db)
    else:
        detail, actual_url = await _fetch_detail_page(job.source_url, job.source, job.title, job.company)

    if detail.get("description"):
        job.description = detail["description"]
    if detail.get("requirements"):
        job.requirements = detail["requirements"]
    if actual_url and actual_url != job.source_url:
        job.source_url = actual_url
    db.commit()
    db.refresh(job)
    return {"job": _job_to_dict(job)}


async def _fetch_detail_page(source_url: str, source: str, title: str, company: str) -> tuple:
    """Navigate to job detail page and extract content. Returns (result, actual_url)."""
    from playwright.async_api import async_playwright
    import os

    selectors = _get_detail_selectors(source)
    result = {"description": "", "requirements": ""}
    actual_url = source_url

    # Load BOSS login state if available
    storage_state = None
    if source == "BOSS直聘":
        state_file = os.path.join(os.path.dirname(__file__), "..", "..", "browser_states", "boss_state.json")
        if os.path.exists(state_file):
            storage_state = state_file

    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            if storage_state:
                context = await browser.new_context(
                    storage_state=storage_state,
                    viewport={"width": 1280, "height": 800},
                    locale="zh-CN",
                )
                page = await context.new_page()
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)
            else:
                page = await browser.new_page()

            # BOSS is an SPA - use networkidle to wait for React rendering
            wait_until = "networkidle" if source == "BOSS直聘" else "domcontentloaded"
            await page.goto(source_url, timeout=30000, wait_until=wait_until)
            await page.wait_for_timeout(5000 if source == "BOSS直聘" else 3000)
            actual_url = page.url

            # Check if BOSS redirected to login
            if source == "BOSS直聘" and any(kw in actual_url.lower() for kw in ["login", "register", "passport"]):
                print(f"[fetch_detail] BOSS redirected to login page")
                result["description"] = "（BOSS直聘登录状态已过期，请重新登录后查看详情）"
                await browser.close()
                return result, actual_url

            text = await page.inner_text("body")
            print(f"[fetch_detail] {source} page text len: {len(text)}")

            for desc_sel in selectors.get("description", []):
                el = await page.query_selector(desc_sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if len(t) > 20:
                        result["description"] = t
                        break

            for req_sel in selectors.get("requirements", []):
                el = await page.query_selector(req_sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if len(t) > 10:
                        result["requirements"] = t
                        break

            # Fallback: extract large text blocks that look like descriptions
            if not result["description"] and len(text) > 100:
                result["description"] = _extract_desc_from_text(text, title, company)

            await browser.close()
    except Exception as e:
        print(f"[fetch_detail] error: {e}")

    return result, actual_url


async def _search_and_fetch_detail(job, db) -> tuple:
    """Search the platform for this job and navigate to its detail page. Returns (result, actual_url)."""
    import urllib.parse

    search_urls = {
        "BOSS直聘": f"https://www.zhipin.com/web/geek/jobs?query={urllib.parse.quote(job.title)}&city=101010100",
        "猎聘": f"https://www.liepin.com/zhaopin/?key={urllib.parse.quote(job.title)}",
        "智联招聘": f"https://sou.zhaopin.com/?kw={urllib.parse.quote(job.title)}",
        "国聘": f"https://www.iguopin.com/job?keyword={urllib.parse.quote(job.title)}",
    }
    source_name = job.source
    search_url = search_urls.get(source_name, "")
    actual_url = ""
    if not search_url:
        return {"description": "", "requirements": ""}, actual_url

    from playwright.async_api import async_playwright
    selectors = _get_detail_selectors(source_name)
    result = {"description": "", "requirements": ""}

    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()
            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

            # Find and click the first matching job link
            link_selectors = [
                f"a:has-text('{job.title[:8]}')",
                "a[href*='job_detail']",
                f"a[href*='/job/']",
                "a[href*='jobdetail']",
                "[class*='job-name'] a[href]",
                "[class*='job-title'] a[href]",
            ]

            # For 国聘, use popup-based navigation since cards have no direct job links
            if source_name == "国聘":
                name_el = await page.query_selector(".job-name")
                if name_el:
                    async with page.expect_popup(timeout=5000) as popup_info:
                        await name_el.click()
                    popup = await popup_info.value
                    target = popup.url
                    await popup.close()
                    await page.goto(target, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                    actual_url = page.url
                    for desc_sel in selectors.get("description", []):
                        el = await page.query_selector(desc_sel)
                        if el:
                            t = (await el.inner_text()).strip()
                            if len(t) > 20:
                                result["description"] = t
                                break
                    for req_sel in selectors.get("requirements", []):
                        el = await page.query_selector(req_sel)
                        if el:
                            t = (await el.inner_text()).strip()
                            if len(t) > 10:
                                result["requirements"] = t
                                break
            else:
                for link_sel in link_selectors:
                    link = await page.query_selector(link_sel)
                    if link:
                        href = await link.get_attribute("href")
                        if href:
                            target = href if href.startswith("http") else f"{selectors.get('base_url', '')}{href}"
                            print(f"[search_fetch] navigating to: {target}")
                            await page.goto(target, timeout=30000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(3000)
                            actual_url = page.url

                            for desc_sel in selectors.get("description", []):
                                el = await page.query_selector(desc_sel)
                                if el:
                                    t = (await el.inner_text()).strip()
                                    if len(t) > 20:
                                        result["description"] = t
                                        break
                            for req_sel in selectors.get("requirements", []):
                                el = await page.query_selector(req_sel)
                                if el:
                                    t = (await el.inner_text()).strip()
                                    if len(t) > 10:
                                        result["requirements"] = t
                                        break
                            break

            await browser.close()
    except Exception as e:
        print(f"[search_fetch] error: {e}")

    return result, actual_url


def _get_detail_selectors(source: str) -> dict:
    """Get platform-specific selectors for job detail pages."""
    selectors_map = {
        "猎聘": {
            "description": [".job-detail-bottom .content-word", ".job-main-content", "[class*='job-detail'] [class*='content']", "[class*='detail'] [class*='content']", ".content-word"],
            "requirements": [".job-qualifications", ".job-detail-bottom .job-qualifications", "[class*='qualification']", "[class*='require']"],
            "base_url": "https://www.liepin.com",
        },
        "智联招聘": {
            "description": [".responsibility", ".job-detail-description", "[class*='responsibility']", "[class*='detail'] [class*='content']", ".describtion"],
            "requirements": [".requirement", ".job-detail-requirement", "[class*='require']", "[class*='qualification']"],
            "base_url": "https://sou.zhaopin.com",
        },
        "BOSS直聘": {
            "description": [".job-sec-text", ".job-detail", ".detail-text", "[class*='job-sec']", "[class*='job-detail'] [class*='text']", "[class*='detail-content']", "[class*='desc']", ".job-main"],
            "requirements": [".job-sec-text", ".job-detail", "[class*='require']", "[class*='qualification']", "[class*='job-sec']"],
            "base_url": "https://www.zhipin.com",
        },
        "国聘": {
            "description": [".job-detail-desc", ".job-info", "[class*='job-desc']", "[class*='job-info']", "[class*='detail'] [class*='content']"],
            "requirements": [".job-requirement", "[class*='require']", "[class*='condition']", "[class*='qualification']"],
            "base_url": "https://www.iguopin.com",
        },
    }
    return selectors_map.get(source, {"description": ["[class*='detail']"], "requirements": ["[class*='require']"], "base_url": ""})


def _extract_desc_from_text(text: str, title: str, company: str) -> str:
    """Extract description-relevant paragraphs from full page text."""
    lines = text.split("\n")
    relevant = []
    capture = False
    desc_keywords = ["岗位职责", "职位描述", "工作内容", "岗位描述", "职责描述", "任职要求", "任职资格", "职位要求", "岗位要求"]
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(kw in line for kw in desc_keywords):
            capture = True
            relevant.append(line)
            continue
        if capture and len(line) > 10:
            relevant.append(line)
            if len(relevant) > 20:
                break
    return "\n".join(relevant) if relevant else ""


def _job_to_dict(j: JobListing) -> dict:
    return {
        "id": j.id,
        "title": j.title,
        "company": j.company,
        "description": j.description,
        "requirements": j.requirements,
        "source": j.source,
        "source_url": j.source_url,
        "salary": j.salary,
        "city": j.city,
        "location": j.location,
        "posted_date": j.posted_date,
    }
