import uuid
from mini_gradescope import database as db
from mini_gradescope.models import Assignment


def create_assignment(title: str, description: str, max_score: float) -> Assignment:
    assignment = Assignment(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        max_score=max_score,
    )
    db.insert("assignments", assignment)
    return assignment


def get_assignment(assignment_id: str) -> dict | None:
    return db.get("assignments", assignment_id)


def list_assignments() -> list[dict]:
    return db.all_records("assignments")
