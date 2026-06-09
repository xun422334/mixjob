import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import resume, chat, jobs, cities, match, auth
from .models.database import init_db

app = FastAPI(title="AI智能求职助手")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,https://www.mixjob.cn,https://mixjob.cn").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(chat.router)
app.include_router(jobs.router)
app.include_router(cities.router)
app.include_router(match.router)
app.include_router(auth.router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}
