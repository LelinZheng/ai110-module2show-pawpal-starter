from __future__ import annotations

import datetime
from dataclasses import dataclass, field, replace
from typing import Optional


# ---------------------------------------------------------------------------
# Module-level time helpers
# ---------------------------------------------------------------------------

def _parse_time(t: str) -> int:
    """Convert 'HH:MM' to total minutes since midnight."""
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _format_time(minutes: int) -> str:
    """Convert total minutes since midnight to 'HH:MM'."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def expand_recurring_tasks(tasks: list[Task], day_start: str, day_end: str) -> list[Task]:
    """Expand any Task with recur_every_hours set into multiple timed copies.

    Each copy gets earliest_start spaced by the recurrence interval.
    Non-recurring tasks are returned unchanged.

    @param tasks: the original task list, possibly containing recurring tasks
    @param day_start: owner's day start time as 'HH:MM'
    @param day_end: owner's day end time as 'HH:MM'
    @return: expanded list where recurring tasks have been replaced by timed copies
    """
    expanded: list[Task] = []
    day_start_min = _parse_time(day_start)
    day_end_min = _parse_time(day_end)

    for task in tasks:
        if task.recur_every_hours is None:
            expanded.append(task)
            continue

        interval = task.recur_every_hours * 60
        cursor = day_start_min
        occurrence = 1
        while cursor + task.duration_minutes <= day_end_min:
            copy = replace(
                task,
                title=f"{task.title} ({occurrence})",
                earliest_start=_format_time(cursor),
                recur_every_hours=None,  # copies are not themselves recurring
            )
            expanded.append(copy)
            cursor += interval
            occurrence += 1

    return expanded


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """A pet owner with a named daily availability window."""

    name: str
    day_start: str  # "HH:MM"
    day_end: str    # "HH:MM"
    # available_minutes removed — derived from day_start/day_end to avoid silent conflicts

    def total_available_minutes(self) -> int:
        """Return the number of minutes between day_start and day_end."""
        return _parse_time(self.day_end) - _parse_time(self.day_start)


@dataclass
class Pet:
    """A pet with species, age, optional special needs, and an associated task list."""

    name: str
    species: str            # "dog" | "cat" | "other"
    age_years: float
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a care task to this pet's task list."""
        self.tasks.append(task)

    def task_count(self) -> int:
        """Return the number of tasks currently assigned to this pet."""
        return len(self.tasks)

    def is_senior(self) -> bool:
        """Return True if the pet meets the senior age threshold for its species."""
        thresholds = {"dog": 7, "cat": 10}
        threshold = thresholds.get(self.species, 8)
        return self.age_years >= threshold

    def summary(self) -> str:
        """Return a one-line description including name, species, age, and any special needs."""
        base = f"{self.name} ({self.species}, {self.age_years:.1f} yrs)"
        if self.is_senior():
            base += " \u2014 senior"
        if self.special_needs:
            needs = ", ".join(self.special_needs)
            base += f" [needs: {needs}]"
        return base

    def complete_task(self, task: Task) -> Optional[Task]:
        """Mark a task complete; if it recurs, append the next occurrence to this pet's task list and return it.

        @param task: the Task to mark as completed
        @return: the next Task occurrence if the task recurs, else None
        """
        next_occurrence = task.mark_complete()
        if next_occurrence is not None:
            self.tasks.append(next_occurrence)
        return next_occurrence

    def filter_tasks(
        self,
        category: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[Task]:
        """Return tasks matching the given filters; None means no filter on that field.

        @param category: if provided, only return tasks whose category equals this value
        @param completed: if provided, only return tasks whose completed flag matches
        @return: filtered list of Task objects
        """
        result = self.tasks
        if category is not None:
            result = [t for t in result if t.category == category]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result


@dataclass
class Task:
    """A single pet care activity with timing constraints and a completion flag."""

    title: str
    category: str           # walk | feed | medication | enrichment | grooming | vet
    duration_minutes: int
    priority: str           # low | medium | high | critical
    earliest_start: Optional[str] = None   # "HH:MM" or None
    deadline: Optional[str] = None         # "HH:MM" or None
    notes: str = ""
    recur_every_hours: Optional[int] = None  # if set, task repeats this many hours apart
    frequency: Optional[str] = None   # "daily" | "weekly" | None
    due_date: Optional[str] = None    # "YYYY-MM-DD" — the date this task instance is due
    completed: bool = False

    def mark_complete(self) -> Optional[Task]:
        """Mark this task as completed and return the next occurrence if it recurs, else None.

        Uses datetime.timedelta to advance due_date by 1 day (daily) or 7 days (weekly).

        @return: a new Task copy with completed=False and an advanced due_date, or None if non-recurring
        """
        self.completed = True
        if self.frequency is None:
            return None

        delta = datetime.timedelta(days=1 if self.frequency == "daily" else 7)
        base = datetime.date.fromisoformat(self.due_date) if self.due_date else datetime.date.today()
        next_due = (base + delta).isoformat()

        return replace(self, completed=False, due_date=next_due)

    def has_deadline(self) -> bool:
        """Return True when a hard deadline time has been set on this task."""
        return self.deadline is not None

    def is_mandatory(self) -> bool:
        """Return True if the task must be scheduled (critical priority or has a deadline)."""
        return self.priority == "critical" or self.has_deadline()


@dataclass
class ScheduledTask:
    """A Task placed at a concrete time slot with an explanatory reason."""

    task: Task
    start_time: str     # "HH:MM"
    end_time: str       # "HH:MM"
    reason: str

    def duration_minutes(self) -> int:
        """Return the number of minutes between start_time and end_time."""
        return _parse_time(self.end_time) - _parse_time(self.start_time)


@dataclass
class DailyPlan:
    """The full scheduling result for one day: scheduled tasks plus any that couldn't fit."""

    owner: Owner
    pet: Pet
    date: str
    scheduled: list[ScheduledTask] = field(default_factory=list)
    # tuple[Task, str] — task + reason it could not be scheduled
    unscheduled: list[tuple[Task, str]] = field(default_factory=list)
    total_minutes_scheduled: int = 0

    def is_complete(self) -> bool:
        """Return True when every input task was successfully scheduled."""
        return len(self.unscheduled) == 0

    def tasks_sorted_by_time(self) -> list[ScheduledTask]:
        """Return scheduled tasks ordered chronologically by start_time."""
        return sorted(self.scheduled, key=lambda s: _parse_time(s.start_time))

    def summary(self) -> str:
        """Return a formatted multi-line string showing the full day plan and any unscheduled tasks."""
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
            for st in self.tasks_sorted_by_time():
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
    """Greedy single-day scheduler: mandatory tasks first, then flexible tasks by priority."""

    def generate(self, owner: Owner, pet: Pet, tasks: list[Task]) -> DailyPlan:
        """Validate inputs, sort tasks, greedily fill the owner's time window, and return a DailyPlan."""
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

        tasks = expand_recurring_tasks(tasks, owner.day_start, owner.day_end)
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
        """Split into mandatory and flexible groups, sort each, and return mandatory-first."""
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
        """Return True if the task fits in [slot_start, day_end] without overflowing and respects earliest_start."""
        slot_start_min = _parse_time(slot_start)
        day_end_min = _parse_time(day_end)

        if task.earliest_start is not None:
            if slot_start_min < _parse_time(task.earliest_start):
                return False

        return slot_start_min + task.duration_minutes <= day_end_min

    def _build_reason(self, task: Task, start_time: str) -> str:
        """Return a short human-readable explanation for why the task was placed at start_time."""
        if task.priority == "critical":
            return "Critical task \u2014 must be completed today"
        if task.has_deadline():
            return f"Deadline at {task.deadline} \u2014 scheduled with enough lead time"
        if task.priority == "high":
            return f"High-priority task scheduled at {start_time}"
        return f"Scheduled at {start_time} after higher-priority tasks"

    def _next_free_slot(self, plan: DailyPlan, task: Task) -> Optional[str]:
        """Walk existing scheduled blocks to find the first gap that fits the task; return 'HH:MM' or None."""
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

    def check_input_conflicts(self, tasks: list[Task]) -> list[str]:
        """Scan a task list for overlapping time windows before scheduling; return warning strings.

        Checks every pair of tasks whose earliest_start values are both set. Two tasks
        conflict when one's window starts before the other's ends:
            a.start < b.start + b.duration  AND  b.start < a.start + a.duration
        Returns plain-English warnings — never raises, never crashes.
        """
        warnings: list[str] = []
        anchored = [t for t in tasks if t.earliest_start is not None]

        for i in range(len(anchored)):
            for j in range(i + 1, len(anchored)):
                a, b = anchored[i], anchored[j]
                a_start = _parse_time(a.earliest_start)  # type: ignore[arg-type]
                b_start = _parse_time(b.earliest_start)  # type: ignore[arg-type]
                a_end = a_start + a.duration_minutes
                b_end = b_start + b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    warnings.append(
                        f"WARNING: '{a.title}' ({a.earliest_start}–{_format_time(a_end)}) "
                        f"overlaps '{b.title}' ({b.earliest_start}–{_format_time(b_end)})"
                    )
        return warnings

    def detect_conflicts(self, plans: list[DailyPlan]) -> list[tuple[ScheduledTask, ScheduledTask]]:
        """Return pairs of ScheduledTasks from different pets that overlap in time.

        Two tasks conflict when one starts before the other ends:
            a.start < b.end  AND  b.start < a.end
        Only cross-pet conflicts are reported (same-pet overlaps can't happen
        because generate() already prevents them).

        @param plans: list of DailyPlan objects, one per pet
        @return: list of conflicting (ScheduledTask, ScheduledTask) pairs
        """
        conflicts: list[tuple[ScheduledTask, ScheduledTask]] = []
        # Flatten all scheduled tasks, tagged with their pet name
        all_tasks: list[tuple[str, ScheduledTask]] = []
        for plan in plans:
            for st in plan.scheduled:
                all_tasks.append((plan.pet.name, st))

        for i in range(len(all_tasks)):
            pet_a, st_a = all_tasks[i]
            for j in range(i + 1, len(all_tasks)):
                pet_b, st_b = all_tasks[j]
                if pet_a == pet_b:
                    continue  # same pet, skip
                a_start = _parse_time(st_a.start_time)
                a_end   = _parse_time(st_a.end_time)
                b_start = _parse_time(st_b.start_time)
                b_end   = _parse_time(st_b.end_time)
                if a_start < b_end and b_start < a_end:
                    conflicts.append((st_a, st_b))

        return conflicts
