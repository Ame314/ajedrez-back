import json
from pymongo import MongoClient

docs_to_insert = []

with open("utils/lichess_db_eval.jsonl", "r") as f:
    for _, line in zip(range(1000), f):
        line = line.strip()
        if not line:
            continue  # Salta líneas vacías
        try:
            docs_to_insert.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"Error al leer línea (saltada): {line[:50]}...")
            continue

client = MongoClient("mongodb://mongo:27017")
db = client.ajedrez_db
db.lesson_evals.insert_many(docs_to_insert)
print(f"{len(docs_to_insert)} evaluaciones cargadas.")
