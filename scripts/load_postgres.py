"""Copy a SQLite research database (schema, PKs, FKs, rows) into PostgreSQL, to test Agent 1 on a server database.
Table and column names are lower-cased: PostgreSQL folds unquoted names to lower case, so generated SQL like
`SELECT Name FROM Track` only works against lower-case identifiers.
Usage: python -m scripts.load_postgres data/chinook.db postgresql+psycopg://user:pw@localhost:5432/chinook [--keep-case]
--keep-case keeps the SQLite names exactly (quoted identifiers) - used to check the adapter gives SQLite-identical retrieval."""
import sys

from sqlalchemy import Column, ForeignKeyConstraint, MetaData, Table, create_engine, inspect


def copy(sqlite_path, url, keep_case=False):
    low = (lambda n: n) if keep_case else str.lower
    src, dst = create_engine(f"sqlite:///{sqlite_path}"), create_engine(url)
    insp, meta = inspect(src), MetaData()
    for name in insp.get_table_names():
        pk = set(insp.get_pk_constraint(name)["constrained_columns"])
        # as_generic(): SQLite's DATETIME/NVARCHAR become types PostgreSQL understands
        cols = [Column(low(c["name"]), c["type"].as_generic(), primary_key=c["name"] in pk) for c in insp.get_columns(name)]
        fks = [ForeignKeyConstraint([low(c) for c in fk["constrained_columns"]],
                                    [f"{low(fk['referred_table'])}.{low(c)}" for c in fk["referred_columns"]])
               for fk in insp.get_foreign_keys(name)]
        Table(low(name), meta, *cols, *fks)
    meta.drop_all(dst)
    meta.create_all(dst)
    with src.connect() as s, dst.begin() as d:
        for t in meta.sorted_tables:  # parents before children, so FKs hold
            src_name = next(n for n in insp.get_table_names() if low(n) == t.name)
            rows = [{low(k): v for k, v in r._mapping.items()} for r in s.exec_driver_sql(f'SELECT * FROM "{src_name}"')]
            if rows:
                d.execute(t.insert(), rows)
            print(f"{t.name}: {len(rows)} rows")


if __name__ == "__main__":
    copy(sys.argv[1], sys.argv[2], "--keep-case" in sys.argv)
