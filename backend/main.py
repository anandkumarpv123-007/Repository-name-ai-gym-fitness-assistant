from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.health import router as health_router
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.workouts import router as workouts_router
from routers.nutrition import router as nutrition_router
from routers.buddy import router as buddy_router
from routers.habit import router as habit_router
from routers.planner import router as planner_router


app = FastAPI(title="AI Gym & Fitness Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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