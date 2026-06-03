import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..models.database import get_db, Resume, JobListing, MatchResult
from ..services.ai_service import match_score as ai_match_score

router = APIRouter(prefix="/api/match", tags=["match"])

SEMAPHORE = asyncio.Semaphore(5)

SOURCE_KEY_TO_NAME = {
    "boss": "BOSS直聘",
    "liepin": "猎聘",
    "zhaopin": "智联招聘",
    "guopin": "国聘",
}


@router.get("")
async def get_matches(
    city: str = "",
    min_score: float = Query(0.0, ge=0, le=100),
    resume_id: Optional[int] = None,
    source: str = "",
    db: Session = Depends(get_db),
):
    # Get the resume
    if resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
    else:
        resume = db.query(Resume).order_by(Resume.created_at.desc()).first()
    if not resume:
        return {"matches": [], "message": "请先上传简历"}

    # Get jobs
    query = db.query(JobListing)
    if city:
        query = query.filter(JobListing.city == city)
    if source:
        source_name = SOURCE_KEY_TO_NAME.get(source, source)
        query = query.filter(JobListing.source == source_name)
    jobs = query.order_by(JobListing.created_at.desc()).all()

    # Build resume info once
    resume_info = {
        "skills": resume.skills or [],
        "experience": resume.experience or [],
        "projects": resume.projects or [],
        "education": resume.education or [],
    }

    async def score_job(job):
        existing = (
            db.query(MatchResult)
            .filter(MatchResult.resume_id == resume.id, MatchResult.job_id == job.id)
            .first()
        )
        if existing:
            return (job, existing.score, "")

        async with SEMAPHORE:
            try:
                result = await ai_match_score(
                    resume_info,
                    {
                        "title": job.title,
                        "company": job.company,
                        "description": job.description,
                        "requirements": job.requirements,
                    },
                )
                score = float(result.get("score", 0))
                reason = result.get("reason", "")
            except Exception as e:
                print(f"[Match] job {job.id} ({job.title}) score failed: {e}")
                score = 0.0
                reason = ""

        match = MatchResult(
            resume_id=resume.id,
            job_id=job.id,
            score=score,
            is_recommended=score >= min_score,
        )
        db.add(match)
        db.commit()
        return (job, score, reason)

    # Score all jobs concurrently (limited by semaphore)
    scored = await asyncio.gather(*[score_job(job) for job in jobs])

    results = []
    for job, score, reason in scored:
        if score >= min_score:
            results.append(
                {
                    "job": {
                        "id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "description": job.description,
                        "requirements": job.requirements,
                        "source": job.source,
                        "source_url": job.source_url,
                        "salary": job.salary,
                        "city": job.city,
                        "location": job.location,
                        "posted_date": job.posted_date,
                    },
                    "score": score,
                    "reason": reason,
                    "resume_id": resume.id,
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "matches": results,
        "city": city,
        "min_score": min_score,
        "total_jobs": len(jobs),
        "matched": len(results),
    }
