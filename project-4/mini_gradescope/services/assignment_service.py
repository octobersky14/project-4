import uuid
from mini_gradescope import database as db
from mini_gradescope.models import Assignment


def create_assignment(
    title: str,
    description: str,
    max_score: float,
    anonymous_grading: bool = False,
) -> Assignment:
    assignment = Assignment(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        max_score=max_score,
        anonymous_grading=anonymous_grading,
    )
    db.insert("assignments", assignment)
    return assignment


def get_assignment(assignment_id: str) -> dict | None:
    return db.get("assignments", assignment_id)


def list_assignments() -> list[dict]:
    return db.all_records("assignments")
