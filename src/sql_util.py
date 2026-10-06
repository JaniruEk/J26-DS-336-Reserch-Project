def clean_sql(genrated_text):
    generated_text =  genrated_text.strip()

    generated_text =generated_text.replace("```sql","")
    generated_text=generated_text.replace("```SQL","")
    generated_text=generated_text.replace("```","")

    generated_text=generated_text.strip()

    return generated_text