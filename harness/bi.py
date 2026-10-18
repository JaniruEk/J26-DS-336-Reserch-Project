"""BI integration ("explore, then promote"): a chat answer an analyst trusts is saved with its SQL frozen, then replayed
by BI tools without the model. Saved answers live in a local SQLite file; dashboards read GET /answers/{id}.csv
or a Superset chart created from the same SQL. The language model is never on the dashboard refresh path."""
import csv
import io
import json
import os
import re
import sqlite3
import time
from decimal import Decimal

NUMERIC = (int, float, Decimal)  # server databases return NUMERIC sums as Decimal


def chart_hint(columns, rows):
    """Rule-based chart suggestion for a result: 'number', 'line', 'bar' or 'table'."""
    if not rows or not columns:
        return "table"
    if len(columns) == 1 and len(rows) == 1 and isinstance(rows[0][0], NUMERIC):
        return "number"
    if len(columns) == 2 and all(isinstance(r[1], NUMERIC) for r in rows) and not all(isinstance(r[0], NUMERIC) for r in rows):
        return "line" if re.search(r"date|month|year|day|week|time|period", columns[0], re.I) else "bar"
    return "table"


def _cell(v):
    """Neutralise spreadsheet formulas (CSV injection): a text cell starting with = + - @ tab or CR gets a leading quote.
    Numbers are left alone, so -5 stays a number."""
    return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def to_csv(columns, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([_cell(c) for c in columns])
    w.writerows([_cell(v) for v in r] for r in rows)
    return buf.getvalue()


class AnswerStore:
    """Saved answers in a local SQLite file. ponytail: one file, no users/roles; add the bank's SSO + an analyst role before real use."""

    def __init__(self, path):
        self.path = path
        with self._con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL, question TEXT,
                         db TEXT, sql TEXT, columns TEXT, chart TEXT, superset_chart_id INTEGER)""")

    def _con(self):
        return sqlite3.connect(self.path)

    def add(self, question, db, sql, columns, chart):
        with self._con() as c:
            cur = c.execute("INSERT INTO answers (created, question, db, sql, columns, chart) VALUES (?,?,?,?,?,?)",
                            (time.time(), question, db, sql, json.dumps(columns), chart))
            return cur.lastrowid

    def get(self, answer_id):
        with self._con() as c:
            c.row_factory = sqlite3.Row
            r = c.execute("SELECT * FROM answers WHERE id = ?", (answer_id,)).fetchone()
        return None if r is None else {**dict(r), "columns": json.loads(r["columns"])}

    def all(self):
        with self._con() as c:
            c.row_factory = sqlite3.Row
            return [{**dict(r), "columns": json.loads(r["columns"])} for r in c.execute("SELECT * FROM answers ORDER BY id DESC")]

    def set_superset(self, answer_id, chart_id):
        with self._con() as c:
            c.execute("UPDATE answers SET superset_chart_id = ? WHERE id = ?", (chart_id, answer_id))


def superset_config():
    """Superset connection from env vars; None when not fully configured (the endpoint then answers 501).
    SUPERSET_DATABASES maps our db keys to Superset database ids, e.g. '{"chinook": 1}'.
    No default credentials: use a dedicated low-privilege Superset account that can only create datasets/charts,
    and a Superset database connection that logs in with a SELECT-only database user."""
    url, user, password = (os.environ.get(k) for k in ("SUPERSET_URL", "SUPERSET_USER", "SUPERSET_PASSWORD"))
    if not (url and user and password):
        return None
    return {"url": url.rstrip("/"), "user": user,
            "password": password,
            "databases": json.loads(os.environ.get("SUPERSET_DATABASES", "{}"))}


# Superset 6 viz ids (legacy dist_bar/line were removed in Superset 5+).
VIZ = {"bar": "echarts_timeseries_bar", "line": "echarts_timeseries_line", "number": "big_number_total", "table": "table"}


def superset_chart(ds, chart, columns):
    """-> (form_data params, query_context) for a chart on dataset `ds`. query_context lets /api/v1/chart/{id}/data render it headlessly."""
    metric = lambda col: {"expressionType": "SQL", "sqlExpression": f'SUM("{col}")', "label": col}
    params = {"viz_type": VIZ[chart], "datasource": f"{ds}__table"}
    if chart in ("bar", "line"):
        m = metric(columns[1])
        params |= {"x_axis": columns[0], "xAxisForceCategorical": True, "metrics": [m], "groupby": [], "row_limit": 1000}
        order = [[m, False]] if chart == "bar" else [[columns[0], True]]  # bars by size, lines in x-axis order
        query = {"columns": [columns[0]], "metrics": [m], "orderby": order, "row_limit": 1000}
    elif chart == "number":
        m = metric(columns[0])
        params |= {"metric": m}
        query = {"columns": [], "metrics": [m], "row_limit": 1}
    else:
        params |= {"query_mode": "raw", "all_columns": columns, "row_limit": 1000}
        query = {"columns": columns, "metrics": [], "row_limit": 1000}
    context = {"datasource": {"id": ds, "type": "table"}, "force": False, "queries": [query],
               "form_data": params, "result_format": "json", "result_type": "full"}
    return params, context


def _ok(resp):
    """raise_for_status, but keep Superset's own error message (e.g. 'Dataset already exists')."""
    if resp.is_error:
        raise RuntimeError(f"{resp.request.method} {resp.request.url.path} -> {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def push_to_superset(cfg, answer, client=None):
    """Create a virtual dataset from the saved SQL and a chart on it, via Superset's REST API -> (dataset_id, chart_id, url).
    ponytail: minimal params; verified live on Superset 6.1.0 (bar + big number render via /chart/{id}/data) on 18 Oct 2026."""
    import httpx
    db_id = cfg["databases"].get(answer["db"])
    if db_id is None:
        raise ValueError(f"no Superset database configured for '{answer['db']}' (set SUPERSET_DATABASES)")
    c = client or httpx.Client(base_url=cfg["url"], timeout=30)
    token = _ok(c.post("/api/v1/security/login", json={"username": cfg["user"], "password": cfg["password"],
                                                         "provider": "db", "refresh": True}))["access_token"]
    c.headers["Authorization"] = f"Bearer {token}"
    c.headers["X-CSRFToken"] = _ok(c.get("/api/v1/security/csrf_token/"))["result"]
    c.headers["Referer"] = cfg["url"]
    name = f"answer_{int(answer['id'])}"
    found = _ok(c.get("/api/v1/dataset/", params={"q": f"(filters:!((col:table_name,opr:eq,value:{name})))"}))["result"]
    ds = found[0]["id"] if found else _ok(c.post("/api/v1/dataset/", json={"database": db_id, "table_name": name,
                                                                           "sql": answer["sql"]}))["id"]
    params, context = superset_chart(ds, answer["chart"], answer["columns"])
    chart = _ok(c.post("/api/v1/chart/", json={"slice_name": answer["question"][:250], "viz_type": params["viz_type"],
                                           "datasource_id": ds, "datasource_type": "table", "params": json.dumps(params),
                                           "query_context": json.dumps(context)}))["id"]
    return ds, chart, f"{cfg['url']}/explore/?slice_id={chart}"
