from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings
from services.indexing_service import run_full_sync_task, run_incremental_sync_task, _sync_lock

router = APIRouter(prefix="/api/indexer", tags=["indexer"])
_security = HTTPBearer()

def _verify_token(credentials: HTTPAuthorizationCredentials = Security(_security)):
    settings = get_settings()
    if not settings.SYNC_TOKEN or credentials.credentials != settings.SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/sync/full", dependencies=[Depends(_verify_token)])
async def trigger_manual_full_sync(background_tasks: BackgroundTasks):
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Синхронизация уже выполняется.")
    _sync_lock.release()
    background_tasks.add_task(run_full_sync_task)
    return {"message": "Процесс ПОЛНОЙ переиндексации запущен в фоновом режиме."}

@router.post("/sync/incremental", dependencies=[Depends(_verify_token)])
async def trigger_manual_incremental_sync(background_tasks: BackgroundTasks):
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Синхронизация уже выполняется.")
    _sync_lock.release()
    background_tasks.add_task(run_incremental_sync_task)
    return {"message": "Процесс ЧАСТИЧНОЙ переиндексации запущен в фоновом режиме."}