"""Schema reflection: tables, columns and FK graph read live from the DB catalog (no hardcoded schema)."""
import re
import sqlite3
from dataclasses import dataclass


@dataclass
class Table:
    name: str
    columns: list  # (name, type, is_pk)
    fks: list  # (column, parent_table, parent_column)


def reflect(db_path):
    """db_path: SQLite file, or a SQLAlchemy URL for a server database (see db.py)."""
    from .db import is_url, reflect_url
    if is_url(db_path):
        return reflect_url(db_path, Table)
    con = sqlite3.connect(db_path)
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {
            n: Table(
                n,
                [(r[1], r[2], bool(r[5])) for r in con.execute(f'PRAGMA table_info("{n}")')],
                [(r[3], r[2], r[4]) for r in con.execute(f'PRAGMA foreign_key_list("{n}")')],
            )
            for n in names
        }
    finally:
        con.close()


def infer_fks(tables):
    """Add FKs implied by naming when a column is not declared as one (opt-in; returns what was added).
    Rules: (1) same name as another table's single-column PK (CustomerId); (2) <table>_id / <table>Id;
    (3) TPC-H style prefixes, l_orderkey -> o_orderkey. A column that is its table's only PK is never an FK."""
    def norm(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())

    def strip(s):
        m = re.match(r"^[A-Za-z]{1,3}_(.+)$", s)
        return (m.group(1) if m else s).lower()

    pk = {n: [c for c, _, p in t.columns if p] for n, t in tables.items()}
    single = {n: cs[0] for n, cs in pk.items() if len(cs) == 1}
    by_pk, by_stripped = {}, {}
    for n, c in single.items():
        by_pk.setdefault(c.lower(), []).append(n)
        if strip(c) != c.lower():
            by_stripped.setdefault(strip(c), []).append(n)
    by_name = {norm(n): n for n in tables}
    by_name.update({norm(n)[:-1]: n for n in tables if norm(n).endswith("s")})
    added = []
    for n, t in tables.items():
        declared = {c for c, _, _ in t.fks}
        for c, _, is_pk in t.columns:
            if c in declared or (is_pk and len(pk[n]) == 1):
                continue
            owners = [o for o in by_pk.get(c.lower(), []) if o != n]
            if len(owners) != 1:
                m = re.match(r"^(.+?)_?(id|key)$", c, re.I)
                o = by_name.get(norm(m.group(1))) if m else None
                owners = [o] if o and o != n and o in single else []
            if not owners and strip(c) != c.lower():
                owners = [o for o in by_stripped.get(strip(c), []) if o != n]
            if len(owners) == 1:
                t.fks.append((c, owners[0], single[owners[0]]))
                added.append((n, c, owners[0]))
    return added


def adjacency(tables):
    """Undirected FK graph. Missing/dangling FKs just yield fewer edges (never an error)."""
    adj = {n: set() for n in tables}
    for t in tables.values():
        for _, parent, _ in t.fks:
            if parent in tables:
                adj[t.name].add(parent)
                adj[parent].add(t.name)
    return adj


def ident(name):
    """Quote a name only when it needs it ("Order Details"); plain names stay bare, so earlier token counts reproduce.
    Unquoted, the model reads `Order Details` as two words and writes `OrderDetails` or a syntax error (Northwind)."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else '"' + name.replace('"', '""') + '"'


def render(table, keep=None, notes=None):
    """Render a table (optionally only `keep` columns) as DDL. One renderer for every mode keeps token counts comparable.
    notes: column -> text shown as a /* comment */ after it (sample values, glossary meaning); None = original output."""
    keep = {c for c, _, _ in table.columns} if keep is None else set(keep)
    notes = notes or {}
    lines = [f"{ident(c)} {typ}{' PRIMARY KEY' if pk else ''}".strip() + (f" /* {notes[c]} */" if c in notes else "")
             for c, typ, pk in table.columns if c in keep]
    lines += [f"FOREIGN KEY ({ident(c)}) REFERENCES {ident(p)}({ident(pc)})" if pc else f"FOREIGN KEY ({ident(c)}) REFERENCES {ident(p)}"
              for c, p, pc in table.fks if c in keep]
    return f"CREATE TABLE {ident(table.name)} (\n  " + ",\n  ".join(lines) + "\n);"
