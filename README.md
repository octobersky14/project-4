[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/yuBMyNJ2)

# Project 4: Critical Agentic Coding

A minimal assignment submission and grading system built with Cursor Auto agent mode. Students submit text or source files and view their results. Graders review submissions, assign rubric scores and feedback, and update grades. Scores are summed and converted to an overall letter grade using fixed percentage thresholds.

## Implementations

- `main`: Part I baseline submission and grading system.
- `anonymous-grading`: Part II redesign with optional anonymous assignments and separate TA and instructor views. The implementations remain on separate branches.

Both versions use Python command-line interfaces and local JSON storage; no web server or external database is needed.

## Directory structure

```text
README.md
reflection.md                   # Reflection on main
project-4/
  student.py                    # Student commands
  grader.py                     # Grader/instructor commands
  mini_gradescope/
    models.py                   # Assignment, Submission, and Grade records
    database.py                 # JSON persistence
    anonymization.py            # Part II only: student ID masking
    services/
      assignment_service.py     # Create and retrieve assignments
      submission_service.py     # Store and retrieve submissions
      grading_service.py        # Rubric totals, letter grades, and updates
      results_service.py        # Combine results and apply viewing rules
  tests/test_mini_gradescope.py  # Automated service tests
  data/                         # Created at runtime; ignored by Git
```

On `anonymous-grading`, the reflection is at `project-4/reflection.md`, and the annotated conversation is at `project-4/annotations.pdf`.

## Requirements

Use **Python 3.10 or newer**. Running the application requires only the Python standard library. `pytest` is needed only for the tests.

Run the examples below from the repository root. Replace `ASSIGNMENT_ID` and `SUBMISSION_ID` with the full IDs printed by the create and submit commands. The example names `alice` and `grader1` are user-supplied identifiers.

## Run Part I

Select the baseline branch:

```bash
git switch main
python3 project-4/grader.py create-assignment "HW1" "Write a hello-world program" 100
python3 project-4/student.py list-assignments
```

Submit work interactively, ending with a line containing only `.`:

```bash
python3 project-4/student.py submit alice ASSIGNMENT_ID
```

Alternatively, append `--file path/to/answer.py` to read a text or source file. The system stores its contents; it does not execute or automatically grade submitted code.

Review, grade, and retrieve results:

```bash
python3 project-4/grader.py list-submissions --assignment-id ASSIGNMENT_ID
python3 project-4/grader.py view-submission SUBMISSION_ID
python3 project-4/grader.py grade grader1 SUBMISSION_ID --scores correctness=85 style=10 --feedback "Good work!"
python3 project-4/student.py my-results alice
python3 project-4/student.py view-submission alice SUBMISSION_ID
python3 project-4/grader.py all-results
```

The example totals 95/100 and produces an A. To revise an existing grade, use `update-grade` with the same arguments as `grade`.

## Run Part II

Select the redesign branch and create an anonymous assignment:

```bash
git switch anonymous-grading
python3 project-4/grader.py create-assignment "HW2" "Anonymous submission" 100 --role instructor --anonymous
python3 project-4/student.py submit alice ASSIGNMENT_ID
```

Use the new assignment and submission IDs in these commands:

```bash
python3 project-4/grader.py list-submissions --assignment-id ASSIGNMENT_ID --role ta
python3 project-4/grader.py view-submission grader1 SUBMISSION_ID --role ta
python3 project-4/grader.py grade grader1 SUBMISSION_ID --scores correctness=85 style=10 --feedback "Good work!" --role ta
python3 project-4/grader.py all-results --role ta
python3 project-4/grader.py view-submission instructor1 SUBMISSION_ID --role instructor
python3 project-4/student.py my-results alice
```

Student commands are unchanged. Part II's grader `view-submission` requires a grader ID before the submission ID. Grader commands default to `--role ta`; creating assignments requires `--role instructor`. Omit `--anonymous` to create a regular assignment.

For anonymous assignments, TA views replace the student ID with a stable token that differs by assignment, including after grading. Instructor views always retain the real student ID, and students see their own identifiers and results.

**Implementation limits:** IDs and roles are supplied through command-line arguments without authentication. Stored JSON retains real identities, and masking does not remove identifying information from submission content or timestamps. This prototype demonstrates different views but does not fully enforce the assignment's system-level anonymity requirement.

## Storage and tests

The application creates `assignments.json`, `submissions.json`, and `grades.json` in `project-4/data/`. Data persists between commands and remains in place when switching branches in the same checkout.

To run the tests for the currently selected branch:

```bash
python3 -m venv project-4/.venv
source project-4/.venv/bin/activate
python3 -m pip install pytest
python3 -m pytest project-4/tests -q
```

Tests use temporary storage rather than the application's saved data. For command options, run `python3 project-4/student.py --help` or `python3 project-4/grader.py --help`.
