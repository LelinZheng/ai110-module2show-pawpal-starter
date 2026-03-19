# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

PawPal+ goes beyond a basic task list with several algorithmic features built into `pawpal_system.py`:

### Priority-aware scheduling
The `Scheduler` sorts tasks using a composite key — mandatory tasks (critical priority or deadline-bound) are always placed first, ordered by earliest deadline. Flexible tasks fill remaining slots ordered by priority then duration. No task is silently dropped; anything that doesn't fit is recorded in `DailyPlan.unscheduled` with a plain-English reason.

### Filtering
`Pet.filter_tasks(category=None, completed=None)` returns a subset of a pet's tasks matching any combination of category and completion status. Used by the UI to surface incomplete medication tasks or show all walks at a glance.

### Recurring tasks
Set `recur_every_hours` on any `Task` and the scheduler automatically expands it into correctly spaced copies across the owner's day window — one `Task(title="Feeding", recur_every_hours=6)` becomes three scheduled feedings without manual duplication. Tasks can also be given a `frequency` ("daily" or "weekly") and a `due_date`; the UI's date picker filters tasks by date so tomorrow's recurring task only appears when you navigate to tomorrow.

### Conflict detection
Two layers of conflict checking, both returning warnings instead of crashing:
- **Input conflicts** (`Scheduler.check_input_conflicts`): scans a pet's task list before scheduling and flags any two tasks whose `earliest_start` windows overlap, so the owner can fix the input rather than be surprised by the output.
- **Cross-pet conflicts** (`Scheduler.detect_conflicts`): after generating plans for multiple pets, identifies any time slots where the owner would be double-booked across different pets.

### Running the app

```bash
streamlit run app.py
```

### Running the CLI demo

```bash
python main.py
```

### Running tests

```bash
python -m pytest
```

## Testing PawPal+

### Running the test suite

```bash
python -m pytest
```

### What the tests cover

The suite in `tests/test_pawpal.py` covers 11 behaviors across five groups:

| Group | Tests | What is verified |
|---|---|---|
| **Task completion** | 2 | `mark_complete()` sets `completed=True`; calling it twice is safe |
| **Task addition** | 2 | `add_task()` increments count; the exact object is stored |
| **Sorting correctness** | 2 | `tasks_sorted_by_time()` returns chronological order regardless of input order; critical tasks are always scheduled before flexible ones |
| **Recurrence** | 2 | Completing a daily task marks it done without spawning a duplicate; `task_count` stays at 1 after completion |
| **Conflict detection** | 3 | Overlapping cross-pet slots are flagged; non-overlapping slots are not; passing `existing_plans` to `generate()` eliminates double-booking |

### Confidence level

⭐⭐⭐⭐ (4 / 5)

The core scheduling logic — priority ordering, deadline enforcement, earliest-start constraints, and cross-pet conflict avoidance — is well covered and all 11 tests pass. The main gap is edge-case coverage: very long task lists that overflow the day window, recurring tasks that span midnight, and owner windows shorter than a single task's duration are not yet tested. Those scenarios are handled defensively in the code (tasks that don't fit land in `unscheduled` with a reason) but are not verified by automated tests.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
