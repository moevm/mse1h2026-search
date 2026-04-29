from fastapi import APIRouter, BackgroundTasks
from services.indexing_service import run_sync_task

router = APIRouter(prefix="/api/indexer", tags=["indexer"])

@router.post("/sync")
async def trigger_manual_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_sync_task)
    return {"message": "Процесс переиндексации запущен в фоновом режиме."}