from fastapi import APIRouter, Request

router = APIRouter()

def clean_document(doc):
    doc['_id'] = str(doc['_id'])
    return doc

@router.get("/puzzles")
async def get_puzzles(request: Request):
    db = request.app.state.db
    puzzles_cursor = db.puzzles.find().limit(50)
    puzzles = await puzzles_cursor.to_list(length=50)
    return [clean_document(p) for p in puzzles]
