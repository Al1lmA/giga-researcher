import asyncio
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskRecord:
    task_id: str
    task: str
    report_type: str
    status: str = "pending"
    progress: int = 0
    logs: list[str] = field(default_factory=list)
    report_chunks: list[str] = field(default_factory=list)
    result: Dict[str, Optional[str]] = field(
        default_factory=lambda: {"output": None, "pdf_output": None, "sources_output": None}
    )
    error: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    version: int = 0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task": self.task,
            "report_type": self.report_type,
            "status": self.status,
            "progress": self.progress,
            "logs": deepcopy(self.logs),
            "report_chunks": deepcopy(self.report_chunks),
            "report": "".join(self.report_chunks),
            "result": deepcopy(self.result),
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }


class InMemoryTaskStore:
    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task: str, report_type: str) -> str:
        task_id = uuid.uuid4().hex
        async with self._lock:
            self._tasks[task_id] = TaskRecord(task_id=task_id, task=task, report_type=report_type)
        return task_id

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            task = self._tasks.get(task_id)
            return task.snapshot() if task else None

    async def mark_running(self, task_id: str):
        await self._mutate(task_id, lambda task: setattr(task, "status", "running"))

    async def append_log(self, task_id: str, output: str):
        def mutate(task: TaskRecord):
            task.logs.append(output)

        await self._mutate(task_id, mutate)

    async def append_report(self, task_id: str, output: str):
        def mutate(task: TaskRecord):
            task.report_chunks.append(output)

        await self._mutate(task_id, mutate)

    async def set_progress(self, task_id: str, progress: int):
        def mutate(task: TaskRecord):
            task.progress = progress

        await self._mutate(task_id, mutate)

    async def set_result(
        self,
        task_id: str,
        output: Optional[str] = None,
        pdf_output: Optional[str] = None,
        sources_output: Optional[str] = None,
    ):
        def mutate(task: TaskRecord):
            if output is not None:
                task.result["output"] = output
            if pdf_output is not None:
                task.result["pdf_output"] = pdf_output
            if sources_output is not None:
                task.result["sources_output"] = sources_output

        await self._mutate(task_id, mutate)

    async def set_error(self, task_id: str, error: str):
        def mutate(task: TaskRecord):
            task.status = "failed"
            task.error = error

        await self._mutate(task_id, mutate)

    async def mark_finished(self, task_id: str):
        def mutate(task: TaskRecord):
            task.status = "finished"
            task.progress = max(task.progress, 100)

        await self._mutate(task_id, mutate)

    async def _mutate(self, task_id: str, callback):
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            callback(task)
            task.updated_at = utc_now_iso()
            task.version += 1


class TaskEventPublisher:
    def __init__(self, store: InMemoryTaskStore, task_id: str):
        self.store = store
        self.task_id = task_id

    async def mark_running(self):
        await self.store.mark_running(self.task_id)

    async def send_log(self, output: str):
        await self.store.append_log(self.task_id, output)

    async def send_report(self, output: str):
        await self.store.append_report(self.task_id, output)

    async def send_progress(self, progress: int):
        await self.store.set_progress(self.task_id, progress)

    async def send_path(
        self,
        output: Optional[str] = None,
        pdf_output: Optional[str] = None,
        sources_output: Optional[str] = None,
    ):
        await self.store.set_result(
            self.task_id,
            output=output,
            pdf_output=pdf_output,
            sources_output=sources_output,
        )

    async def send_error(self, output: str):
        await self.store.set_error(self.task_id, output)

    async def finish(self):
        await self.store.mark_finished(self.task_id)

    async def send_json(self, payload: Dict[str, Any]):
        message_type = payload.get("type")
        output = payload.get("output")
        if message_type == "logs" and output is not None:
            await self.send_log(output)
        elif message_type == "report" and output is not None:
            await self.send_report(output)
        elif message_type == "progress" and output is not None:
            await self.send_progress(int(output))
        elif message_type == "path":
            await self.send_path(
                output=payload.get("output"),
                pdf_output=payload.get("pdf_output"),
                sources_output=payload.get("sources_output"),
            )
        elif message_type == "error" and output is not None:
            await self.send_error(output)

    async def send_text(self, output: str):
        await self.send_error(output)
