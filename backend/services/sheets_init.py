"""
One-time initializer: creates all monitoring tabs with header rows.
Run once at startup or manually:
    python -m backend.services.sheets_init
"""
from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)


def init_all_sheets() -> dict:
    """
    Create every monitoring tab and write its header row.
    Safe to call multiple times — only writes headers when the tab is empty.
    Returns a summary dict.
    """
    from backend.services.sheets_service import (
        HEADERS, TAB_USERS, TAB_PAYMENTS,
        TAB_GENERATIONS, TAB_ERRORS, TAB_DIARY,
        _get_client, _spreadsheet_id,
    )

    results: dict[str, str] = {}
    try:
        gc = _get_client()
        sh = gc.open_by_key(_spreadsheet_id())
        existing_titles = [ws.title for ws in sh.worksheets()]
        logger.info(f"[SHEETS INIT] Existing tabs: {existing_titles}")

        for tab_name, headers in HEADERS.items():
            try:
                if tab_name in existing_titles:
                    ws = sh.worksheet(tab_name)
                    first = ws.row_values(1)
                    if not first or first[0] != headers[0]:
                        ws.insert_row(headers, index=1)
                        results[tab_name] = "headers written"
                        logger.info(f"[SHEETS INIT] Headers written to '{tab_name}'")
                    else:
                        results[tab_name] = "ok (headers already present)"
                        logger.info(f"[SHEETS INIT] Tab '{tab_name}' already has headers")
                else:
                    ws = sh.add_worksheet(title=tab_name, rows=1000, cols=20)
                    ws.append_row(headers, value_input_option="USER_ENTERED")
                    results[tab_name] = "created"
                    logger.info(f"[SHEETS INIT] Created tab '{tab_name}'")
            except Exception as tab_err:
                results[tab_name] = f"error: {tab_err}"
                logger.error(f"[SHEETS INIT] Tab '{tab_name}' error: {tab_err}")

        return {"status": "ok", "tabs": results}

    except Exception as exc:
        import traceback
        logger.error(f"[SHEETS INIT] Failed: {exc}\n{traceback.format_exc()}")
        return {"status": "error", "error": str(exc)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Allow running from repo root: python -m backend.services.sheets_init
    result = init_all_sheets()
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)
