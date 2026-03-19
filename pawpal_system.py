from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Owner:
    name: str
    day_start: str  # "HH:MM"
    day_end: str    # "HH:MM"
    # available_minutes removed — derived from day_start/day_end to avoid silent conflicts

    def total_available_minutes(self) -> int:
        """Return total minutes between day_start and day_end."""
        pass


@dataclass
class Pet:
    name: str
    species: str            # "dog" | "cat" | "other"
    age_years: float
    special_needs: list[str] = field(default_factory=list)

    def is_senior(self) -> bool:
        """Return True if the pet is considered senior for its species."""
        pass

    def summary(self) -> str:
        """Return a short human-readable description of the pet."""
        pass


@dataclass
class Task:
    title: str
    category: str           # walk | feed | medication | enrichment | grooming | vet
    duration_minutes: int
    priority: str           # low | medium | high | critical
    earliest_start: Optional[str] = None   # "HH:MM" or None
    deadline: Optional[str] = None         # "HH:MM" or None
    notes: str = ""

    def is_mandatory(self) -> bool:
        """Return True if this task must be scheduled (critical priority or has a deadline)."""
        pass

    def has_deadline(self) -> bool:
        """Return True if this task has a hard deadline."""
        pass


@dataclass
class ScheduledTask:
    task: Task
    start_time: str     # "HH:MM"
    end_time: str       # "HH:MM"
    reason: str

    def duration_minutes(self) -> int:
        """Return the duration of this scheduled task in minutes."""
        pass


@dataclass
class DailyPlan:
    owner: Owner
    pet: Pet
    date: str
    scheduled: list[ScheduledTask] = field(default_factory=list)
    # tuple[Task, str] — task + reason it could not be scheduled
    unscheduled: list[tuple[Task, str]] = field(default_factory=list)
    total_minutes_scheduled: int = 0

    def summary(self) -> str:
        """Return a human-readable summary of the full day plan."""
        pass

    def is_complete(self) -> bool:
        """Return True if all tasks were successfully scheduled (nothing left unscheduled)."""
        pass


class Scheduler:
    def generate(self, owner: Owner, pet: Pet, tasks: list[Task]) -> DailyPlan:
        """
        Produce a DailyPlan by scheduling tasks within the owner's available time window.

        Mandatory tasks (critical priority or with deadlines) are placed first,
        ordered by deadline. Remaining flexible tasks fill open slots by priority.
        Tasks that cannot fit are recorded in DailyPlan.unscheduled.
        """
        pass

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """
        Return tasks sorted for scheduling: mandatory first (by deadline),
        then flexible by priority descending, duration ascending.
        """
        pass

    def _fits_in_slot(self, task: Task, slot_start: str, day_end: str) -> bool:
        """Return True if the task fits within [slot_start, day_end] without overflow."""
        pass

    def _build_reason(self, task: Task, start_time: str) -> str:
        """Return a human-readable explanation for why a task was scheduled at start_time."""
        pass

    def _next_free_slot(self, plan: DailyPlan, task: Task) -> Optional[str]:
        """
        Find the next available start time in the plan that can fit task.duration_minutes,
        respecting task.earliest_start and the owner's day_end boundary.
        Returns "HH:MM" string or None if no slot is available.
        """
        pass
