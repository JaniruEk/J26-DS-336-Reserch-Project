import re

def classify_error(gold_sql,generated_sql,execution_error,executed,execution_match):
    if execution_match:
        return "correct"

    if not executed:
        error =(execution_error or "").lower()

        if "syntax error" in error or "incomplete input" in error:
            return "syntax_error"

        if "no such table" in error:
            return "wrong_table"

        if "no such column" in error or "ambiguous column" in error:
            return "wrong_column"

        return "execution_error"

    gold =gold_sql.upper()
    generated = generated_sql.upper() 

    def contains_keyword(sql,keyword):
        return bool(re.search(r"\b" + keyword + r"\b", sql))

    checks =[
        ("wrong_join","JOIN"),
        ("wrong_group_by","GROUP BY"),
        ("wrong_aggregation","COUNT"),
        ("wrong_aggregation","SUM"),
        ("wrong_aggregation","AVG"),
        ("wrong_aggregation","MAX"),
        ("wrong_aggregation","MIN"),
        ("wrong_filter","WHERE"),
        ("wrong_order_by","ORDER BY")
    ]

    for label,keyword in checks:
        if contains_keyword(gold,keyword) != contains_keyword(generated,keyword):
            return label

    return "result_mismatch_unclassified"

