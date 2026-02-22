from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import users, tasks, notes, ai_chatbot, stats, habits, credentials
from services.scheduler import start_scheduler
import uvicorn
import os

app = FastAPI(title="AI Smart Daily Work Assistant")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://daily-repot.onrender.com",
        "https://daily-task-frontend-mu.vercel.app",
        "https://daily-task-frontend-oumq.onrender.com",
        "https://frontend-daily-task.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routes
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(ai_chatbot.router)
app.include_router(stats.router)
app.include_router(habits.router)
app.include_router(credentials.router)

@app.on_event("startup")
async def startup_event():
    # Start the background task scheduler
    start_scheduler()

@app.get("/")
@app.head("/")
async def root():
    return {"message": "AI Smart Planner API is running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
