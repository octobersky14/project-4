#!/usr/bin/env python3
"""Student CLI for mini-Gradescope."""
import argparse
import sys
import json
from datetime import datetime

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from mini_gradescope.services import assignment_service, submission_service
from mini_gradescope.services.results_service import get_results_for_student, get_results_for_submission, AccessDenied
from mini_gradescope.services.submission_service import AssignmentNotFound


def _ts(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def cmd_list_assignments(args):
    assignments = assignment_service.list_assignments()
    if not assignments:
        print("No assignments available.")
        return
    print(f"{'ID':<38} {'Title':<25} {'Max Score'}")
    print("-" * 72)
    for a in assignments:
        print(f"{a['id']:<38} {a['title']:<25} {a['max_score']}")


def cmd_submit(args):
    if args.file:
        try:
            with open(args.file) as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: file '{args.file}' not found.")
            sys.exit(1)
    else:
        print("Enter submission content (end with a line containing only '.'):")
        lines = []
        while True:
            line = input()
            if line == ".":
                break
            lines.append(line)
        content = "\n".join(lines)

    try:
        sub = submission_service.submit(args.assignment_id, args.student_id, content)
    except AssignmentNotFound as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Submitted successfully.")
    print(f"  Submission ID : {sub['id']}")
    print(f"  Assignment    : {sub['assignment_id']}")
    print(f"  Submitted at  : {_ts(sub['submitted_at'])}")


def cmd_my_results(args):
    results = get_results_for_student(args.student_id)
    if not results:
        print("No submissions found.")
        return
    for r in results:
        sub = r["submission"]
        asgn = r["assignment"]
        grade = r["grade"]
        title = asgn["title"] if asgn else sub["assignment_id"]
        print(f"\nAssignment : {title}")
        print(f"  Submission ID : {sub['id']}")
        print(f"  Submitted     : {_ts(sub['submitted_at'])}")
        if grade:
            print(f"  Score         : {grade['total_score']} / {asgn['max_score'] if asgn else '?'}")
            print(f"  Grade         : {grade['overall_grade']}")
            print(f"  Feedback      : {grade['feedback']}")
            if grade["scores"]:
                print("  Rubric scores :")
                for item, pts in grade["scores"].items():
                    print(f"    {item}: {pts}")
        else:
            print("  Grade         : (not yet graded)")


def cmd_view_submission(args):
    try:
        r = get_results_for_submission(args.submission_id, args.student_id, "student")
    except KeyError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except AccessDenied as e:
        print(f"Access denied: {e}")
        sys.exit(1)

    sub = r["submission"]
    asgn = r["assignment"]
    grade = r["grade"]
    print(f"Submission : {sub['id']}")
    print(f"Assignment : {asgn['title'] if asgn else sub['assignment_id']}")
    print(f"Submitted  : {_ts(sub['submitted_at'])}")
    print(f"Content    :\n{sub['content']}")
    if grade:
        print(f"\nScore      : {grade['total_score']} / {asgn['max_score'] if asgn else '?'}")
        print(f"Grade      : {grade['overall_grade']}")
        print(f"Feedback   : {grade['feedback']}")
    else:
        print("\nGrade      : (not yet graded)")


def main():
    parser = argparse.ArgumentParser(description="mini-Gradescope: Student CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # list-assignments
    sub.add_parser("list-assignments", help="List all available assignments")

    # submit
    p_sub = sub.add_parser("submit", help="Submit work for an assignment")
    p_sub.add_argument("student_id", help="Your student ID")
    p_sub.add_argument("assignment_id", help="Assignment ID to submit to")
    p_sub.add_argument("--file", help="Path to file to submit (omit to type inline)")

    # my-results
    p_res = sub.add_parser("my-results", help="View results for all your submissions")
    p_res.add_argument("student_id", help="Your student ID")

    # view-submission
    p_view = sub.add_parser("view-submission", help="View a specific submission and its grade")
    p_view.add_argument("student_id", help="Your student ID")
    p_view.add_argument("submission_id", help="Submission ID to view")

    args = parser.parse_args()
    {
        "list-assignments": cmd_list_assignments,
        "submit": cmd_submit,
        "my-results": cmd_my_results,
        "view-submission": cmd_view_submission,
    }[args.command](args)


if __name__ == "__main__":
    main()
