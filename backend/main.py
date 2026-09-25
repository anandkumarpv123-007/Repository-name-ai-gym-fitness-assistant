from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from create_tables import init_db
from routers.health import router as health_router
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.workouts import router as workouts_router
from routers.nutrition import router as nutrition_router
from routers.buddy import router as buddy_router
from routers.habit import router as habit_router
from routers.planner import router as planner_router
from routers.iot import router as iot_router
from routers.analytics import router as analytics_router
from routers.media import router as media_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize all SQLAlchemy database tables and default seeds on startup
    init_db()
    yield


app = FastAPI(title="AI Gym & Fitness Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-gym-fitness-assistant-xi.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "AI Gym & Fitness Assistant API is running"
    }


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(workouts_router)
app.include_router(nutrition_router)
app.include_router(buddy_router)
app.include_router(habit_router)
app.include_router(planner_router)
app.include_router(iot_router)
app.include_router(analytics_router)
app.include_router(media_router)