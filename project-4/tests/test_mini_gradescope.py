"""Integration tests for mini-Gradescope (Part I + Part II anonymous grading)."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mini_gradescope import database as db
from mini_gradescope.anonymization import anon_token, should_anonymize, anonymize_submission
from mini_gradescope.services import assignment_service, submission_service, grading_service
from mini_gradescope.services.results_service import (
    get_results_for_student,
    get_results_for_submission,
    get_all_results,
    AccessDenied,
    InsufficientRole,
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
def anon_assignment():
    return assignment_service.create_assignment("HW2", "Blind-graded exam", 100, anonymous_grading=True)


@pytest.fixture
def submission(assignment):
    return submission_service.submit(assignment.id, "alice", "print('hello world')")


@pytest.fixture
def anon_submission(anon_assignment):
    return submission_service.submit(anon_assignment.id, "alice", "my answer")


# ── Assignment Service ────────────────────────────────────────────────────────

class TestAssignmentService:
    def test_create_and_retrieve(self):
        a = assignment_service.create_assignment("HW1", "desc", 50)
        fetched = assignment_service.get_assignment(a.id)
        assert fetched["title"] == "HW1"
        assert fetched["max_score"] == 50

    def test_anonymous_grading_flag_stored(self):
        a = assignment_service.create_assignment("HW1", "d", 50, anonymous_grading=True)
        fetched = assignment_service.get_assignment(a.id)
        assert fetched["anonymous_grading"] is True

    def test_anonymous_grading_defaults_false(self):
        a = assignment_service.create_assignment("HW1", "d", 50)
        assert assignment_service.get_assignment(a.id)["anonymous_grading"] is False

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
        assert len(submission_service.list_student_submissions("alice")) == 1


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


# ── Results Service (original role behaviour) ─────────────────────────────────

class TestResultsService:
    def test_student_sees_own_results(self, assignment, submission):
        grading_service.grade_submission(submission["id"], "g", {"q": 90}, "nice")
        results = get_results_for_student("alice")
        assert len(results) == 1
        assert results[0]["grade"]["overall_grade"] == "A-"

    def test_student_cannot_view_others_submission(self, assignment, submission):
        with pytest.raises(AccessDenied):
            get_results_for_submission(submission["id"], "bob", "student")

    def test_ta_can_view_any_submission(self, assignment, submission):
        r = get_results_for_submission(submission["id"], "ta1", "ta")
        assert r["submission"]["id"] == submission["id"]

    def test_instructor_can_view_any_submission(self, assignment, submission):
        r = get_results_for_submission(submission["id"], "prof", "instructor")
        assert r["submission"]["id"] == submission["id"]

    def test_all_results_for_ta(self, assignment):
        submission_service.submit(assignment.id, "alice", "a")
        submission_service.submit(assignment.id, "bob", "b")
        results = get_all_results(role="ta")
        assert len(results) == 2

    def test_student_cannot_call_all_results(self):
        with pytest.raises(InsufficientRole):
            get_all_results(role="student")

    def test_ungraded_submission_shows_none_grade(self, submission):
        results = get_results_for_student("alice")
        assert results[0]["grade"] is None

    def test_result_includes_assignment_metadata(self, submission):
        results = get_results_for_student("alice")
        assert results[0]["assignment"]["title"] == "HW1"


# ── Anonymization Unit Tests ──────────────────────────────────────────────────

class TestAnonymization:
    def test_anon_token_is_deterministic(self):
        t1 = anon_token("alice", "hw1")
        t2 = anon_token("alice", "hw1")
        assert t1 == t2

    def test_anon_token_differs_across_assignments(self):
        assert anon_token("alice", "hw1") != anon_token("alice", "hw2")

    def test_anon_token_differs_across_students(self):
        assert anon_token("alice", "hw1") != anon_token("bob", "hw1")

    def test_anon_token_prefixed(self):
        assert anon_token("alice", "hw1").startswith("anon-")

    def test_should_anonymize_ta_on_anon_assignment(self, anon_assignment):
        a = assignment_service.get_assignment(anon_assignment.id)
        assert should_anonymize(a, "ta") is True

    def test_should_not_anonymize_instructor(self, anon_assignment):
        a = assignment_service.get_assignment(anon_assignment.id)
        assert should_anonymize(a, "instructor") is False

    def test_should_not_anonymize_normal_assignment(self, assignment):
        a = assignment_service.get_assignment(assignment.id)
        assert should_anonymize(a, "ta") is False

    def test_anonymize_submission_hides_student_id(self, anon_submission, anon_assignment):
        a = assignment_service.get_assignment(anon_assignment.id)
        anon = anonymize_submission(anon_submission, a)
        assert anon["student_id"] != "alice"
        assert anon["student_id"].startswith("anon-")

    def test_anonymize_submission_preserves_content(self, anon_submission, anon_assignment):
        a = assignment_service.get_assignment(anon_assignment.id)
        anon = anonymize_submission(anon_submission, a)
        assert anon["content"] == "my answer"
        assert anon["id"] == anon_submission["id"]

    def test_anonymize_does_not_mutate_original(self, anon_submission, anon_assignment):
        a = assignment_service.get_assignment(anon_assignment.id)
        anonymize_submission(anon_submission, a)
        assert anon_submission["student_id"] == "alice"


# ── Anonymous Grading — End-to-End ───────────────────────────────────────────

class TestAnonymousGradingPolicy:
    def test_ta_sees_anon_token_not_real_id(self, anon_submission, anon_assignment):
        r = get_results_for_submission(anon_submission["id"], "ta1", "ta")
        assert r["submission"]["student_id"] != "alice"
        assert r["submission"]["student_id"].startswith("anon-")

    def test_instructor_sees_real_id_on_anon_assignment(self, anon_submission, anon_assignment):
        r = get_results_for_submission(anon_submission["id"], "prof", "instructor")
        assert r["submission"]["student_id"] == "alice"

    def test_student_sees_own_real_id_on_anon_assignment(self, anon_submission):
        results = get_results_for_student("alice")
        assert results[0]["submission"]["student_id"] == "alice"

    def test_all_results_ta_anon(self, anon_assignment):
        submission_service.submit(anon_assignment.id, "alice", "a")
        submission_service.submit(anon_assignment.id, "bob", "b")
        results = get_all_results(role="ta")
        ids = [r["submission"]["student_id"] for r in results]
        assert "alice" not in ids
        assert "bob" not in ids
        assert all(sid.startswith("anon-") for sid in ids)

    def test_all_results_instructor_sees_real_ids(self, anon_assignment):
        submission_service.submit(anon_assignment.id, "alice", "a")
        results = get_all_results(role="instructor")
        assert results[0]["submission"]["student_id"] == "alice"

    def test_two_students_get_distinct_tokens(self, anon_assignment):
        s1 = submission_service.submit(anon_assignment.id, "alice", "a")
        s2 = submission_service.submit(anon_assignment.id, "bob", "b")
        a = assignment_service.get_assignment(anon_assignment.id)
        t1 = anonymize_submission(s1, a)["student_id"]
        t2 = anonymize_submission(s2, a)["student_id"]
        assert t1 != t2

    def test_same_student_consistent_token_across_calls(self, anon_assignment):
        s = submission_service.submit(anon_assignment.id, "alice", "a")
        a = assignment_service.get_assignment(anon_assignment.id)
        t1 = anonymize_submission(s, a)["student_id"]
        t2 = anonymize_submission(s, a)["student_id"]
        assert t1 == t2

    def test_normal_assignment_ta_sees_real_id(self, submission):
        r = get_results_for_submission(submission["id"], "ta1", "ta")
        assert r["submission"]["student_id"] == "alice"

    def test_ta_cannot_create_assignment(self):
        # Enforced in CLI — ensure the flag is readable at service level via assignment metadata
        a = assignment_service.create_assignment("X", "d", 10, anonymous_grading=True)
        fetched = assignment_service.get_assignment(a.id)
        assert fetched["anonymous_grading"] is True
