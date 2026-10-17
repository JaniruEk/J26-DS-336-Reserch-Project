"""Schema reflection: tables, columns and FK graph read live from the DB catalog (no hardcoded schema)."""
import sqlite3
from dataclasses import dataclass


@dataclass
class Table:
    name: str
    columns: list  # (name, type, is_pk)
    fks: list  # (column, parent_table, parent_column)


def reflect(db_path):
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


def adjacency(tables):
    """Undirected FK graph. Missing/dangling FKs just yield fewer edges (never an error)."""
    adj = {n: set() for n in tables}
    for t in tables.values():
        for _, parent, _ in t.fks:
            if parent in tables:
                adj[t.name].add(parent)
                adj[parent].add(t.name)
    return adj


def render(table, keep=None):
    """Render a table (optionally only `keep` columns) as DDL. One renderer for every mode keeps token counts comparable."""
    keep = {c for c, _, _ in table.columns} if keep is None else set(keep)
    lines = [f"{c} {typ}{' PRIMARY KEY' if pk else ''}".strip()
             for c, typ, pk in table.columns if c in keep]
    lines += [f"FOREIGN KEY ({c}) REFERENCES {p}({pc})" if pc else f"FOREIGN KEY ({c}) REFERENCES {p}"
              for c, p, pc in table.fks if c in keep]
    return f"CREATE TABLE {table.name} (\n  " + ",\n  ".join(lines) + "\n);"
