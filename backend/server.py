from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
from backend.websocket_manager import WebSocketManager
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
import os

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
    user = 'DESKTOP-AHIBJG1'
    passw = 'CTK-IT-Check!#'
    # user = os.getenv('USERNAME')
    # passw = os.getenv('PASSWORD')
    #
    username = 'DESKTOP-AHIBJG1'
    password = 'CTK-IT-Check!#'
    #
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

'''
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
'''

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("===> КТО-ТО ПЫТАЕТСЯ ПОДКЛЮЧИТЬСЯ К WEBSOCKET")
    await manager.connect(websocket)
    logger.info(f"WebSocket подключен: {websocket.client}")
    try:
        while True:
            logger.info("Ожидаем сообщение от клиента...")
            data = await websocket.receive_text()
            logger.info(f"Получено сообщение от клиента: {data}")

            if data.startswith("start"):
                try:
                    logger.info("Парсим JSON после 'start'")
                    json_data = json.loads(data[6:])
                    task = json_data.get("task")
                    report_type = json_data.get("report_type")

                    logger.info(f"Извлечено: task={task}, report_type={report_type}")

                    if task and report_type:
                        logger.info("Запускаем start_streaming")
                        await manager.start_streaming(task, report_type, websocket)
                    else:
                        logger.error("Ошибка: Не все данные были переданы (task или report_type отсутствует)")
                        await websocket.send_text("Ошибка: не указаны task или report_type")

                except json.JSONDecodeError as e:
                    logger.exception("Ошибка при разборе JSON из сообщения")
                    await websocket.send_text("Ошибка формата запроса")

                except Exception as e:
                    logger.exception("Ошибка внутри обработки команды start")
                    await websocket.send_text("Внутренняя ошибка при запуске задачи")

    except WebSocketDisconnect:
        logger.warning("WebSocket отключен")
        await manager.disconnect(websocket)

    except Exception as e:
        logger.exception("Необработанная ошибка в WebSocket соединении")
