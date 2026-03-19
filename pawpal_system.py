from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Module-level time helpers
# ---------------------------------------------------------------------------

def _parse_time(t: str) -> int:
    """Convert 'HH:MM' to total minutes since midnight.

    :param t: Time string in "HH:MM" format.
    :return: Total minutes since midnight.
    """
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _format_time(minutes: int) -> str:
    """Convert total minutes since midnight to 'HH:MM'.

    :param minutes: Total minutes since midnight.
    :return: Time string in "HH:MM" format.
    """
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Represents a pet owner with a defined availability window for the day."""

    name: str
    day_start: str  # "HH:MM"
    day_end: str    # "HH:MM"
    # available_minutes removed — derived from day_start/day_end to avoid silent conflicts

    def total_available_minutes(self) -> int:
        """Return total minutes between day_start and day_end.

        :return: Integer number of minutes available in the owner's day window.
        """
        return _parse_time(self.day_end) - _parse_time(self.day_start)


@dataclass
class Pet:
    """Represents a pet with species, age, and optional special needs."""

    name: str
    species: str            # "dog" | "cat" | "other"
    age_years: float
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet's task list."""
        self.tasks.append(task)

    def task_count(self) -> int:
        """Return the number of tasks assigned to this pet."""
        return len(self.tasks)

    def is_senior(self) -> bool:
        """Return True if the pet is considered senior for its species.

        Senior thresholds: dog >= 7 years, cat >= 10 years, other >= 8 years.

        :return: True if the pet qualifies as senior.
        """
        thresholds = {"dog": 7, "cat": 10}
        threshold = thresholds.get(self.species, 8)
        return self.age_years >= threshold

    def summary(self) -> str:
        """Return a short human-readable description of the pet.

        Format: "<name> (<species>, <age> yrs)" with " — senior" appended when
        applicable, and " [needs: <item>, ...]" appended when special_needs is
        non-empty.

        :return: One-line summary string.
        """
        base = f"{self.name} ({self.species}, {self.age_years:.1f} yrs)"
        if self.is_senior():
            base += " \u2014 senior"
        if self.special_needs:
            needs = ", ".join(self.special_needs)
            base += f" [needs: {needs}]"
        return base


@dataclass
class Task:
    """Represents a single care task to be scheduled in the owner's day."""

    title: str
    category: str           # walk | feed | medication | enrichment | grooming | vet
    duration_minutes: int
    priority: str           # low | medium | high | critical
    earliest_start: Optional[str] = None   # "HH:MM" or None
    deadline: Optional[str] = None         # "HH:MM" or None
    notes: str = ""
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def has_deadline(self) -> bool:
        """Return True if this task has a hard deadline.

        :return: True when deadline is not None.
        """
        return self.deadline is not None

    def is_mandatory(self) -> bool:
        """Return True if this task must be scheduled (critical priority or has a deadline).

        :return: True when priority is "critical" or a deadline is set.
        """
        return self.priority == "critical" or self.has_deadline()


@dataclass
class ScheduledTask:
    """A Task that has been assigned a concrete start and end time."""

    task: Task
    start_time: str     # "HH:MM"
    end_time: str       # "HH:MM"
    reason: str

    def duration_minutes(self) -> int:
        """Return the duration of this scheduled task in minutes.

        :return: Integer number of minutes between start_time and end_time.
        """
        return _parse_time(self.end_time) - _parse_time(self.start_time)


@dataclass
class DailyPlan:
    """The complete scheduling result for a single day."""

    owner: Owner
    pet: Pet
    date: str
    scheduled: list[ScheduledTask] = field(default_factory=list)
    # tuple[Task, str] — task + reason it could not be scheduled
    unscheduled: list[tuple[Task, str]] = field(default_factory=list)
    total_minutes_scheduled: int = 0

    def is_complete(self) -> bool:
        """Return True if all tasks were successfully scheduled (nothing left unscheduled).

        :return: True when unscheduled is empty.
        """
        return len(self.unscheduled) == 0

    def summary(self) -> str:
        """Return a human-readable summary of the full day plan.

        The summary includes owner/pet info, date, total scheduled time, a
        chronological list of scheduled tasks with reasons, and a section for
        unscheduled tasks when any exist.

        :return: Multi-line formatted string.
        """
        lines: list[str] = []
        lines.append("=== PawPal+ Daily Plan ===")
        lines.append(
            f"Owner: {self.owner.name}  |  Pet: {self.pet.summary()}"
        )
        lines.append(
            f"Date: {self.date}  |  Scheduled: {len(self.scheduled)} tasks"
            f" ({self.total_minutes_scheduled} min)"
        )

        if self.scheduled:
            lines.append("")
            for st in sorted(self.scheduled, key=lambda s: _parse_time(s.start_time)):
                label = f"{st.start_time} \u2013 {st.end_time}"
                title_col = f"{st.task.title:<20}"
                priority_tag = f"[{st.task.priority}]"
                lines.append(
                    f"{label}  {title_col} {priority_tag} \u2014 {st.reason}"
                )

        if self.unscheduled:
            lines.append("")
            lines.append(f"\u26a0 Unscheduled ({len(self.unscheduled)}):")
            for task, reason in self.unscheduled:
                lines.append(
                    f"  - {task.title} ({task.duration_minutes} min): {reason}"
                )

        lines.append("==========================")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

# Valid priority values and their sort order (lower number = higher urgency).
_PRIORITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

_VALID_PRIORITIES: frozenset[str] = frozenset(_PRIORITY_ORDER)


class Scheduler:
    """Greedy single-day task scheduler for PawPal+.

    <p>Tasks are sorted so mandatory items (critical priority or deadline-bound)
    fill slots first, followed by flexible tasks ordered by priority then
    duration. Tasks that cannot fit within the owner's window are recorded in
    DailyPlan.unscheduled with a human-readable reason.</p>
    """

    def generate(self, owner: Owner, pet: Pet, tasks: list[Task]) -> DailyPlan:
        """Produce a DailyPlan by scheduling tasks within the owner's available time window.

        Mandatory tasks (critical priority or with deadlines) are placed first,
        ordered by deadline. Remaining flexible tasks fill open slots by priority.
        Tasks that cannot fit are recorded in DailyPlan.unscheduled.

        :param owner: The owner whose day_start/day_end define the scheduling window.
        :param pet: The pet whose care tasks are being scheduled.
        :param tasks: List of Task objects to schedule.
        :return: A populated DailyPlan.
        :raises ValueError: If any task has duration_minutes <= 0, an unknown
            priority value, or a deadline that precedes its earliest_start.
        """
        # --- Validation ---
        for task in tasks:
            if task.duration_minutes <= 0:
                raise ValueError(
                    f"Task '{task.title}' has non-positive duration: {task.duration_minutes}"
                )
            if task.priority not in _VALID_PRIORITIES:
                raise ValueError(
                    f"Task '{task.title}' has unknown priority: '{task.priority}'"
                )
            if task.deadline is not None and task.earliest_start is not None:
                if _parse_time(task.deadline) < _parse_time(task.earliest_start):
                    raise ValueError(
                        f"Task '{task.title}' has deadline {task.deadline!r} "
                        f"before earliest_start {task.earliest_start!r}"
                    )

        sorted_tasks = self._sort_tasks(tasks)

        plan = DailyPlan(
            owner=owner,
            pet=pet,
            date=datetime.date.today().isoformat(),
        )

        for task in sorted_tasks:
            start_str = self._next_free_slot(plan, task)

            if start_str is None:
                plan.unscheduled.append((task, "Not enough time remaining in the day"))
                continue

            # Deadline feasibility check: start + duration must not exceed deadline.
            if task.deadline is not None:
                finish = _parse_time(start_str) + task.duration_minutes
                if finish > _parse_time(task.deadline):
                    plan.unscheduled.append(
                        (task, f"Cannot fit before deadline {task.deadline}")
                    )
                    continue

            end_str = _format_time(_parse_time(start_str) + task.duration_minutes)
            reason = self._build_reason(task, start_str)
            plan.scheduled.append(
                ScheduledTask(task=task, start_time=start_str, end_time=end_str, reason=reason)
            )

        plan.total_minutes_scheduled = sum(
            st.duration_minutes() for st in plan.scheduled
        )
        return plan

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted for scheduling: mandatory first (by deadline),
        then flexible by priority descending, duration ascending.

        Mandatory group sort key: (deadline minutes ascending, None deadlines go
        last, then priority order value ascending).
        Flexible group sort key: (priority order value ascending, duration_minutes
        ascending).

        :param tasks: Unsorted list of Task objects.
        :return: New sorted list.
        """
        mandatory = [t for t in tasks if t.is_mandatory()]
        flexible = [t for t in tasks if not t.is_mandatory()]

        # Sort mandatory: deadline asc (None last), then priority value asc.
        mandatory.sort(
            key=lambda t: (
                _parse_time(t.deadline) if t.deadline is not None else float("inf"),
                _PRIORITY_ORDER[t.priority],
            )
        )

        # Sort flexible: priority value asc (high urgency first), then duration asc.
        flexible.sort(
            key=lambda t: (_PRIORITY_ORDER[t.priority], t.duration_minutes)
        )

        return mandatory + flexible

    def _fits_in_slot(self, task: Task, slot_start: str, day_end: str) -> bool:
        """Return True if the task fits within [slot_start, day_end] without overflow.

        Also verifies that slot_start is not earlier than task.earliest_start when
        that constraint is set.

        :param task: The task to check.
        :param slot_start: Proposed start time as "HH:MM".
        :param day_end: Owner's day end boundary as "HH:MM".
        :return: True if the task fits without overflowing day_end and respects
            earliest_start.
        """
        slot_start_min = _parse_time(slot_start)
        day_end_min = _parse_time(day_end)

        if task.earliest_start is not None:
            if slot_start_min < _parse_time(task.earliest_start):
                return False

        return slot_start_min + task.duration_minutes <= day_end_min

    def _build_reason(self, task: Task, start_time: str) -> str:
        """Return a human-readable explanation for why a task was scheduled at start_time.

        :param task: The task that was scheduled.
        :param start_time: The assigned start time as "HH:MM".
        :return: Short descriptive string.
        """
        if task.priority == "critical":
            return "Critical task \u2014 must be completed today"
        if task.has_deadline():
            return f"Deadline at {task.deadline} \u2014 scheduled with enough lead time"
        if task.priority == "high":
            return f"High-priority task scheduled at {start_time}"
        return f"Scheduled at {start_time} after higher-priority tasks"

    def _next_free_slot(self, plan: DailyPlan, task: Task) -> Optional[str]:
        """Find the next available start time in the plan that can fit task.duration_minutes.

        Walks through already-scheduled tasks (sorted by start_time) to identify
        gaps, starting from the later of day_start and task.earliest_start.
        Returns the first slot where _fits_in_slot() is True.

        :param plan: The DailyPlan built so far (may already have scheduled tasks).
        :param task: The task that needs a slot.
        :return: "HH:MM" start time string, or None if no slot is available.
        """
        # Determine earliest candidate minute for this task.
        cursor_min = _parse_time(plan.owner.day_start)
        if task.earliest_start is not None:
            cursor_min = max(cursor_min, _parse_time(task.earliest_start))

        day_end_min = _parse_time(plan.owner.day_end)

        # Walk scheduled blocks sorted by start_time to find gaps.
        occupied = sorted(plan.scheduled, key=lambda s: _parse_time(s.start_time))

        for st in occupied:
            block_start = _parse_time(st.start_time)
            block_end = _parse_time(st.end_time)

            if cursor_min + task.duration_minutes <= block_start:
                # Gap before this block is large enough.
                candidate = _format_time(cursor_min)
                if self._fits_in_slot(task, candidate, plan.owner.day_end):
                    return candidate

            # Advance cursor past this block.
            if block_end > cursor_min:
                cursor_min = block_end

        # Check the tail of the day after all scheduled blocks.
        if cursor_min + task.duration_minutes <= day_end_min:
            candidate = _format_time(cursor_min)
            if self._fits_in_slot(task, candidate, plan.owner.day_end):
                return candidate

        return None
