"""
Anonymization layer for anonymous-grading assignments.

When an assignment has anonymous_grading=True, TAs must not be able to
identify which student produced a submission. This module enforces that
at the data level before any output reaches the CLI.

Strategy:
- Replace student_id with a deterministic but non-reversible token
  derived from sha256(student_id + ":" + assignment_id).
- The token is consistent: the same student always maps to the same
  token within a given assignment, so a grader can distinguish
  submissions without knowing identities.
- Cross-assignment correlation is prevented because the token changes
  per assignment.
- Instructors bypass anonymization entirely.
"""
import hashlib
import copy


def anon_token(student_id: str, assignment_id: str) -> str:
    raw = f"{student_id}:{assignment_id}".encode()
    return "anon-" + hashlib.sha256(raw).hexdigest()[:12]


def should_anonymize(assignment: dict | None, role: str) -> bool:
    if role == "instructor":
        return False
    return bool(assignment and assignment.get("anonymous_grading"))


def anonymize_submission(submission: dict, assignment: dict | None) -> dict:
    """Return a copy of submission with student_id replaced by anon token."""
    s = copy.deepcopy(submission)
    s["student_id"] = anon_token(submission["student_id"], submission["assignment_id"])
    return s
