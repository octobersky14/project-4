#!/usr/bin/env python3
"""Grader CLI for mini-Gradescope."""
import argparse
import sys
import json
from datetime import datetime

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from mini_gradescope.services import assignment_service, submission_service, grading_service
from mini_gradescope.services.results_service import get_all_results, get_results_for_submission
from mini_gradescope.services.grading_service import SubmissionNotFound, AlreadyGraded


def _ts(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def _parse_scores(raw: list[str]) -> dict[str, float]:
    scores = {}
    for item in raw:
        if "=" not in item:
            print(f"Error: score item '{item}' must be in 'rubric_item=points' format.")
            sys.exit(1)
        key, val = item.split("=", 1)
        try:
            scores[key.strip()] = float(val.strip())
        except ValueError:
            print(f"Error: points value '{val}' is not a number.")
            sys.exit(1)
    return scores


def cmd_create_assignment(args):
    a = assignment_service.create_assignment(args.title, args.description, args.max_score)
    print(f"Assignment created.")
    print(f"  ID          : {a.id}")
    print(f"  Title       : {a.title}")
    print(f"  Description : {a.description}")
    print(f"  Max score   : {a.max_score}")


def cmd_list_submissions(args):
    subs = submission_service.list_submissions(args.assignment_id)
    if not subs:
        print("No submissions found.")
        return
    print(f"{'Submission ID':<38} {'Student':<20} {'Submitted':<20} Graded?")
    print("-" * 90)
    for s in subs:
        grade = grading_service.get_grade_for_submission(s["id"])
        graded = f"Yes ({grade['overall_grade']})" if grade else "No"
        print(f"{s['id']:<38} {s['student_id']:<20} {_ts(s['submitted_at']):<20} {graded}")


def cmd_view_submission(args):
    sub = submission_service.get_submission(args.submission_id)
    if not sub:
        print(f"Error: submission '{args.submission_id}' not found.")
        sys.exit(1)
    asgn = assignment_service.get_assignment(sub["assignment_id"])
    grade = grading_service.get_grade_for_submission(args.submission_id)

    print(f"Submission : {sub['id']}")
    print(f"Student    : {sub['student_id']}")
    print(f"Assignment : {asgn['title'] if asgn else sub['assignment_id']}")
    print(f"Submitted  : {_ts(sub['submitted_at'])}")
    print(f"\n--- Content ---\n{sub['content']}\n--- End ---")

    if grade:
        print(f"\nGraded by  : {grade['grader_id']} at {_ts(grade['graded_at'])}")
        print(f"Score      : {grade['total_score']} / {asgn['max_score'] if asgn else '?'}")
        print(f"Grade      : {grade['overall_grade']}")
        print(f"Feedback   : {grade['feedback']}")
        if grade["scores"]:
            print("Rubric     :")
            for item, pts in grade["scores"].items():
                print(f"  {item}: {pts}")
    else:
        print("\n(Not yet graded)")


def cmd_grade(args):
    scores = _parse_scores(args.scores)
    try:
        g = grading_service.grade_submission(args.submission_id, args.grader_id, scores, args.feedback)
    except SubmissionNotFound as e:
        print(f"Error: {e}")
        sys.exit(1)
    except AlreadyGraded as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Graded successfully.")
    print(f"  Grade ID    : {g['id']}")
    print(f"  Total score : {g['total_score']}")
    print(f"  Grade       : {g['overall_grade']}")
    print(f"  Feedback    : {g['feedback']}")


def cmd_update_grade(args):
    scores = _parse_scores(args.scores)
    try:
        g = grading_service.update_grade(args.submission_id, args.grader_id, scores, args.feedback)
    except SubmissionNotFound as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Grade updated.")
    print(f"  Total score : {g['total_score']}")
    print(f"  Grade       : {g['overall_grade']}")
    print(f"  Feedback    : {g['feedback']}")


def cmd_all_results(args):
    results = get_all_results()
    if not results:
        print("No submissions found.")
        return
    for r in results:
        sub = r["submission"]
        asgn = r["assignment"]
        grade = r["grade"]
        title = asgn["title"] if asgn else sub["assignment_id"]
        status = f"{grade['total_score']}/{asgn['max_score']} ({grade['overall_grade']})" if grade else "Ungraded"
        print(f"[{title}] student={sub['student_id']}  sub={sub['id'][:8]}...  {status}")


def main():
    parser = argparse.ArgumentParser(description="mini-Gradescope: Grader CLI")
    cmds = parser.add_subparsers(dest="command", required=True)

    # create-assignment
    p_ca = cmds.add_parser("create-assignment", help="Create a new assignment")
    p_ca.add_argument("title", help="Assignment title")
    p_ca.add_argument("description", help="Assignment description")
    p_ca.add_argument("max_score", type=float, help="Maximum possible score")

    # list-submissions
    p_ls = cmds.add_parser("list-submissions", help="List submissions")
    p_ls.add_argument("--assignment-id", help="Filter by assignment ID")

    # view-submission
    p_vs = cmds.add_parser("view-submission", help="View a submission's content and grade")
    p_vs.add_argument("submission_id", help="Submission ID")

    # grade
    p_g = cmds.add_parser("grade", help="Grade a submission")
    p_g.add_argument("grader_id", help="Your grader ID")
    p_g.add_argument("submission_id", help="Submission ID to grade")
    p_g.add_argument("--scores", nargs="+", required=True,
                     metavar="ITEM=POINTS",
                     help="Rubric scores e.g. --scores correctness=40 style=10")
    p_g.add_argument("--feedback", required=True, help="Written feedback for the student")

    # update-grade
    p_ug = cmds.add_parser("update-grade", help="Update an existing grade")
    p_ug.add_argument("grader_id", help="Your grader ID")
    p_ug.add_argument("submission_id", help="Submission ID to re-grade")
    p_ug.add_argument("--scores", nargs="+", required=True, metavar="ITEM=POINTS")
    p_ug.add_argument("--feedback", required=True, help="Updated feedback")

    # all-results
    cmds.add_parser("all-results", help="View all submissions and their grades")

    args = parser.parse_args()
    {
        "create-assignment": cmd_create_assignment,
        "list-submissions": cmd_list_submissions,
        "view-submission": cmd_view_submission,
        "grade": cmd_grade,
        "update-grade": cmd_update_grade,
        "all-results": cmd_all_results,
    }[args.command](args)


if __name__ == "__main__":
    main()
