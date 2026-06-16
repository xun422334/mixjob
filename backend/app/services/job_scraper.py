import asyncio
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright
from ..models.database import JobListing
from .scrapers import SCRAPER_REGISTRY
from .scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


async def scrape_jobs(
    city: str,
    keyword: str,
    sources: Optional[List[str]] = None,
    db: Optional[Session] = None,
) -> dict:
    if sources is None:
        sources = list(SCRAPER_REGISTRY.keys())

    results_list = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)

        for src_key in sources:
            scraper_cls = SCRAPER_REGISTRY.get(src_key)
            if scraper_cls is None:
                continue
            scraper = scraper_cls(city=city, keyword=keyword)
            delay = scraper.rate_limit_delay
            results_list.append(await _run_one(src_key, scraper, browser, delay=delay))

        await browser.close()

    # 2. Collect per-source results
    per_source = {}
    all_raw_jobs = []
    for item in results_list:
        if isinstance(item, Exception):
            continue
        src_key, result = item
        if isinstance(result, Exception):
            per_source[src_key] = {"status": "error", "count": 0, "error": str(result)}
        else:
            per_source[src_key] = {"status": "ok", "count": len(result)}
            all_raw_jobs.extend(result)

    # 3. Dedup within the batch
    seen_keys = set()
    unique_jobs = []
    for job in all_raw_jobs:
        key = BaseScraper.build_dedup_key(
            job["title"], job["company"], job.get("city", city)
        )
        if key not in seen_keys:
            seen_keys.add(key)
            unique_jobs.append(job)

    # 4. Dedup against DB and insert
    new_count = 0
    dup_count = 0
    if db is not None:
        for job in unique_jobs:
            existing = (
                db.query(JobListing)
                .filter(
                    JobListing.title == job["title"],
                    JobListing.company == job["company"],
                    JobListing.city == job.get("city", city),
                )
                .first()
            )
            if existing:
                dup_count += 1
                continue
            db.add(JobListing(
                title=job["title"],
                company=job["company"],
                description=job.get("description", ""),
                requirements=job.get("requirements", ""),
                source=job.get("source", ""),
                source_url=job.get("source_url", ""),
                salary=job.get("salary", ""),
                city=job.get("city", city),
                location=job.get("location", ""),
                posted_date=job.get("posted_date", ""),
            ))
            new_count += 1
        db.commit()

    return {
        "city": city,
        "keyword": keyword,
        "total_found": len(all_raw_jobs),
        "after_dedup": len(unique_jobs),
        "new_added": new_count,
        "duplicates_skipped": dup_count,
        "per_source": per_source,
    }


async def _run_one(src_key: str, scraper, browser, delay: float = 0):
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        logger.info(f"[{src_key}] Starting scrape for keyword={scraper.keyword}...")
        result = await asyncio.wait_for(scraper.scrape(browser=browser), timeout=120)
        for job in result:
            job["source"] = scraper.source_name
        logger.info(f"[{src_key}] Done: {len(result)} jobs")
        return (src_key, result)
    except asyncio.TimeoutError:
        logger.warning(f"[{src_key}] Timed out after 90s")
        return (src_key, Exception("抓取超时"))
    except Exception as e:
        logger.warning(f"[{src_key}] Failed: {e}")
        return (src_key, e)
