from fastapi import APIRouter, BackgroundTasks
from services.indexing_service import run_full_sync_task, run_incremental_sync_task

router = APIRouter(prefix="/api/indexer", tags=["indexer"])

@router.post("/sync/full")
async def trigger_manual_full_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_full_sync_task)
    return {"message": "Процесс ПОЛНОЙ переиндексации запущен в фоновом режиме."}

@router.post("/sync/incremental")
async def trigger_manual_incremental_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_incremental_sync_task)
    return {"message": "Процесс ЧАСТИЧНОЙ переиндексации запущен в фоновом режиме."}