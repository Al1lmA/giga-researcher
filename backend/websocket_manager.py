import asyncio
import datetime
from typing import List, Dict
from fastapi import WebSocket
from loguru import logger
from backend.qch_report_type import qcheck_report
from backend.mr_report_type import mr_report


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.sender_tasks: Dict[WebSocket, asyncio.Task] = {}
        self.message_queues: Dict[WebSocket, asyncio.Queue] = {}

    async def start_sender(self, websocket: WebSocket):
        """Start the sender task."""
        queue = self.message_queues.get(websocket)
        if not queue:
            return

        while True:
            message = await queue.get()
            if websocket in self.active_connections:
                try:
                    await websocket.send_text(message)
                except:
                    break
            else:
                break

    async def connect(self, websocket: WebSocket):
        """Connect a websocket."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.message_queues[websocket] = asyncio.Queue()
        self.sender_tasks[websocket] = asyncio.create_task(self.start_sender(websocket))

    async def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.sender_tasks[websocket].cancel()
            await self.message_queues[websocket].put(None)
            del self.sender_tasks[websocket]
            del self.message_queues[websocket]

    async def start_streaming(self, task, report_type, websocket):
        """Start streaming the output."""
        try:
            await self.run_agent(task, report_type, websocket)
        except Exception as er:
            return
        return


    async def run_agent(self, task, report_type, websocket):
        """Run the agent."""
        start_time = datetime.datetime.now()
        logger.info(f"report_type:  {report_type}")
        logger.info(f"Agent start:  {start_time}")

        match report_type:
            case "qcheck_report":
                if task.strip().isdigit() and len(task) < 11:    
                    pptx_path, pdf_path = await qcheck_report(websocket=websocket, task=task.strip())  
                    await websocket.send_json({"type": "path", "output": pptx_path, "pdf_output" : pdf_path})           
                else:
                    await websocket.send_json({"type": "logs", "output": "Введите корректный ИНН"})
                    return
            case "mr_report":
                logger.info("Running mr_report...")
                pptx_path, pdf_path, sources_path = await mr_report(websocket=websocket, task=task.strip(), image=False)
                await websocket.send_json({"type": "path", "output": pptx_path, "pdf_output" : pdf_path, "sources_output":sources_path})
            case "mr_report_image":
                pptx_path, pdf_path, sources_path = await mr_report(websocket=websocket, task=task.strip(), image=True)
                await websocket.send_json({"type": "path", "output": pptx_path, "pdf_output" : pdf_path, "sources_output":sources_path})
            # case "gf_report":
            #     await websocket.send_json({"type": "logs", "output": f"\nGF REPORT\n"})

        end_time = datetime.datetime.now()
        logger.info(f"Agent finish:  {end_time}")
        await websocket.send_json({"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"})
        # await websocket.send_json({"type": "path", "output": pptx_path, "pdf_output" : pdf_path})
        return
