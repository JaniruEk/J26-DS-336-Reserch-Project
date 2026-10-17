from schema_utils import get_schema

db_path = "data/spider_data/spider_data/database/company_office/company_office.sqlite"

schema = get_schema(db_path)
print(schema)