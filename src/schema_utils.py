import sqlite3


def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name from sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """
    )

    tables = cursor.fetchall()

    schema_parts =[]

    for (table_name,) in tables:
        cursor.execute (f'PRAGMA table_info("{table_name}")')
        columns = cursor.fetchall()

        column_names = [column[1] for column in columns]

        schema_parts.append(
            f"{table_name}({', '.join(column_names)})"
        )

    conn.close()
    
    return "\n".join(schema_parts)


