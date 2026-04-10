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

# ── Column map (match HEADERS order) ──
# Оплаты:     H=Сумма(сум)  I=Кредиты  J=Статус  C=Тип
# Генерации:  H=Кредиты     I=Статус   J=API($)  K=Время(сек)
# Польз:      G=Реферер
# Дневник:    G=Выручка     I=API($)

# IMPORTANT: Russian-locale Google Sheets uses ";" as formula argument separator.
# We use S=";" throughout.
S = ";"


def _f(formula: str) -> str:
    """Prefix with = so gspread writes it as a formula."""
    return f"={formula}"


def _build_dashboard_rows() -> list[list]:
    """
    Returns the full dashboard as list of [label, value/formula, note] rows.

    Row layout (sheet row = data index + 2, because row 1 = header):
      Row 2  = title
      Row 34 = Курс USD→UZS (used as rate cell B34)
    """
    U, P, G, D = _U, _P, _G, _D

    # ── Shorthand formula builders ────────────────────────────────────────
    def sumif(rng, crit, sum_rng):
        return f"SUMIF({rng}{S}{crit}{S}{sum_rng})"

    def countif(rng, crit):
        return f"COUNTIF({rng}{S}{crit})"

    def counta(rng):
        return f"COUNTA({rng})"

    def ifn(cond, t, f_):
        return f"IF({cond}{S}{t}{S}{f_})"

    def rnd(val, digits):
        return f"ROUND({val}{S}{digits})"

    def iferr(val, fallback):
        return f"IFERROR({val}{S}{fallback})"

    def avgif(rng, crit, avg_rng):
        return f"AVERAGEIF({rng}{S}{crit}{S}{avg_rng})"

    # ── Cross-tab references ──────────────────────────────────────────────
    # Пользователи
    total_users   = counta(f"{U}!A2:A")
    ref_users     = countif(f"{U}!G2:G", '"<>—"')

    # Оплаты
    rev_ok        = sumif(f"{P}!J2:J", '"✅ Подтверждено"', f"{P}!H2:H")
    rev_topup     = sumif(f"{P}!C2:C", '"💵 Пополнение баланса"', f"{P}!H2:H")
    rev_balance   = sumif(f"{P}!C2:C", '"💸 Оплата с баланса"', f"{P}!H2:H")
    commissions   = sumif(f"{P}!C2:C", '"👥 Реферальная комиссия"', f"{P}!H2:H")
    cnt_ok        = countif(f"{P}!J2:J", '"✅ Подтверждено"')
    cnt_wait      = countif(f"{P}!J2:J", '"⏳ Ожидание"')
    cnt_rej       = countif(f"{P}!J2:J", '"❌ Отклонено"')

    # Генерации
    total_gens    = counta(f"{G}!A2:A")
    ok_gens       = countif(f"{G}!I2:I", '"✅ Готово"')
    fail_gens     = countif(f"{G}!I2:I", '"❌ Ошибка"')
    nb_gens       = countif(f"{G}!F2:F", '"🍌 Nano Banana"')
    kl_gens       = countif(f"{G}!F2:F", '"🎥 Kling"')
    veo_gens      = countif(f"{G}!F2:F", '"🎬 Veo 3"')
    cr_spent      = sumif(f"{G}!I2:I", '"✅ Готово"', f"{G}!H2:H")
    api_sum       = f"SUM({G}!J2:J)"
    avg_time      = iferr(rnd(avgif(f"{G}!I2:I", '"✅ Готово"', f"{G}!K2:K"), "0"), "0")

    # ── Dashboard rows ────────────────────────────────────────────────────
    # Each row: [label, formula/value, unit/note]
    # NOTE: Row 34 of the SHEET = data index 32 = "Курс USD→UZS"
    # (1 header row + 32 data rows before it = row 33... wait let me count)
    # header=row1, data[0]=row2 ... data[32]=row34.  ✓

    rows: list[list] = [
        # data[0] = row 2
        ["📊 HARF AI — МОНИТОРИНГ", _f("NOW()"), "Обновляется при открытии"],
        # data[1] = row 3
        ["", "", ""],

        # ── 👥 ПОЛЬЗОВАТЕЛИ ─────────────────────────────────── row 4-9
        # data[2] = row 4
        ["👥 ПОЛЬЗОВАТЕЛИ", "", ""],
        # data[3] = row 5
        ["Всего зарегистрировано",  _f(total_users),                          "человек"],
        # data[4] = row 6
        ["По реферальной ссылке",   _f(ref_users),                            "человек"],
        # data[5] = row 7
        ["Органика (без реферала)", _f(f"B5-B6"),                             "человек"],
        # data[6] = row 8
        ["Доля рефералов (%)",      _f(ifn("B5>0", rnd("B6/B5*100", "1"), "0")), "%"],
        # data[7] = row 9
        ["", "", ""],

        # ── 💰 ФИНАНСЫ ──────────────────────────────────────── row 10-20
        # data[8] = row 10
        ["💰 ФИНАНСЫ", "", ""],
        # data[9] = row 11
        ["Выручка подтверждена (UZS)", _f(rev_ok),                            "сум"],
        # data[10] = row 12
        ["Выручка (USD)",              _f(iferr(rnd("B11/B34", "2"), "0")),   "$"],
        # data[11] = row 13
        ["Пополнений баланса (UZS)",   _f(rev_topup),                         "сум"],
        # data[12] = row 14
        ["Оплат с баланса (UZS)",      _f(rev_balance),                       "сум"],
        # data[13] = row 15
        ["Оплат подтверждено",         _f(cnt_ok),                            "шт"],
        # data[14] = row 16
        ["Оплат ожидает",              _f(cnt_wait),                          "шт"],
        # data[15] = row 17
        ["Оплат отклонено",            _f(cnt_rej),                           "шт"],
        # data[16] = row 18
        ["Реферальных комиссий (UZS)", _f(commissions),                       "сум"],
        # data[17] = row 19
        ["Средний чек (UZS)",          _f(ifn("B15>0", rnd("B11/B15", "0"), "0")), "сум"],
        # data[18] = row 20
        ["", "", ""],

        # ── 🎨 ГЕНЕРАЦИИ ─────────────────────────────────────── row 21-32
        # data[19] = row 21
        ["🎨 ГЕНЕРАЦИИ", "", ""],
        # data[20] = row 22
        ["Всего задач",              _f(total_gens),                           "шт"],
        # data[21] = row 23
        ["Успешных",                 _f(ok_gens),                              "шт"],
        # data[22] = row 24
        ["Ошибок",                   _f(fail_gens),                            "шт"],
        # data[23] = row 25
        ["В процессе / ожидании",    _f(f"B22-B23-B24"),                       "шт"],
        # data[24] = row 26
        ["Успешность (%)",           _f(ifn("B22>0", rnd("B23/B22*100", "1"), "0")), "%"],
        # data[25] = row 27
        ["🍌 Nano Banana",           _f(nb_gens),                              "генераций"],
        # data[26] = row 28
        ["🎥 Kling",                 _f(kl_gens),                              "генераций"],
        # data[27] = row 29
        ["🎬 Veo 3",                 _f(veo_gens),                             "генераций"],
        # data[28] = row 30
        ["Кредитов потрачено",       _f(cr_spent),                             "кредитов"],
        # data[29] = row 31
        ["Среднее время (сек)",      _f(avg_time),                             "сек"],
        # data[30] = row 32
        ["", "", ""],

        # ── 📊 РАСЧЁТ ПРИБЫЛИ ────────────────────────────────── row 33-44
        # data[31] = row 33
        ["📊 РАСЧЁТ ПРИБЫЛИ", "", ""],
        # data[32] = row 34  ← USD RATE CELL (B34)
        ["Курс USD → UZS",           12700,                                    "← измените при необходимости"],
        # data[33] = row 35
        ["API: Nano Banana ($)",     _f(f"B27*0.004"),                         "$"],
        # data[34] = row 36
        ["API: Kling ($)",           _f(f"B28*0.14"),                          "$"],
        # data[35] = row 37
        ["API: Veo 3 ($)",           _f(f"B29*0.10"),                          "$"],
        # data[36] = row 38
        ["Итого API расходы ($)",    _f(f"B35+B36+B37"),                       "$"],
        # data[37] = row 39
        ["Итого API расходы (UZS)", _f(rnd("B38*B34", "0")),                  "сум"],
        # data[38] = row 40
        ["", "", ""],
        # data[39] = row 41
        ["💰 ПРИБЫЛЬ (UZS)",         _f("B11-B39"),                            "сум"],
        # data[40] = row 42
        ["💰 ПРИБЫЛЬ (USD)",         _f(iferr(rnd("B41/B34", "2"), "0")),      "$"],
        # data[41] = row 43
        ["Маржинальность (%)",       _f(ifn("B11>0", rnd("B41/B11*100", "1"), "0")), "%"],
        # data[42] = row 44
        ["", "", ""],

        # ── 📅 ДНЕВНИК — ИТОГИ ──────────────────────────────── row 45-49
        # data[43] = row 45
        ["📅 ИТОГИ ЗА ВСЁ ВРЕМЯ (из Дневника)", "", ""],
        # data[44] = row 46
        ["Всего новых польз. (из дн.)", _f(f"SUM({D}!B2:B)"),                "человек"],
        # data[45] = row 47
        ["Выручка по дневнику (UZS)",   _f(f"SUM({D}!G2:G)"),                "сум"],
        # data[46] = row 48
        ["API расход по дневнику ($)",  _f(f"SUM({D}!I2:I)"),                "$"],
        # data[47] = row 49
        ["Дней с записями",             _f(counta(f"{D}!A2:A")),              "дней"],
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

        # Build and write all data rows
        # Rate cell = B34 (row 34 = header + 32 data rows before it)
        data_rows = _build_dashboard_rows()
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
