"""
Initialiser + Dashboard builder for Google Sheets monitoring.

Run once at startup or via POST /api/debug/sheets-init
Rebuild dashboard: POST /api/debug/sheets-dashboard
"""
from __future__ import annotations

import logging
import time
import sys

logger = logging.getLogger(__name__)

# ─── Tab initialiser ─────────────────────────────────────────────────────────

def init_all_sheets() -> dict:
    """
    Create / repair all monitoring tabs with header rows.
    Safe to call many times.
    """
    from backend.services.sheets_service import (
        HEADERS, TAB_USERS, TAB_PAYMENTS, TAB_GENERATIONS,
        TAB_ERRORS, TAB_DIARY, TAB_DASHBOARD,
        _get_client, _spreadsheet_id,
    )

    results: dict[str, str] = {}
    try:
        gc = _get_client()
        sh = gc.open_by_key(_spreadsheet_id())
        existing = [ws.title for ws in sh.worksheets()]
        logger.info(f"[SHEETS INIT] Existing tabs: {existing}")

        for tab_name, headers in HEADERS.items():
            if tab_name == TAB_DASHBOARD:
                continue  # dashboard built separately
            try:
                if tab_name in existing:
                    ws = sh.worksheet(tab_name)
                    first = ws.row_values(1)
                    if not first or first[0] != headers[0]:
                        ws.insert_row(headers, index=1)
                        results[tab_name] = "headers written"
                    else:
                        results[tab_name] = "ok"
                else:
                    ws = sh.add_worksheet(title=tab_name, rows=2000, cols=20)
                    ws.append_row(headers, value_input_option="USER_ENTERED")
                    results[tab_name] = "created"
                    logger.info(f"[SHEETS INIT] Created tab '{tab_name}'")
                time.sleep(0.3)
            except Exception as e:
                results[tab_name] = f"error: {e}"
                logger.error(f"[SHEETS INIT] '{tab_name}': {e}")

        return {"status": "ok", "tabs": results}

    except Exception as exc:
        import traceback
        logger.error(f"[SHEETS INIT] Failed: {exc}\n{traceback.format_exc()}")
        return {"status": "error", "error": str(exc)}


# ─── Dashboard builder ────────────────────────────────────────────────────────

# Short aliases for tab names used in formulas (must match TAB_* constants).
# Google Sheets requires single-quotes around sheet names with special chars.
_U  = "'👥 Пользователи'"
_P  = "'💳 Оплаты'"
_G  = "'🎨 Генерации'"
_D  = "'📅 Дневник'"

# ── Column map (1-indexed; match HEADERS order) ──
# Оплаты:     H=Сумма(сум)  I=Кредиты  J=Статус  C=Тип
# Генерации:  H=Кредиты     I=Статус   J=API($)  K=Время(сек)
# Польз:      G=Реферер     F=Источник
# Дневник:    G=Выручка     I=API($)

def _f(formula: str) -> str:
    """Prefix string with = so gspread writes it as a formula."""
    return f"={formula}"


def _build_dashboard_rows(usd_rate_cell: str = "B33") -> list[list]:
    """
    Returns the full dashboard as a list of [label, value/formula, note] rows.
    usd_rate_cell — the cell where the USD/UZS rate is stored (used in formulas).
    """
    U, P, G, D = _U, _P, _G, _D

    # Часто используемые формулы
    total_users   = f"COUNTA({U}!A2:A)"
    ref_users     = f"COUNTIF({U}!G2:G,\"<>—\")"
    rev_confirmed = f"SUMIF({P}!J2:J,\"✅ Подтверждено\",{P}!H2:H)"
    rev_topup     = f"SUMIF({P}!C2:C,\"💵 Пополнение баланса\",{P}!H2:H)"
    rev_balance   = f"SUMIF({P}!C2:C,\"💸 Оплата с баланса\",{P}!H2:H)"
    commissions   = f"SUMIF({P}!C2:C,\"👥 Реферальная комиссия\",{P}!H2:H)"
    cnt_confirmed = f"COUNTIF({P}!J2:J,\"✅ Подтверждено\")"
    cnt_waiting   = f"COUNTIF({P}!J2:J,\"⏳ Ожидание\")"
    cnt_rejected  = f"COUNTIF({P}!J2:J,\"❌ Отклонено\")"
    total_gens    = f"COUNTA({G}!A2:A)"
    ok_gens       = f"COUNTIF({G}!I2:I,\"✅ Готово\")"
    fail_gens     = f"COUNTIF({G}!I2:I,\"❌ Ошибка\")"
    nb_gens       = f"COUNTIF({G}!F2:F,\"🍌 Nano Banana\")"
    kl_gens       = f"COUNTIF({G}!F2:F,\"🎥 Kling\")"
    veo_gens      = f"COUNTIF({G}!F2:F,\"🎬 Veo 3\")"
    cr_spent      = f"SUMIF({G}!I2:I,\"✅ Готово\",{G}!H2:H)"
    api_total     = f"SUM({G}!J2:J)"
    avg_time      = (f"IFERROR(ROUND(AVERAGEIF({G}!I2:I,"
                    f"\"✅ Готово\",{G}!K2:K),0),0)")

    rows: list[list] = [
        # ── Заголовок ──────────────────────────────────────────────────────
        ["📊 HARF AI — МОНИТОРИНГ", _f("NOW()"), "Обновляется при открытии"],
        ["", "", ""],

        # ── 👥 Пользователи ────────────────────────────────────────────────
        ["👥 ПОЛЬЗОВАТЕЛИ", "", ""],
        ["Всего зарегистрировано",     _f(total_users),                   "человек"],
        ["По реферальной ссылке",      _f(ref_users),                     "человек"],
        ["Без реферала (органика)",    _f(f"{total_users}-{ref_users}"),  "человек"],
        ["Доля рефералов (%)",         _f(f"IF({total_users}>0,"
                                           f"ROUND({ref_users}/{total_users}*100,1),0)"),
                                       "%"],
        ["", "", ""],

        # ── 💰 Финансы ─────────────────────────────────────────────────────
        ["💰 ФИНАНСЫ", "", ""],
        ["Выручка подтверждена (UZS)", _f(rev_confirmed),                 "сум"],
        ["Выручка (USD)",              _f(f"IFERROR(ROUND({rev_confirmed}/{usd_rate_cell},2),0)"),
                                       "долларов"],
        ["Пополнений баланса (UZS)",   _f(rev_topup),                     "сум"],
        ["Оплат с баланса (UZS)",      _f(rev_balance),                   "сум"],
        ["Оплат подтверждено",         _f(cnt_confirmed),                 "шт"],
        ["Оплат ожидает",              _f(cnt_waiting),                   "шт"],
        ["Оплат отклонено",            _f(cnt_rejected),                  "шт"],
        ["Реферальных комиссий (UZS)", _f(commissions),                   "сум"],
        ["Средний чек (UZS)",          _f(f"IF({cnt_confirmed}>0,"
                                           f"ROUND({rev_confirmed}/{cnt_confirmed},0),0)"),
                                       "сум"],
        ["", "", ""],

        # ── 🎨 Генерации ───────────────────────────────────────────────────
        ["🎨 ГЕНЕРАЦИИ", "", ""],
        ["Всего задач",                _f(total_gens),   "шт"],
        ["Успешных",                   _f(ok_gens),      "шт"],
        ["Ошибок",                     _f(fail_gens),    "шт"],
        ["В процессе / ожидании",      _f(f"{total_gens}-{ok_gens}-{fail_gens}"),
                                       "шт"],
        ["Успешность (%)",             _f(f"IF({total_gens}>0,"
                                           f"ROUND({ok_gens}/{total_gens}*100,1),0)"),
                                       "%"],
        ["🍌 Nano Banana",             _f(nb_gens),      "генераций"],
        ["🎥 Kling",                   _f(kl_gens),      "генераций"],
        ["🎬 Veo 3",                   _f(veo_gens),     "генераций"],
        ["Кредитов потрачено",         _f(cr_spent),     "кредитов"],
        ["Среднее время (сек)",        _f(avg_time),     "секунд"],
        ["", "", ""],

        # ── 📊 Прибыль ─────────────────────────────────────────────────────
        ["📊 РАСЧЁТ ПРИБЫЛИ", "", ""],
        ["Курс USD → UZS",            12700,             "← измените при необходимости"],
        ["API: Nano Banana ($)",       _f(f"{nb_gens}*0.004"),    "$"],
        ["API: Kling ($)",             _f(f"{kl_gens}*0.14"),     "$"],
        ["API: Veo 3 ($)",             _f(f"{veo_gens}*0.10"),    "$"],
        ["Итого API расходы ($)",      _f(f"SUM({api_total})"),   "$"],
        ["Итого API расходы (UZS)",    _f(f"ROUND({api_total}*{usd_rate_cell},0)"),
                                       "сум"],
        ["", "", ""],
        ["💰 ПРИБЫЛЬ (UZS)",          _f(f"{rev_confirmed}-ROUND({api_total}*{usd_rate_cell},0)"),
                                       "сум"],
        ["💰 ПРИБЫЛЬ (USD)",          _f(f"IFERROR(ROUND(({rev_confirmed}-"
                                           f"ROUND({api_total}*{usd_rate_cell},0))/{usd_rate_cell},2),0)"),
                                       "долларов"],
        ["Маржинальность (%)",         _f(f"IF({rev_confirmed}>0,"
                                           f"ROUND(({rev_confirmed}-"
                                           f"ROUND({api_total}*{usd_rate_cell},0))/{rev_confirmed}*100,1),0)"),
                                       "%"],
        ["", "", ""],

        # ── 📅 Дневник — итоги ────────────────────────────────────────────
        ["📅 ИТОГИ ЗА ВСЁ ВРЕМЯ (из Дневника)", "", ""],
        ["Всего новых польз. (из дн.)", _f(f"SUM({D}!B2:B)"),    "человек"],
        ["Выручка по дневнику (UZS)",   _f(f"SUM({D}!G2:G)"),    "сум"],
        ["API расход по дневнику ($)",  _f(f"SUM({D}!I2:I)"),    "$"],
        ["Дней с записями",             _f(f"COUNTA({D}!A2:A)"), "дней"],
    ]
    return rows


def create_dashboard() -> dict:
    """
    Create (or fully rebuild) the 📊 Дашборд tab with live formulas.
    """
    from backend.services.sheets_service import (
        TAB_DASHBOARD, HEADERS, _get_client, _spreadsheet_id,
    )

    try:
        gc = _get_client()
        sh = gc.open_by_key(_spreadsheet_id())

        existing = [ws.title for ws in sh.worksheets()]
        if TAB_DASHBOARD in existing:
            ws = sh.worksheet(TAB_DASHBOARD)
            ws.clear()
            logger.info("[DASHBOARD] Cleared existing dashboard tab")
        else:
            ws = sh.add_worksheet(title=TAB_DASHBOARD, rows=200, cols=5)
            logger.info("[DASHBOARD] Created new dashboard tab")

        # Write header row first
        ws.append_row(HEADERS[TAB_DASHBOARD], value_input_option="USER_ENTERED")
        time.sleep(0.5)

        # Build and write all rows
        # usd_rate_cell = B33 (row 33 in data = row 34 in sheet because of header row)
        # We build rows first to find the rate row, then write
        data_rows = _build_dashboard_rows(usd_rate_cell="B34")
        ws.append_rows(data_rows, value_input_option="USER_ENTERED")

        # Format: bold section headers (rows where column B is empty and A has emoji)
        try:
            _format_dashboard(ws, data_rows)
        except Exception as fe:
            logger.warning(f"[DASHBOARD] Formatting skipped: {fe}")

        logger.info(f"[DASHBOARD] Written {len(data_rows)} rows")
        return {"status": "ok", "rows": len(data_rows)}

    except Exception as exc:
        import traceback
        logger.error(f"[DASHBOARD] Failed: {exc}\n{traceback.format_exc()}")
        return {"status": "error", "error": str(exc)}


def _format_dashboard(ws, data_rows: list) -> None:
    """Bold section headers and apply background colors."""
    import gspread
    from gspread.utils import rowcol_to_a1

    section_rows = []  # 1-indexed sheet rows (1 = header)
    for i, row in enumerate(data_rows):
        label = row[0] if row else ""
        value = row[1] if len(row) > 1 else ""
        # Section headers: have emoji, no formula in B
        if label and label[0] in "👥💰🎨📊📅" and value == "":
            section_rows.append(i + 2)  # +1 for header row, +1 for 1-indexing

    if not section_rows:
        return

    requests = []
    for sr in section_rows:
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": sr - 1,
                    "endRowIndex": sr,
                    "startColumnIndex": 0,
                    "endColumnIndex": 3,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.27, "green": 0.51, "blue": 0.71},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        })

    # Bold the title row (row 2 = first data row)
    requests.append({
        "repeatCell": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 1,
                "endRowIndex": 2,
                "startColumnIndex": 0,
                "endColumnIndex": 3,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.13, "green": 0.29, "blue": 0.53},
                    "textFormat": {
                        "bold": True,
                        "fontSize": 13,
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                    },
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    })

    # Profit rows — highlight green
    profit_labels = ["💰 ПРИБЫЛЬ (UZS)", "💰 ПРИБЫЛЬ (USD)", "Маржинальность (%)"]
    for i, row in enumerate(data_rows):
        if row and row[0] in profit_labels:
            sr = i + 2
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": sr - 1,
                        "endRowIndex": sr,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.72, "green": 0.88, "blue": 0.72},
                            "textFormat": {"bold": True},
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            })

    if requests:
        ws.spreadsheet.batch_update({"requests": requests})
        logger.info(f"[DASHBOARD] Applied {len(requests)} formatting rules")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import json
    result = init_all_sheets()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    result2 = create_dashboard()
    print(json.dumps(result2, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)
