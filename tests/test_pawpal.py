"""
tests/test_pawpal.py — Unit tests for PawPal+ core logic.
Run with: pytest
"""
import datetime

from pawpal_system import Owner, Pet, Task, Scheduler, _parse_time


def make_task(**kwargs) -> Task:
    """Helper: create a Task with sensible defaults, overridable via kwargs."""
    defaults = dict(
        title="Test Task",
        category="walk",
        duration_minutes=20,
        priority="medium",
    )
    defaults.update(kwargs)
    return Task(**defaults)


def make_owner(**kwargs) -> Owner:
    defaults = dict(name="Jordan", day_start="07:00", day_end="21:00")
    defaults.update(kwargs)
    return Owner(**defaults)


# ---------------------------------------------------------------------------
# Test 1: mark_complete() changes task status
# ---------------------------------------------------------------------------

def test_mark_complete_sets_completed_true() -> None:
    """A newly created task is not completed; mark_complete() should change that."""
    task = make_task(title="Morning Walk")

    assert task.completed is False, "Task should start as not completed"

    task.mark_complete()

    assert task.completed is True, "Task should be completed after mark_complete()"


def test_mark_complete_is_idempotent() -> None:
    """Calling mark_complete() twice should not raise and status stays True."""
    task = make_task(title="Feeding")
    task.mark_complete()
    task.mark_complete()

    assert task.completed is True


# ---------------------------------------------------------------------------
# Test 2: add_task() increases the pet's task count
# ---------------------------------------------------------------------------

def test_add_task_increases_task_count() -> None:
    """Adding tasks to a Pet should increase task_count() by one each time."""
    pet = Pet(name="Mochi", species="cat", age_years=3.0)

    assert pet.task_count() == 0, "Pet should start with zero tasks"

    pet.add_task(make_task(title="Insulin Shot", priority="critical"))
    assert pet.task_count() == 1

    pet.add_task(make_task(title="Breakfast Feeding", category="feed"))
    assert pet.task_count() == 2


def test_add_task_stores_correct_task() -> None:
    """The task added to a Pet should be retrievable and match the original."""
    pet = Pet(name="Buddy", species="dog", age_years=5.0)
    task = make_task(title="Afternoon Walk", priority="high")

    pet.add_task(task)

    assert pet.tasks[0] is task, "The stored task should be the exact object added"
    assert pet.tasks[0].title == "Afternoon Walk"


# ---------------------------------------------------------------------------
# Test 3: Sorting correctness — scheduled tasks in chronological order
# ---------------------------------------------------------------------------

def test_tasks_sorted_by_time_returns_chronological_order() -> None:
    """tasks_sorted_by_time() returns tasks ordered by start time."""
    owner = make_owner()
    pet = Pet(name="Rex", species="dog", age_years=4.0)

    # Add tasks OUT OF ORDER on purpose
    pet.add_task(make_task(
        title="Evening Walk", priority="medium", earliest_start="18:00"
    ))
    pet.add_task(make_task(
        title="Morning Walk", priority="high", earliest_start="07:00"
    ))
    pet.add_task(make_task(
        title="Afternoon Feed", priority="high", earliest_start="12:00"
    ))

    plan = Scheduler().generate(owner, pet, pet.tasks)
    sorted_tasks = plan.tasks_sorted_by_time()

    start_minutes = [_parse_time(st.start_time) for st in sorted_tasks]
    assert start_minutes == sorted(start_minutes), (
        "tasks_sorted_by_time() should return tasks in ascending start-time order"
    )


def test_mandatory_tasks_scheduled_before_flexible() -> None:
    """Critical tasks must be placed before lower-priority flexible tasks."""
    owner = make_owner()
    pet = Pet(name="Mochi", species="cat", age_years=3.0)

    pet.add_task(make_task(title="Low Priority Walk", priority="low"))
    pet.add_task(make_task(
        title="Critical Med",
        category="medication",
        priority="critical",
        duration_minutes=10,
    ))

    plan = Scheduler().generate(owner, pet, pet.tasks)
    sorted_tasks = plan.tasks_sorted_by_time()

    titles = [st.task.title for st in sorted_tasks]
    assert titles.index("Critical Med") < titles.index("Low Priority Walk"), (
        "Critical tasks must appear earlier than low-priority flexible tasks"
    )


# ---------------------------------------------------------------------------
# Test 4: Recurrence — completing a task marks it done, no new task spawned
# ---------------------------------------------------------------------------

def test_mark_complete_sets_completed_on_recurring_task() -> None:
    """Completing a daily task marks it done; no new task is spawned.

    Recurrence is handled by due_date filtering in the UI — tasks for future
    dates appear when the user navigates to that date.
    """
    today = datetime.date.today().isoformat()
    task = make_task(
        title="Daily Feed",
        category="feed",
        frequency="daily",
        due_date=today,
    )

    task.mark_complete()

    assert task.completed is True


def test_complete_task_does_not_spawn_new_task() -> None:
    """Pet.complete_task() must NOT append extra tasks to the pet's list."""
    today = datetime.date.today().isoformat()
    pet = Pet(name="Mochi", species="cat", age_years=3.0)
    task = make_task(
        title="Daily Feed",
        category="feed",
        frequency="daily",
        due_date=today,
    )
    pet.add_task(task)

    pet.complete_task(task)

    assert pet.task_count() == 1, (
        "Task count must stay at 1 — no auto-spawning on completion"
    )


# ---------------------------------------------------------------------------
# Test 5: Conflict detection — overlapping cross-pet tasks are flagged
# ---------------------------------------------------------------------------

def test_detect_conflicts_flags_overlapping_tasks() -> None:
    """Two pets scheduled at the same time must be reported as a conflict."""
    owner = make_owner()
    scheduler = Scheduler()

    pet1 = Pet(name="Mochi", species="cat", age_years=3.0)
    pet1.add_task(make_task(
        title="Morning Walk", earliest_start="07:00", duration_minutes=30
    ))

    pet2 = Pet(name="Buddy", species="dog", age_years=5.0)
    pet2.add_task(make_task(
        title="Breakfast Feed", earliest_start="07:00", duration_minutes=20
    ))

    plan1 = scheduler.generate(owner, pet1, pet1.tasks)
    # scheduled independently → overlap expected
    plan2 = scheduler.generate(owner, pet2, pet2.tasks)

    conflicts = scheduler.detect_conflicts([plan1, plan2])
    assert len(conflicts) > 0, (
        "Overlapping tasks across pets must be reported as conflicts"
    )


def test_detect_conflicts_none_when_sequential() -> None:
    """Tasks for two pets that do not overlap must not be flagged."""
    owner = make_owner()
    scheduler = Scheduler()

    pet1 = Pet(name="Mochi", species="cat", age_years=3.0)
    pet1.add_task(make_task(
        title="Morning Walk", earliest_start="07:00", duration_minutes=30
    ))

    pet2 = Pet(name="Buddy", species="dog", age_years=5.0)
    pet2.add_task(make_task(
        title="Afternoon Walk", earliest_start="14:00", duration_minutes=30
    ))

    plan1 = scheduler.generate(owner, pet1, pet1.tasks)
    plan2 = scheduler.generate(owner, pet2, pet2.tasks)

    conflicts = scheduler.detect_conflicts([plan1, plan2])
    assert conflicts == [], (
        "Non-overlapping tasks must not produce any conflict warnings"
    )


def test_existing_plans_prevent_cross_pet_overlap() -> None:
    """generate() with existing_plans places tasks in free slots."""
    owner = make_owner()
    scheduler = Scheduler()

    pet1 = Pet(name="Mochi", species="cat", age_years=3.0)
    pet1.add_task(make_task(
        title="Morning Walk", earliest_start="07:00", duration_minutes=30
    ))
    plan1 = scheduler.generate(owner, pet1, pet1.tasks)

    pet2 = Pet(name="Buddy", species="dog", age_years=5.0)
    pet2.add_task(make_task(title="Breakfast Feed", duration_minutes=20))
    plan2 = scheduler.generate(
        owner, pet2, pet2.tasks, existing_plans=[plan1]
    )

    conflicts = scheduler.detect_conflicts([plan1, plan2])
    assert conflicts == [], (
        "When existing_plans is passed, the scheduler must avoid "
        "cross-pet time conflicts"
    )
