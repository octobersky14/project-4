import uuid
from mini_gradescope import database as db
from mini_gradescope.models import Grade
from mini_gradescope.services import submission_service, assignment_service


class SubmissionNotFound(Exception):
    pass


class AlreadyGraded(Exception):
    pass


def _letter_grade(pct: float) -> str:
    if pct >= 93:
        return "A"
    if pct >= 90:
        return "A-"
    if pct >= 87:
        return "B+"
    if pct >= 83:
        return "B"
    if pct >= 80:
        return "B-"
    if pct >= 77:
        return "C+"
    if pct >= 73:
        return "C"
    if pct >= 70:
        return "C-"
    if pct >= 60:
        return "D"
    return "F"


def grade_submission(
    submission_id: str,
    grader_id: str,
    scores: dict[str, float],
    feedback: str,
) -> dict:
    submission = submission_service.get_submission(submission_id)
    if not submission:
        raise SubmissionNotFound(f"Submission '{submission_id}' does not exist.")

    existing = db.find("grades", submission_id=submission_id)
    if existing:
        raise AlreadyGraded(
            f"Submission '{submission_id}' has already been graded. "
            "Use update_grade to modify it."
        )

    assignment = assignment_service.get_assignment(submission["assignment_id"])
    total_score = sum(scores.values())
    max_score = assignment["max_score"] if assignment else total_score
    pct = (total_score / max_score * 100) if max_score else 0

    grade = Grade(
        id=str(uuid.uuid4()),
        submission_id=submission_id,
        grader_id=grader_id,
        scores=scores,
        total_score=total_score,
        feedback=feedback,
        overall_grade=_letter_grade(pct),
    )
    db.insert("grades", grade)
    return db.get("grades", grade.id)


def update_grade(
    submission_id: str,
    grader_id: str,
    scores: dict[str, float],
    feedback: str,
) -> dict:
    submission = submission_service.get_submission(submission_id)
    if not submission:
        raise SubmissionNotFound(f"Submission '{submission_id}' does not exist.")

    existing = db.find("grades", submission_id=submission_id)
    assignment = assignment_service.get_assignment(submission["assignment_id"])
    total_score = sum(scores.values())
    max_score = assignment["max_score"] if assignment else total_score
    pct = (total_score / max_score * 100) if max_score else 0

    if existing:
        import time
        record = existing[0]
        record.update(
            grader_id=grader_id,
            scores=scores,
            total_score=total_score,
            feedback=feedback,
            overall_grade=_letter_grade(pct),
            graded_at=time.time(),
        )
        data = db._load("grades")
        data[record["id"]] = record
        db._save("grades", data)
        return record

    return grade_submission(submission_id, grader_id, scores, feedback)


def get_grade_for_submission(submission_id: str) -> dict | None:
    results = db.find("grades", submission_id=submission_id)
    return results[0] if results else None
