"""Demo (Agent 3): show the panel what is INSIDE a database (tables, columns, links, a few rows).

Read-only (SQLite URI mode=ro), 5-second limit per query, never raises: a problem becomes a short message.
No torch, no Gradio: testable anywhere.
"""
import sqlite3
import time
from pathlib import Path

SAMPLE_ROWS = 3
MAX_CELL = 40          # characters shown per cell
TIMEOUT_S = 5.0

# Questions the panel can try on each demo database. They come from the saved evaluation set or the demo
# examples; nothing here says what the right answer is.
SUGGESTED_QUESTIONS = {
    "concert_singer": ["How many singers are there?",
                       "What are the names of the singers who performed in a concert in 2014?"],
    "world_1": ["What is the average life expectancy of the countries in Asia?",
                "What are the names and areas of countries with the top 5 largest area?"],
    "car_1": ["What is the horsepower of the car with the largest accelerate?",
              "What is the maximum accelerate for all the different cylinders?"],
    "chinook": ["List all artist names.",
                "List the titles of all albums by the artist AC/DC.",
                "What is the total revenue per billing country?"],
}


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


def _cell(v):
    if v is None:
        return "NULL"
    if isinstance(v, (bytes, bytearray)):
        return "(binary)"
    s = str(v).replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    return s if len(s) <= MAX_CELL else s[:MAX_CELL - 1] + "…"


def describe_database(db_path, sample_rows=SAMPLE_ROWS):
    """{'tables': [{'name', 'columns': [(name, type)], 'links': ['col -> table.col'], 'n_rows', 'sample': (cols, rows)}]}
    or {'error': message}."""
    con = None
    try:
        path = Path(db_path).resolve()
        if not path.exists():
            return {"error": f"database file not found ({path.name})"}
        con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        con.text_factory = lambda b: b.decode("utf-8", errors="replace")
        deadline = time.time() + TIMEOUT_S
        con.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10000)
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        tables = []
        for n in names:
            cols = [(r[1], r[2] or "") for r in con.execute(f"PRAGMA table_info({_quote(n)})")]
            links = [f"{r[3]} -> {r[2]}.{r[4]}" for r in con.execute(f"PRAGMA foreign_key_list({_quote(n)})")]
            try:
                n_rows = con.execute(f"SELECT COUNT(*) FROM {_quote(n)}").fetchone()[0]
                cur = con.execute(f"SELECT * FROM {_quote(n)} LIMIT {int(sample_rows)}")
                sample = ([d[0] for d in cur.description], [list(r) for r in cur.fetchall()])
            except sqlite3.Error:
                n_rows, sample = None, ([], [])
            tables.append({"name": n, "columns": cols, "links": links, "n_rows": n_rows, "sample": sample})
        return {"tables": tables}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass


def describe_markdown(db_path, db_name=None, sample_rows=SAMPLE_ROWS):
    """The same information as Markdown for the screen."""
    info = describe_database(db_path, sample_rows)
    if "error" in info:
        return f"**Could not read this database:** {info['error']}"
    if not info["tables"]:
        return "This database has no tables."
    lines = [f"**{len(info['tables'])} tables.** Read-only: nothing here can be changed.", ""]
    qs = SUGGESTED_QUESTIONS.get(db_name or Path(db_path).stem)
    if qs:
        lines += ["**Questions you can try:**"] + [f"- {q}" for q in qs] + [""]
    for t in info["tables"]:
        n = "?" if t["n_rows"] is None else f"{t['n_rows']:,}"
        lines.append(f"#### {t['name']} ({n} rows)")
        lines.append("Columns: " + ", ".join(f"{c} ({ty.lower()})" if ty else c for c, ty in t["columns"]))
        if t["links"]:
            lines.append("")
            lines.append("Links to other tables: " + "; ".join(t["links"]))
        cols, rows = t["sample"]
        if cols and rows:
            lines += ["", "| " + " | ".join(_cell(c) for c in cols) + " |", "|" + "---|" * len(cols)]
            lines += ["| " + " | ".join(_cell(v) for v in r) + " |" for r in rows]
        lines.append("")
    return "\n".join(lines)
