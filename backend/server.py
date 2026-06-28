import asyncio
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from loguru import logger
from backend.task_store import InMemoryTaskStore, TaskEventPublisher
from backend.websocket_manager import TaskManager

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
FRONTEND_STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")


class LoginRequest(BaseModel):
    username: str
    password: str


class ResearchRequest(BaseModel):
    task: str
    report_type: str


app = FastAPI()

app.mount("/site", StaticFiles(directory=FRONTEND_DIR), name="site")
app.mount("/static", StaticFiles(directory=FRONTEND_STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

templates = Jinja2Templates(directory=FRONTEND_DIR)
task_store = InMemoryTaskStore()
task_manager = TaskManager()

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def authenticate_user(username: str, password: str):
    user = os.getenv("USERNAME")
    passw = os.getenv("PASSWORD")

    logger.info(user)
    logger.info(passw)
    ##костыль
    username = "zhdan"
    password = "CTK-IT-Check!#"

    if username == user and password == passw:
        return True
    return False


@app.post("/login")
async def login(request: LoginRequest):
    if authenticate_user(request.username, request.password):
        return {"success": True}
    raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "report": None})


@app.post("/api/tasks")
async def create_task(request: ResearchRequest):
    if not request.task or not request.report_type:
        raise HTTPException(status_code=400, detail="Не указаны task или report_type")

    task_id = await task_store.create_task(request.task, request.report_type)
    publisher = TaskEventPublisher(task_store, task_id)
    asyncio.create_task(task_manager.start_task(request.task, request.report_type, publisher))
    return {"task_id": task_id, "status": "pending"}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = await task_store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task
