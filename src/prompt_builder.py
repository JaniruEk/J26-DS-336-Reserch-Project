def build_prompt(schema,question):
    prompt = f"""" You are a Text To SQL system.

    Database Schema : {schema}

    Question : {question}

    Generate te correct SQLite SQL query.

    return SQL only.
    
    """

    return prompt