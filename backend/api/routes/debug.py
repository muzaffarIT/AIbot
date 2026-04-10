from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
import httpx
from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.models.generation_job import GenerationJob
from backend.models.user import User
from backend.services.balance_service import BalanceService

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/sheets-test")
def sheets_test():
    """
    Test Google Sheets connectivity.
    Call GET /api/debug/sheets-test from Railway to diagnose logging issues.
    """
    import os
    import traceback as _tb

    result: dict = {
        "env_var_set": bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()),
        "env_var_length": len(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")),
    }

    try:
        from bot.services.sheets import sheets_test as _st, _append, SPREADSHEET_ID
        conn = _st()
        result["connection"] = conn

        if conn.get("ok"):
            # Try writing a test row
            _append([
                "TEST", "🔧 Тест подключения", "—",
                "System", "—", "0",
                "Проверка связи с таблицей", "0", "0",
                "", "✅ OK", "auto-test",
            ])
            result["write_test"] = "ok — test row appended"
        else:
            result["write_test"] = "skipped (connection failed)"

    except Exception as e:
        result["import_error"] = str(e)
        result["import_traceback"] = _tb.format_exc()

    return result

@router.post("/sheets-init")
def sheets_init():
    """
    Create / repair all monitoring tabs in Google Sheets.
    Call POST /api/debug/sheets-init once after deploy.
    """
    from backend.services.sheets_init import init_all_sheets
    return init_all_sheets()


@router.post("/sheets-migrate")
def sheets_migrate(clear: bool = True):
    """
    Migrate ALL historical DB data to Google Sheets.
    ?clear=true  — clears tabs first (default), then writes everything.
    ?clear=false — appends to existing data.
    WARNING: can take 1-3 minutes depending on data volume.
    """
    from backend.services.sheets_migration import migrate_all_to_sheets
    return migrate_all_to_sheets(clear_first=clear)


@router.post("/sheets-dashboard")
def sheets_dashboard():
    """
    (Re)build the 📊 Дашборд tab with live profit/monitoring formulas.
    Call after deploy or after changing tab structure.
    """
    from backend.services.sheets_init import create_dashboard
    return create_dashboard()


@router.post("/cleanup-stale")
async def cleanup_stale():
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        stale = db.query(GenerationJob).filter(
            GenerationJob.status == "pending",
            GenerationJob.created_at < cutoff
        ).all()
        
        refunded = 0
        balance_service = BalanceService(db)
        for job in stale:
            job.status = "failed"
            job.error_message = "Manual cleanup"
            user = db.query(User).filter(User.id == job.user_id).first()
            if user:
                balance_service.add_credits(
                    user_id=user.id,
                    amount=job.credits_reserved,
                    comment="Manual cleanup"
                )
                refunded += job.credits_reserved
        db.commit()
        return {"cleaned": len(stale), "refunded": refunded}
    finally:
        db.close()

@router.get("/kie-ping")
async def kie_ping():
    """Test KIE AI API connectivity using the real createTask endpoint."""
    import httpx
    from backend.core.config import settings
    base = (settings.kie_base_url or "https://api.kie.ai").rstrip("/")
    key = settings.kie_api_key or ""
    results = {}

    # Test 1: create a market task (nano-banana) — no wait, just confirm API accepts it
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{base}/api/v1/jobs/createTask",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "google/nano-banana",
                    "input": {"prompt": "api connectivity test", "output_format": "png", "image_size": "1:1"},
                },
            )
            results["createTask_status"] = r.status_code
            try:
                body = r.json()
                results["createTask_body"] = body
                results["task_id"] = body.get("data", {}).get("taskId")
            except Exception:
                results["createTask_body"] = r.text
    except Exception as e:
        results["createTask_error"] = str(e)

    # Test 2: veo endpoint ping
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r2 = await client.get(
                f"{base}/api/v1/veo/record-info",
                headers={"Authorization": f"Bearer {key}"},
                params={"taskId": "ping_test"},
            )
            results["veo_status"] = r2.status_code
    except Exception as e:
        results["veo_error"] = str(e)

    results["key_first_8"] = key[:8] if key else "EMPTY"
    results["base_url"] = base
    results["mock_mode"] = settings.ai_mock_mode
    return results
