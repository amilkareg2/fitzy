from fastapi import APIRouter

from app.api.deps import OwnerDep, SessionDep
from app.schemas.exercise import ExerciseOut
from app.services.exercises import list_exercises

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("")
def get_exercises(
    session: SessionDep, _owner: OwnerDep, include_archived: bool = False
) -> list[ExerciseOut]:
    return [
        ExerciseOut.model_validate(e)
        for e in list_exercises(session, include_archived=include_archived)
    ]
