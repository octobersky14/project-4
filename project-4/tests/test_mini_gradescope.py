"""Integration tests for mini-Gradescope."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mini_gradescope import database as db
from mini_gradescope.services import assignment_service, submission_service, grading_service
from mini_gradescope.services.results_service import (
    get_results_for_student,
    get_results_for_submission,
    get_all_results,
    AccessDenied,
)
from mini_gradescope.services.submission_service import AssignmentNotFound
from mini_gradescope.services.grading_service import SubmissionNotFound, AlreadyGraded


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    yield


@pytest.fixture
def assignment():
    return assignment_service.create_assignment("HW1", "Write a hello-world program", 100)


@pytest.fixture
def submission(assignment):
    return submission_service.submit(assignment.id, "alice", "print('hello world')")


# ── Assignment Service ────────────────────────────────────────────────────────

class TestAssignmentService:
    def test_create_and_retrieve(self):
        a = assignment_service.create_assignment("HW1", "desc", 50)
        fetched = assignment_service.get_assignment(a.id)
        assert fetched["title"] == "HW1"
        assert fetched["max_score"] == 50

    def test_list_assignments(self):
        assignment_service.create_assignment("HW1", "d", 50)
        assignment_service.create_assignment("HW2", "d", 100)
        assert len(assignment_service.list_assignments()) == 2

    def test_get_nonexistent_returns_none(self):
        assert assignment_service.get_assignment("bad-id") is None


# ── Submission Service ────────────────────────────────────────────────────────

class TestSubmissionService:
    def test_submit_creates_record(self, assignment):
        sub = submission_service.submit(assignment.id, "alice", "my work")
        assert sub["student_id"] == "alice"
        assert sub["assignment_id"] == assignment.id

    def test_submit_invalid_assignment_raises(self):
        with pytest.raises(AssignmentNotFound):
            submission_service.submit("no-such-id", "alice", "work")

    def test_list_submissions_filtered_by_assignment(self, assignment):
        a2 = assignment_service.create_assignment("HW2", "d", 50)
        submission_service.submit(assignment.id, "alice", "a")
        submission_service.submit(a2.id, "bob", "b")
        subs = submission_service.list_submissions(assignment_id=assignment.id)
        assert len(subs) == 1
        assert subs[0]["student_id"] == "alice"

    def test_list_student_submissions(self, assignment):
        submission_service.submit(assignment.id, "alice", "a")
        submission_service.submit(assignment.id, "bob", "b")
        alice_subs = submission_service.list_student_submissions("alice")
        assert len(alice_subs) == 1


# ── Grading Service ───────────────────────────────────────────────────────────

class TestGradingService:
    def test_grade_submission(self, submission, assignment):
        scores = {"correctness": 85, "style": 10}
        g = grading_service.grade_submission(submission["id"], "grader1", scores, "Good work!")
        assert g["total_score"] == 95
        assert g["overall_grade"] == "A"

    def test_grade_computes_letter(self, submission):
        g = grading_service.grade_submission(submission["id"], "g", {"q": 70}, "ok")
        assert g["overall_grade"] == "C-"

    def test_grade_nonexistent_submission_raises(self):
        with pytest.raises(SubmissionNotFound):
            grading_service.grade_submission("bad-id", "g", {"q": 10}, "x")

    def test_double_grading_raises(self, submission):
        grading_service.grade_submission(submission["id"], "g", {"q": 10}, "x")
        with pytest.raises(AlreadyGraded):
            grading_service.grade_submission(submission["id"], "g", {"q": 10}, "x")

    def test_update_grade(self, submission):
        grading_service.grade_submission(submission["id"], "g", {"q": 60}, "ok")
        updated = grading_service.update_grade(submission["id"], "g", {"q": 90}, "better")
        assert updated["total_score"] == 90
        assert updated["feedback"] == "better"

    def test_get_grade_for_submission(self, submission):
        assert grading_service.get_grade_for_submission(submission["id"]) is None
        grading_service.grade_submission(submission["id"], "g", {"q": 80}, "good")
        grade = grading_service.get_grade_for_submission(submission["id"])
        assert grade is not None
        assert grade["total_score"] == 80


# ── Results Service ───────────────────────────────────────────────────────────

class TestResultsService:
    def test_student_sees_own_results(self, assignment, submission):
        grading_service.grade_submission(submission["id"], "g", {"q": 90}, "nice")
        results = get_results_for_student("alice")
        assert len(results) == 1
        assert results[0]["grade"]["overall_grade"] == "A-"

    def test_student_cannot_view_others_submission(self, assignment, submission):
        with pytest.raises(AccessDenied):
            get_results_for_submission(submission["id"], "bob", "student")

    def test_grader_can_view_any_submission(self, assignment, submission):
        r = get_results_for_submission(submission["id"], "grader1", "grader")
        assert r["submission"]["id"] == submission["id"]

    def test_all_results_for_grader(self, assignment):
        submission_service.submit(assignment.id, "alice", "a")
        submission_service.submit(assignment.id, "bob", "b")
        results = get_all_results()
        assert len(results) == 2

    def test_ungraded_submission_shows_none_grade(self, submission):
        results = get_results_for_student("alice")
        assert results[0]["grade"] is None

    def test_result_includes_assignment_metadata(self, submission):
        results = get_results_for_student("alice")
        assert results[0]["assignment"]["title"] == "HW1"
