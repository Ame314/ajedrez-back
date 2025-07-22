from fastapi import APIRouter, Request
from models.lesson_eval import LessonEval

router = APIRouter()

@router.post("/lecciones-eval")
async def create_lesson_eval(request: Request, lesson_eval: LessonEval):
    db = request.app.state.db
    data = lesson_eval.dict()
    result = await db.lesson_evals.insert_one(data)
    return {"mensaje": "Lección de evaluación guardada", "id": str(result.inserted_id)}

@router.get("/lecciones-eval")
async def get_lesson_evals(request: Request):
    db = request.app.state.db
    lesson_evals = await db.lesson_evals.find().to_list(100)
    for item in lesson_evals:
        item["_id"] = str(item["_id"])  # para evitar error ObjectId en JSON
    return lesson_evals
