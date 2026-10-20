
import re
import sqlite3


def normalize_sql(sql):
    sql = sql.strip().rstrip(";").lower()
    return re.sub(r"\s+", " ", sql)


def calculate_em(gold_sql, generated_sql):
    return int(
        normalize_sql(gold_sql) ==
        normalize_sql(generated_sql)
    )


def execute_query(db_path, sql):
    # Open SQLite in read-only mode
    connection = sqlite3.connect(
        db_path.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=10
    )
    try:
        connection.execute("PRAGMA query_only = ON")

        # Restrict evaluation to SELECT queries
        if not re.match(
            r"^\s*(SELECT|WITH)\b",
            sql,
            flags=re.IGNORECASE
        ):
            raise ValueError("Only SELECT/WITH queries allowed")

        cursor = connection.execute(sql)
        return cursor.fetchall()
    finally:
        connection.close()


def calculate_ex(db_path, gold_sql, generated_sql):
    try:
        gold_result = execute_query(db_path, gold_sql)
        generated_result = execute_query(db_path, generated_sql)

        return int(gold_result == generated_result)
    except Exception:
        return 0
