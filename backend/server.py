from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
from backend.websocket_manager import WebSocketManager
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
import os

class LoginRequest(BaseModel):
    username: str
    password: str

class ResearchRequest(BaseModel):
    task: str
    report_type: str

app = FastAPI()

app.mount("/site", StaticFiles(directory="/home/TIsAmbrosyeva/giga_researcher/frontend"), name="site")
app.mount("/static", StaticFiles(directory="/home/TIsAmbrosyeva/giga_researcher/frontend/static"), name="static")
app.mount("/outputs", StaticFiles(directory="/home/TIsAmbrosyeva/giga_researcher/outputs"), name="outputs")

templates = Jinja2Templates(directory="/home/TIsAmbrosyeva/giga_researcher/frontend")

manager = WebSocketManager()

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
    user = os.getenv('USERNAME')
    passw = os.getenv('PASSWORD')
    if username == user and password == passw:
        return True
    return False

@app.post("/login")
async def login(request: LoginRequest):
    if authenticate_user(request.username, request.password):
        return {"success": True}
    else:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse('index.html', {"request": request, "report": None})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("start"):
                json_data = json.loads(data[6:])
                task = json_data.get("task")
                report_type = json_data.get("report_type")
                if task and report_type:
                    await manager.start_streaming(task, report_type, websocket)
                else:
                    logger.error(f"Введены не все данные")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
