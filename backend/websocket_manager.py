import datetime
from loguru import logger
from backend.qch_report_type import qcheck_report
from backend.mr_report_type import mr_report


class TaskManager:
    async def start_task(self, task, report_type, publisher):
        try:
            await publisher.mark_running()
            await self.run_agent(task, report_type, publisher)
            task_snapshot = await publisher.store.get_task(publisher.task_id)
            if task_snapshot and task_snapshot["status"] != "failed":
                await publisher.finish()
        except Exception as er:
            logger.exception("Task execution failed")
            await publisher.send_error(str(er))

    async def run_agent(self, task, report_type, publisher):
        start_time = datetime.datetime.now()
        logger.info(f"report_type:  {report_type}")
        logger.info(f"Agent start:  {start_time}")

        match report_type:
            case "qcheck_report":
                if task.strip().isdigit() and len(task) < 11:
                    result = await qcheck_report(websocket=publisher, task=task.strip())
                    if not result:
                        await publisher.send_error("Quick-Check-Up завершился без результирующих файлов.")
                        return
                    pptx_path, pdf_path = result
                    if not pptx_path:
                        await publisher.send_error("Quick-Check-Up не смог сформировать итоговые файлы.")
                        return
                    await publisher.send_path(output=pptx_path, pdf_output=pdf_path)
                else:
                    await publisher.send_error("Введите корректный ИНН")
                    return
            case "mr_report":
                logger.info("Running mr_report...")
                pptx_path, pdf_path, sources_path = await mr_report(
                    websocket=publisher,
                    task=task.strip(),
                    image=False,
                )
                await publisher.send_path(
                    output=pptx_path,
                    pdf_output=pdf_path,
                    sources_output=sources_path,
                )
            case "mr_report_image":
                pptx_path, pdf_path, sources_path = await mr_report(
                    websocket=publisher,
                    task=task.strip(),
                    image=True,
                )
                await publisher.send_path(
                    output=pptx_path,
                    pdf_output=pdf_path,
                    sources_output=sources_path,
                )
            case _:
                await publisher.send_error(f"Неизвестный тип отчета: {report_type}")
                return

        end_time = datetime.datetime.now()
        logger.info(f"Agent finish:  {end_time}")
        await publisher.send_log(f"\nTotal run time: {end_time - start_time}\n")


WebSocketManager = TaskManager
