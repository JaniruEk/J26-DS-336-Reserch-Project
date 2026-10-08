def clean_sql(generated_text):
    generated_text =  generated_text.strip()

    generated_text =generated_text.replace("```sql","")
    generated_text=generated_text.replace("```SQL","")
    generated_text=generated_text.replace("```","")

    generated_text=generated_text.strip()

    return generated_text