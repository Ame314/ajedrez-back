
import pandas as pd
from pymongo import MongoClient

df = pd.read_csv('lichess_db_puzzle.csv')

client = MongoClient("mongodb://mongo:27017")
db = client.ajedrez_db

puzzles = df[["PuzzleId", "FEN", "Moves", "Rating", "Themes", "GameUrl"]].to_dict(orient='records')
db.puzzles.insert_many(puzzles)
print("Puzzles cargados exitosamente.")