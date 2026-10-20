"""Demo (Agent 3): run model-generated SQL safely.

Rules (from the demo spec):
  * database opened READ-ONLY (file:<path>?mode=ro)
  * a single SELECT (or WITH ... SELECT) only
  * 5-second timeout (SQLite progress handler)
  * at most 20 rows returned
  * every exception caught and turned into a friendly message
No torch, no transformers: testable on the laptop.
"""
import sqlite3
import time
from pathlib import Path

MAX_ROWS = 20
TIMEOUT_S = 5.0


def check_select(sql):
    """Return (ok, cleaned_sql_or_reason). Accepts one SELECT / WITH statement only.

    A ';' inside a string literal is also rejected (simple and safe; rare in generated SQL).
    """
    s = (sql or "").strip()
    while s.endswith(";"):
        s = s[:-1].rstrip()
    if not s:
        return False, "The model produced no SQL."
    if ";" in s:
        return False, "More than one SQL statement was produced; only a single SELECT is allowed."
    first = s.split(None, 1)[0].lower()
    if first not in ("select", "with"):
        return False, f"Only SELECT queries are allowed (the model produced '{first.upper()}')."
    return True, s


def run_query(db_path, sql, max_rows=MAX_ROWS, timeout_s=TIMEOUT_S):
    """Run `sql` on the SQLite file read-only. Never raises. Returns a dict:
    ok, status (plain English), columns, rows, truncated, seconds."""
    t0 = time.time()
    out = {"ok": False, "status": "", "columns": [], "rows": [], "truncated": False, "seconds": 0.0}
    ok, s = check_select(sql)
    if not ok:
        out["status"] = "Not run: " + s
        return out
    con = None
    try:
        path = Path(db_path).resolve()
        if not path.exists():
            out["status"] = f"Not run: database file not found ({path.name})."
            return out
        con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode("utf-8", errors="replace")
        deadline = time.time() + timeout_s
        con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10000)
        cur = con.execute(s)
        out["columns"] = [d[0] for d in (cur.description or [])]
        rows = cur.fetchmany(max_rows + 1)
        out["truncated"] = len(rows) > max_rows
        out["rows"] = [list(r) for r in rows[:max_rows]]
        out["ok"] = True
        n = len(out["rows"])
        out["status"] = f"Ran, {n}{'+' if out['truncated'] else ''} row{'s' if n != 1 else ''}"
    except sqlite3.OperationalError as e:
        msg = str(e)
        if "interrupted" in msg.lower():
            out["status"] = f"Failed: the query took longer than {timeout_s:g} seconds and was stopped."
        else:
            out["status"] = f"Failed: {msg}"
    except Exception as e:  # anything else: stay friendly
        out["status"] = f"Failed: {type(e).__name__}: {e}"
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass
        out["seconds"] = round(time.time() - t0, 2)
    return out
