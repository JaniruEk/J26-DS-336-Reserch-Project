"""One read-only door to any database. A db is either a SQLite file path (the research datasets: unchanged
behaviour, so all earlier numbers reproduce) or a SQLAlchemy URL for a server database, e.g.
postgresql+psycopg://readonly_user:***@dbhost/bank. Everything that touches data goes through `query`.
Read-only is enforced by the connection (SQLite mode=ro; PostgreSQL: read-only session default + READ ONLY
transaction), only ONE statement is ever executed per call (a `SELECT 1; COMMIT; DELETE ...` string would otherwise
end the read-only transaction - found and fixed 18 Oct 2026), and every server transaction is rolled back.
A login with SELECT-only privileges is still REQUIRED in deployment: it is the backstop for every dialect."""
import re
import sqlite3
import time
from contextlib import contextmanager, nullcontext
from functools import lru_cache


class DBError(Exception):
    """Any database error, whatever the driver."""


def is_url(db):
    return "://" in str(db)


def redact(db):
    """Safe to show or log: hides the password in a URL, also inside error text. Greedy up to the LAST '@' of the
    token, so a password containing '@' is hidden completely."""
    return re.sub(r"(://[^:/@\s]+:)\S*@", r"\1***@", str(db))


ENFORCED = ("postgresql",)  # server dialects whose read-only mode, one-statement rule and timeout this module enforces


@lru_cache(maxsize=None)
def _engine(url):
    from sqlalchemy import create_engine, make_url
    backend = make_url(url).get_backend_name()
    if backend not in ENFORCED:  # ponytail: add MySQL/SQL Server/Oracle only with their own read-only + timeout session setup
        raise DBError(f"'{backend}' databases are not supported yet: read-only access is only enforced for SQLite and PostgreSQL")
    return create_engine(url, pool_pre_ping=True, connect_args={"options": "-c default_transaction_read_only=on",
                                                                    "connect_timeout": 10})  # unreachable host: fail, don't hang


_HIDDEN = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|--[^\n]*|/\*.*?\*/", re.S)


def single_statement(sql):
    """True if `sql` is one statement (a trailing ';' is fine). Semicolons inside strings/comments don't count;
    PostgreSQL $$-quoted text with ';' is rejected - the safe direction."""
    return ";" not in _HIDDEN.sub(" ", sql).strip().rstrip(";")


def _server_error(e):
    return DBError(redact(str(getattr(e, "orig", None) or e).strip().splitlines()[0]))


@contextmanager
def session(db, timeout=10):
    """One read-only connection for several statements (value linking runs dozens of tiny probes per question).
    Yields run(sql, params=None) -> (column names, rows as tuples). Named params (:name) work for both kinds."""
    if not is_url(db):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        deadline = time.time() + timeout
        con.set_progress_handler(lambda: time.time() > deadline, 10000)  # abort runaway queries

        def run(sql, params=None):
            try:
                cur = con.execute(sql, params or {})
                return [d[0] for d in cur.description or []], cur.fetchall()
            except (sqlite3.Error, sqlite3.Warning) as e:  # Python < 3.11 raises Warning for multiple statements
                raise DBError(str(e)) from e
        try:
            yield run
        finally:
            con.close()
        return
    from sqlalchemy import exc, text
    eng = _engine(db)
    pg = eng.dialect.name == "postgresql"
    try:
        con = eng.connect()
        if pg:
            con.exec_driver_sql("SET TRANSACTION READ ONLY")
            con.exec_driver_sql(f"SET LOCAL statement_timeout = {int(timeout * 1000)}")
        # ponytail: no portable timeout for other dialects; set one on the read-only DB account
    except exc.SQLAlchemyError as e:
        raise _server_error(e) from e

    def run(sql, params=None):
        if not single_statement(sql):
            raise DBError("only one SQL statement is allowed")
        try:
            # PostgreSQL aborts the whole transaction on any error; a savepoint keeps one failed probe from ending the session
            with (con.begin_nested() if pg else nullcontext()):
                if params:  # internal probes with bound values
                    res = con.execute(text(sql), params)
                    return (list(res.keys()), [tuple(r) for r in res]) if res.returns_rows else ([], [])
                if pg:  # prepared statement: the server itself refuses a second command (belt and braces)
                    cur = con.connection.driver_connection.cursor()
                    cur.execute(sql, prepare=True)
                    return ([d.name for d in cur.description], [tuple(r) for r in cur.fetchall()]) if cur.description else ([], [])
                res = con.exec_driver_sql(sql)
                return (list(res.keys()), [tuple(r) for r in res]) if res.returns_rows else ([], [])
        except exc.SQLAlchemyError as e:
            raise _server_error(e) from e
        except Exception as e:  # psycopg errors raised by the raw cursor
            if type(e).__module__.startswith("psycopg"):
                raise DBError(redact(str(e).strip().splitlines()[0])) from e
            raise
    try:
        yield run
    finally:
        con.rollback()  # never commit anything
        con.close()


def query(db, sql, params=None, timeout=10):
    """Run one statement read-only -> (column names, rows as tuples)."""
    with session(db, timeout) as run:
        return run(sql, params)


def dialect(db):
    """Human name of the SQL dialect, for the generator prompt ('SQLite', 'PostgreSQL', ...)."""
    if not is_url(db):
        return "SQLite"
    name = _engine(db).dialect.name
    return {"postgresql": "PostgreSQL", "mysql": "MySQL", "mariadb": "MariaDB", "mssql": "SQL Server", "oracle": "Oracle"}.get(name, name)


def quote(db, name):
    """Quote an identifier for this database."""
    if not is_url(db):
        return '"' + name.replace('"', '""') + '"'
    return _engine(db).dialect.identifier_preparer.quote(name)


def tables_with_rows(db, names):
    return any(query(db, f"SELECT 1 FROM {quote(db, t)} LIMIT 1")[1] for t in names)


def reflect_url(url, Table):
    """Tables, columns and FKs from the server's catalog via SQLAlchemy's inspector (default schema).
    ponytail: one schema only; add a schema= option when a bank keeps tables in several schemas."""
    from sqlalchemy import exc, inspect
    try:
        insp = inspect(_engine(url))
    except exc.SQLAlchemyError as e:  # unreachable server / bad credentials
        raise DBError(redact(str(getattr(e, "orig", None) or e).strip().splitlines()[0])) from e
    out = {}
    for n in insp.get_table_names():
        pk = set(insp.get_pk_constraint(n).get("constrained_columns") or [])
        cols = [(c["name"], str(c["type"]), c["name"] in pk) for c in insp.get_columns(n)]
        fks = [(col, fk["referred_table"], ref) for fk in insp.get_foreign_keys(n)
               for col, ref in zip(fk["constrained_columns"], fk["referred_columns"])]
        out[n] = Table(n, cols, fks)
    return out
