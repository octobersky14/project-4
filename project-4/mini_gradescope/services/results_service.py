from mini_gradescope import database as db
from mini_gradescope.anonymization import should_anonymize, anonymize_submission
from mini_gradescope.services import submission_service, grading_service, assignment_service


class AccessDenied(Exception):
    pass


class InsufficientRole(Exception):
    pass


def _enrich(submission: dict, role: str) -> dict:
    assignment = assignment_service.get_assignment(submission["assignment_id"])
    grade = grading_service.get_grade_for_submission(submission["id"])

    if should_anonymize(assignment, role):
        submission = anonymize_submission(submission, assignment)

    return {
        "submission": submission,
        "assignment": assignment,
        "grade": grade,
    }


def get_results_for_student(student_id: str) -> list[dict]:
    submissions = submission_service.list_student_submissions(student_id)
    # Students always see their own real data
    return [_enrich(s, "instructor") for s in submissions]


def get_results_for_submission(submission_id: str, requester_id: str, role: str) -> dict:
    submission = submission_service.get_submission(submission_id)
    if not submission:
        raise KeyError(f"Submission '{submission_id}' not found.")

    if role == "student":
        if submission["student_id"] != requester_id:
            raise AccessDenied("Students may only view their own submission results.")
        return _enrich(submission, "instructor")  # students see their own real data

    if role not in ("ta", "instructor"):
        raise AccessDenied(f"Unknown role '{role}'.")

    return _enrich(submission, role)


def get_all_results(role: str = "instructor") -> list[dict]:
    if role == "student":
        raise InsufficientRole("Students cannot list all results.")
    submissions = db.all_records("submissions")
    return [_enrich(s, role) for s in submissions]
