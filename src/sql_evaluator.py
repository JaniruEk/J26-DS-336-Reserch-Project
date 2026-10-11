import sqlite3
from collections import Counter

def is_Safe_select (sql):
    """Allow only a single read-only select/with query"""

    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        return False

    if not cleaned.upper().startswith(("SELECT","WITH")):
        return False

    # Return multiple Statement
    if ";" in cleaned:
        return False

    return True


def execute_sql(db_path,sql):
    """Execute SQL and return its result or an error"""

    if not is_Safe_select(sql):
        return{
            "executed":False,
            "rows":None,
            "error":"Only a single SELECT/WITH query is allowed"
        }

    connection =None

    try:
        connection =sqlite3.connect(
            f"file:{db_path.resolve().as_posix()}?mode=ro",
            uri=True,
            timeout=10
        )

        # Limit SQLite exection using a progress handler
        steps=[0]

        def progress():
            steps[0] += 1
            return 1 if steps[0]>10000 else 0

        connection.set_progress_handler(progress,1000)

        cursor = connection.cursor()
        cursor.execute(sql)
        rows=cursor.fetchmany(10001)

        if len(rows)>10000:
            raise RuntimeError("Result exceeds 10000 rows")

        return{
            "executed":True,
            "rows":rows,
            "error":None
        }

    except (sqlite3.Error,RuntimeError) as e:
        return{
            "executed":False,
            "rows":None,
            "error":str(e)
        }

    finally:
        if connection is not None:
            connection.close()


def normalize_rows(rows):
    """Comapre result rows without depending on row order"""

    return Counter(
        tuple(repr(value) for value in row)
        for row in rows
    )


def comapre_sql(db_path,gold_sql,generated_sql):
    gold = execute_sql(db_path,gold_sql)
    predicted = execute_sql(db_path,generated_sql)

    match=(
        gold["executed"] and predicted["executed"]
        and normalize_rows(gold["rows"])== normalize_rows(predicted["rows"])
    )

    return{
        "gold_executed":gold["executed"],
        "executed":predicted["executed"],
        "execution_match": bool(match),
        "gold_error":gold["error"],
        "execution_error":predicted["error"]
    }