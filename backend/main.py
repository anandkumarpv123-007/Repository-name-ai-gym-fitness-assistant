from fastapi import FastAPI

from routers.health import router as health_router
from routers.auth import router as auth_router
from routers.users import router as users_router


app = FastAPI(title="AI Gym & Fitness Assistant")


@app.get("/")
def root():
    return {
        "message": "AI Gym & Fitness Assistant API is running"
    }


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)