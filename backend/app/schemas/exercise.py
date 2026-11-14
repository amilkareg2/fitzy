import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import LoadType


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    equipment: str | None
    load_type: LoadType
    default_rest_s: int | None
    archived: bool
