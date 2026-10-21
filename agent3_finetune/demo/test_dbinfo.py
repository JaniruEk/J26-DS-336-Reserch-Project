"""Tests for the demo's database viewer (no torch, no Gradio).
    python -m pytest agent3_finetune/demo/test_dbinfo.py -v
"""
import sqlite3

import pytest

from agent3_finetune.demo.dbinfo import SUGGESTED_QUESTIONS, describe_database, describe_markdown


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "concert_singer.sqlite"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE singer (id INTEGER PRIMARY KEY, name TEXT, note TEXT)")
    con.execute("CREATE TABLE concert (cid INTEGER, singer_id INTEGER REFERENCES singer(id))")
    con.execute('CREATE TABLE "my table" (x INTEGER)')
    con.executemany("INSERT INTO singer VALUES (?, ?, ?)",
                    [(i, f"s{i}", None) for i in range(10)] + [(99, "a|b\nc", "x" * 200)])
    con.executemany("INSERT INTO concert VALUES (?, ?)", [(1, 1), (2, 2)])
    con.execute('INSERT INTO "my table" VALUES (7)')
    con.execute("CREATE TABLE blobby (b BLOB)")
    con.execute("INSERT INTO blobby VALUES (?)", (b"\x00\x01",))
    con.commit()
    con.close()
    return str(p)


def test_tables_columns_counts(db):
    info = describe_database(db)
    names = [t["name"] for t in info["tables"]]
    assert names == sorted(names) and {"singer", "concert", "my table", "blobby"} <= set(names)
    singer = next(t for t in info["tables"] if t["name"] == "singer")
    assert singer["n_rows"] == 11 and [c for c, _ in singer["columns"]] == ["id", "name", "note"]
    assert len(singer["sample"][1]) == 3  # only a few rows are shown


def test_foreign_key_link_is_shown(db):
    concert = next(t for t in describe_database(db)["tables"] if t["name"] == "concert")
    assert concert["links"] == ["singer_id -> singer.id"]


def test_markdown_has_the_basics(db):
    md = describe_markdown(db)
    assert "#### singer (11 rows)" in md and "Columns: id (integer), name (text)" in md
    assert "Links to other tables: singer_id -> singer.id" in md
    assert "Questions you can try:" in md and "How many singers are there?" in md  # file stem = concert_singer
    assert "(binary)" in md and "NULL" in md and "#### my table (1 rows)" in md


def test_awkward_values_do_not_break_the_markdown_table(db):
    md = describe_markdown(db, sample_rows=20)
    row = next(l for l in md.splitlines() if l.startswith("| 99"))
    assert "\\|" in row and "…" in row and "\n" not in row  # pipe escaped, long value cut, newline removed


def test_missing_file_is_a_message_not_a_crash(tmp_path):
    assert "error" in describe_database(tmp_path / "nope.sqlite")
    assert describe_markdown(tmp_path / "nope.sqlite").startswith("**Could not read this database")


def test_not_a_database_is_a_message_not_a_crash(tmp_path):
    p = tmp_path / "bad.sqlite"
    p.write_text("this is not sqlite")
    assert describe_markdown(p).startswith("**Could not read this database")


def test_database_is_not_modified(db):
    before = open(db, "rb").read()
    describe_markdown(db)
    assert open(db, "rb").read() == before


def test_suggestions_are_for_the_four_demo_databases():
    assert set(SUGGESTED_QUESTIONS) == {"concert_singer", "world_1", "car_1", "chinook"}
    assert all(qs and all(q.strip() for q in qs) for qs in SUGGESTED_QUESTIONS.values())
