from fastapi import FastAPI
from routers.health import router as health_router

app = FastAPI(title="AI Gym & Fitness Assistant")


@app.get("/")
def root():
    return {
        "message": "AI Gym & Fitness Assistant API is running"
    }


app.include_router(health_router)