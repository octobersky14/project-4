import uuid
from mini_gradescope import database as db
from mini_gradescope.models import Submission
from mini_gradescope.services import assignment_service


class AssignmentNotFound(Exception):
    pass


def submit(assignment_id: str, student_id: str, content: str) -> dict:
    if not assignment_service.get_assignment(assignment_id):
        raise AssignmentNotFound(f"Assignment '{assignment_id}' does not exist.")

    submission = Submission(
        id=str(uuid.uuid4()),
        assignment_id=assignment_id,
        student_id=student_id,
        content=content,
    )
    db.insert("submissions", submission)
    return db.get("submissions", submission.id)


def get_submission(submission_id: str) -> dict | None:
    return db.get("submissions", submission_id)


def list_submissions(assignment_id: str | None = None) -> list[dict]:
    if assignment_id:
        return db.find("submissions", assignment_id=assignment_id)
    return db.all_records("submissions")


def list_student_submissions(student_id: str) -> list[dict]:
    return db.find("submissions", student_id=student_id)
