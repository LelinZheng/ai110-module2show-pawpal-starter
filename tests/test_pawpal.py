"""
tests/test_pawpal.py — Unit tests for PawPal+ core logic.
Run with: pytest
"""
from pawpal_system import Pet, Task


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
