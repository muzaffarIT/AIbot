from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header
import httpx
from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.models.generation_job import GenerationJob
from backend.models.user import User
from backend.services.balance_service import BalanceService

router = APIRouter(prefix="/debug", tags=["debug"])


# ── Auth dependency ───────────────────────────────────────────────────────────

def _require_debug_token(x_debug_token: str | None = Header(default=None)) -> None:
    """All /debug endpoints require X-Debug-Token: <SECRET_KEY> header."""
    if not settings.secret_key:
        raise HTTPException(status_code=500, detail="Secret key not configured")
    if not x_debug_token or x_debug_token != settings.secret_key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Debug-Token")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/sheets-test", dependencies=[Depends(_require_debug_token)])
def sheets_test():
    """Test Google Sheets connectivity."""
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


@router.post("/sheets-init", dependencies=[Depends(_require_debug_token)])
def sheets_init():
    """Create / repair all monitoring tabs in Google Sheets."""
    from backend.services.sheets_init import init_all_sheets
    return init_all_sheets()


@router.post("/sheets-migrate", dependencies=[Depends(_require_debug_token)])
def sheets_migrate(clear: bool = True):
    """Migrate ALL historical DB data to Google Sheets."""
    from backend.services.sheets_migration import migrate_all_to_sheets
    return migrate_all_to_sheets(clear_first=clear)


@router.post("/sheets-dashboard", dependencies=[Depends(_require_debug_token)])
def sheets_dashboard():
    """(Re)build the 📊 Дашборд tab with live profit/monitoring formulas."""
    from backend.services.sheets_init import create_dashboard
    return create_dashboard()


@router.post("/cleanup-stale", dependencies=[Depends(_require_debug_token)])
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


@router.get("/kie-ping", dependencies=[Depends(_require_debug_token)])
async def kie_ping():
    """Test KIE AI API connectivity."""
    from backend.core.config import settings
    base = (settings.kie_base_url or "https://api.kie.ai").rstrip("/")
    key = settings.kie_api_key or ""
    results = {}

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


# ── Notification triggers + diagnostics ──────────────────────────────────────
# Why these exist: celery-beat on Railway is fragile (embedded beat in a
# restarting container silently stops firing). These endpoints let an
# external scheduler — cron-job.org, GitHub Actions, UptimeRobot — call the
# daily broadcasts over HTTP on a fixed schedule, decoupling delivery from
# the in-process beat. They also double as a manual "send now" / health
# check for the admin.
#
# Auth: X-Debug-Token header (== SECRET_KEY), same as every /debug route.

def _notification_target_counts(db) -> dict:
    """How many users each broadcast would currently reach — for diagnostics."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func

    total = db.query(func.count(User.id)).scalar() or 0
    opted_in = db.query(func.count(User.id)).filter(
        User.notifications_enabled == True,  # noqa: E712
        User.is_blocked == False,            # noqa: E712
    ).scalar() or 0

    tashkent = timezone(timedelta(hours=5))
    today_start = datetime.combine(
        datetime.now(tashkent).date(), datetime.min.time(), tzinfo=tashkent
    )
    # Eligible for the bonus reminder specifically = opted-in AND not claimed today
    from sqlalchemy import or_
    reminder_eligible = db.query(func.count(User.id)).filter(
        User.notifications_enabled == True,  # noqa: E712
        User.is_blocked == False,            # noqa: E712
        or_(
            User.last_daily_claim == None,  # noqa: E711
            User.last_daily_claim < today_start,
        ),
    ).scalar() or 0

    return {
        "total_users": total,
        "broadcastable_users": opted_in,
        "reminder_eligible_now": reminder_eligible,
    }


@router.post("/trigger-reminders", dependencies=[Depends(_require_debug_token)])
def trigger_reminders():
    """Fire the daily bonus reminder task immediately via the queue."""
    # Use send_task on the worker's celery_app explicitly. The tasks are
    # decorated with @shared_task, which binds to whatever celery app is
    # current at import time — in the backend process that's the default
    # app (amqp://guest@localhost), so daily_reminder_task.delay() would
    # try AMQP and hit Connection refused. send_task routes through the
    # real app whose broker is Redis.
    from worker.celery_app import celery_app
    result = celery_app.send_task("worker.tasks.notification_tasks.daily_reminder_task")
    db = SessionLocal()
    try:
        counts = _notification_target_counts(db)
    finally:
        db.close()
    return {
        "triggered": "daily_reminder_task",
        "task_id": getattr(result, "id", None),
        "targets": counts,
    }


@router.post("/trigger-daily-tip", dependencies=[Depends(_require_debug_token)])
def trigger_daily_tip():
    """Fire the rotating daily-tip broadcast immediately via the queue."""
    # See trigger_reminders: send_task on the real celery_app, not
    # shared_task.delay() (which binds to the default amqp app in backend).
    from worker.celery_app import celery_app
    result = celery_app.send_task("worker.tasks.notification_tasks.daily_tip_task")
    db = SessionLocal()
    try:
        counts = _notification_target_counts(db)
    finally:
        db.close()
    return {
        "triggered": "daily_tip_task",
        "task_id": getattr(result, "id", None),
        "targets": counts,
    }


@router.get("/notifications-status", dependencies=[Depends(_require_debug_token)])
def notifications_status():
    """Health check: shows how many users each broadcast would reach right now.

    Use this to confirm the queue is wired up and the audience size is sane,
    without actually sending anything.
    """
    import os as _os
    db = SessionLocal()
    try:
        counts = _notification_target_counts(db)
    finally:
        db.close()
    # Surface the broker URL the backend would actually use (password masked)
    # so we can tell whether REDIS_URL is being picked up by the container.
    raw = _os.environ.get("REDIS_URL", "")
    masked = raw.replace("://default:", "://default:***@") if "://default:" in raw else raw
    # Actually try to resolve+connect to the broker, so we can tell apart
    # "URL is wrong" from "URL is right but network is blocked".
    diag = {"redis_url_seen": masked}
    # What does the celery app actually think its broker is?
    try:
        from worker.celery_app import celery_app as _celery
        diag["celery_broker"] = str(_celery.conf.broker_url or "").replace(
            "://default:", "://default:***@"
        )
        diag["celery_result"] = str(_celery.conf.result_backend or "")
    except Exception as e:
        diag["celery_inspect_error"] = str(e)
    try:
        import socket as _socket
        from urllib.parse import urlparse as _u
        parsed = _u(raw if "://" in raw else "redis://" + raw)
        host = parsed.hostname or "redis.railway.internal"
        port = parsed.port or 6379
        try:
            ip = _socket.gethostbyname(host)
            diag["resolved"] = f"{host} -> {ip}"
        except Exception as e:
            diag["resolved"] = f"{host} -> DNS FAIL: {e}"
        s = _socket.socket()
        s.settimeout(3)
        try:
            s.connect((host, port))
            diag["tcp_connect"] = f"{host}:{port} OK"
        except Exception as e:
            diag["tcp_connect"] = f"{host}:{port} FAIL: {e}"
        finally:
            s.close()
    except Exception as e:
        diag["net_diag_error"] = str(e)
    return {"ok": True, "targets": counts, "diag": diag}
