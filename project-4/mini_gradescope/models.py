from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class Assignment:
    id: str
    title: str
    description: str
    max_score: float
    created_at: float = field(default_factory=time.time)


@dataclass
class Submission:
    id: str
    assignment_id: str
    student_id: str
    content: str
    submitted_at: float = field(default_factory=time.time)


@dataclass
class Grade:
    id: str
    submission_id: str
    grader_id: str
    scores: dict[str, float]   # rubric_item -> points
    total_score: float
    feedback: str
    overall_grade: str         # letter grade
    graded_at: float = field(default_factory=time.time)
