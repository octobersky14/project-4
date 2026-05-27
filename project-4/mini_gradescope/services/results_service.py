from mini_gradescope import database as db
from mini_gradescope.services import submission_service, grading_service, assignment_service


class AccessDenied(Exception):
    pass


def _enrich(submission: dict) -> dict:
    grade = grading_service.get_grade_for_submission(submission["id"])
    assignment = assignment_service.get_assignment(submission["assignment_id"])
    return {
        "submission": submission,
        "assignment": assignment,
        "grade": grade,
    }


def get_results_for_student(student_id: str) -> list[dict]:
    submissions = submission_service.list_student_submissions(student_id)
    return [_enrich(s) for s in submissions]


def get_results_for_submission(submission_id: str, requester_id: str, role: str) -> dict:
    submission = submission_service.get_submission(submission_id)
    if not submission:
        raise KeyError(f"Submission '{submission_id}' not found.")

    if role == "student" and submission["student_id"] != requester_id:
        raise AccessDenied("Students may only view their own submission results.")

    return _enrich(submission)


def get_all_results() -> list[dict]:
    submissions = db.all_records("submissions")
    return [_enrich(s) for s in submissions]
