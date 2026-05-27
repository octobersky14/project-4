#!/usr/bin/env python3
"""Grader CLI for mini-Gradescope.

Roles
-----
--role ta          Default. Can grade and view submissions, but student identity
                   is hidden on assignments marked anonymous_grading=True.
--role instructor  Full access. Always sees real student identities. Only role
                   that can create assignments or enable anonymous grading.
"""
import argparse
import sys
from datetime import datetime

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from mini_gradescope.services import assignment_service, submission_service, grading_service
from mini_gradescope.services.results_service import (
    get_all_results,
    get_results_for_submission,
    AccessDenied,
    InsufficientRole,
)
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
    if args.role != "instructor":
        print("Error: only instructors can create assignments.")
        sys.exit(1)
    a = assignment_service.create_assignment(
        args.title, args.description, args.max_score,
        anonymous_grading=args.anonymous,
    )
    print(f"Assignment created.")
    print(f"  ID               : {a.id}")
    print(f"  Title            : {a.title}")
    print(f"  Description      : {a.description}")
    print(f"  Max score        : {a.max_score}")
    print(f"  Anonymous grading: {a.anonymous_grading}")


def cmd_list_submissions(args):
    subs = submission_service.list_submissions(args.assignment_id)
    if not subs:
        print("No submissions found.")
        return

    from mini_gradescope.anonymization import should_anonymize, anonymize_submission
    from mini_gradescope.services import assignment_service as asgn_svc

    print(f"{'Submission ID':<38} {'Student':<24} {'Submitted':<20} Graded?")
    print("-" * 95)
    for s in subs:
        asgn = asgn_svc.get_assignment(s["assignment_id"])
        display = anonymize_submission(s, asgn) if should_anonymize(asgn, args.role) else s
        grade = grading_service.get_grade_for_submission(s["id"])
        graded = f"Yes ({grade['overall_grade']})" if grade else "No"
        print(f"{display['id']:<38} {display['student_id']:<24} {_ts(s['submitted_at']):<20} {graded}")


def cmd_view_submission(args):
    try:
        r = get_results_for_submission(args.submission_id, args.grader_id, args.role)
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
    print(f"Student    : {sub['student_id']}")
    print(f"Assignment : {asgn['title'] if asgn else sub['assignment_id']}")
    if asgn and asgn.get("anonymous_grading") and args.role != "instructor":
        print(f"             [anonymous grading enabled — identity hidden]")
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
    try:
        results = get_all_results(role=args.role)
    except InsufficientRole as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not results:
        print("No submissions found.")
        return
    for r in results:
        sub = r["submission"]
        asgn = r["assignment"]
        grade = r["grade"]
        title = asgn["title"] if asgn else sub["assignment_id"]
        anon_flag = " [anon]" if (asgn and asgn.get("anonymous_grading")) else ""
        status = f"{grade['total_score']}/{asgn['max_score']} ({grade['overall_grade']})" if grade else "Ungraded"
        print(f"[{title}{anon_flag}] student={sub['student_id']}  sub={sub['id'][:8]}...  {status}")


def main():
    # Shared role argument inherited by every subcommand
    role_parent = argparse.ArgumentParser(add_help=False)
    role_parent.add_argument(
        "--role", choices=["ta", "instructor"], default="ta",
        help="Your role (default: ta). Instructors have full access; "
             "TAs see anonymized data on blind-graded assignments.",
    )

    parser = argparse.ArgumentParser(description="mini-Gradescope: Grader/Instructor CLI")
    cmds = parser.add_subparsers(dest="command", required=True)

    # create-assignment  [instructor only]
    p_ca = cmds.add_parser("create-assignment", parents=[role_parent],
                            help="Create a new assignment (instructor only)")
    p_ca.add_argument("title")
    p_ca.add_argument("description")
    p_ca.add_argument("max_score", type=float)
    p_ca.add_argument("--anonymous", action="store_true",
                      help="Enable anonymous grading for this assignment")

    # list-submissions
    p_ls = cmds.add_parser("list-submissions", parents=[role_parent],
                            help="List submissions (student identity hidden for TAs on anon assignments)")
    p_ls.add_argument("--assignment-id", dest="assignment_id",
                      help="Filter by assignment ID")

    # view-submission
    p_vs = cmds.add_parser("view-submission", parents=[role_parent],
                            help="View a submission's content and grade")
    p_vs.add_argument("grader_id", help="Your grader/instructor ID")
    p_vs.add_argument("submission_id")

    # grade
    p_g = cmds.add_parser("grade", parents=[role_parent], help="Grade a submission")
    p_g.add_argument("grader_id")
    p_g.add_argument("submission_id")
    p_g.add_argument("--scores", nargs="+", required=True, metavar="ITEM=POINTS")
    p_g.add_argument("--feedback", required=True)

    # update-grade
    p_ug = cmds.add_parser("update-grade", parents=[role_parent],
                            help="Update an existing grade")
    p_ug.add_argument("grader_id")
    p_ug.add_argument("submission_id")
    p_ug.add_argument("--scores", nargs="+", required=True, metavar="ITEM=POINTS")
    p_ug.add_argument("--feedback", required=True)

    # all-results
    cmds.add_parser("all-results", parents=[role_parent],
                    help="View all submissions and grades")

    args = parser.parse_args()
    {
        "create-assignment": cmd_create_assignment,
        "list-submissions":  cmd_list_submissions,
        "view-submission":   cmd_view_submission,
        "grade":             cmd_grade,
        "update-grade":      cmd_update_grade,
        "all-results":       cmd_all_results,
    }[args.command](args)


if __name__ == "__main__":
    main()
