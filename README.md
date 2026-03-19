# PawPal+

> A smart daily pet care scheduler for busy owners — built with Python OOP and Streamlit.

---

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot.png" target="_blank">
  <img src='/course_images/ai110/pawpal_screenshot.png' title='PawPal App' width='' alt='PawPal App' class='center-block' />
</a>

---

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

---

## Features

### Owner & Pet Management
- Register an owner with a named daily time window (e.g. 07:00 – 21:00)
- Add multiple pets with species, age, and special needs
- All scheduling respects the owner's available hours as a hard boundary

### Task Management
- Add tasks with title, category, duration, priority, optional earliest-start time, and deadline
- Edit or delete any task inline with per-row ✏️ / 🗑️ buttons
- Mark tasks complete with a checkbox; completed tasks appear with ~~strikethrough~~
- Filter the task list by category (walk, feed, medication, etc.) and completion status
- Sort the task list by earliest-start time with one click
- Set a task as **daily** or **weekly** recurring with a due date; the date picker shows only tasks relevant to the selected day

### Priority-Aware Scheduling
- Mandatory tasks (critical priority or deadline-bound) are always placed first, sorted by earliest deadline
- Flexible tasks fill remaining slots sorted by priority then duration
- Tasks that cannot fit are recorded in an **Unscheduled** panel with a plain-English reason — nothing is silently dropped

### Sorting by Time
- `DailyPlan.tasks_sorted_by_time()` uses Python's `sorted()` with a `lambda` key on `HH:MM` strings, returning the final schedule in strict chronological order regardless of the order tasks were added
- The UI labels this behaviour explicitly so the owner knows the plan is always sorted

### Filtering by Category and Status
- `Pet.filter_tasks(category, completed)` returns any combination of category and completion filters
- The UI shows an active-filter caption ("Active filters: category = medication · status = incomplete") so the owner always knows what they are seeing

### Recurring Task Expansion
- Set `recur_every_hours` on any task and `expand_recurring_tasks()` automatically creates correctly spaced copies across the day window before scheduling — one `Feeding` task with `recur_every_hours=6` becomes three scheduled feedings
- Set `frequency="daily"` / `"weekly"` and `due_date` for date-scoped tasks that appear on the right day via the date picker

### Conflict Warnings
- **Cross-pet conflicts** (`Scheduler.detect_conflicts`): after generating plans for multiple pets, the UI shows a bordered warning card for every time slot where the owner would be double-booked, including the exact overlap duration and a one-line fix instruction
- **Conflict-aware scheduling** (`Scheduler.generate(existing_plans=…)`): when generating a second pet's plan, already-booked slots from the first pet are passed in so the scheduler places new tasks in genuinely free gaps — eliminating conflicts automatically
- A green `st.success` banner confirms when all pets' plans are conflict-free

### Date Picker
- Select any date at the top of the app; the task list, filters, and schedule all update to show only tasks relevant to that day
- Switching dates clears stale cached plans so the schedule always matches the chosen date

---

## System Design

The app follows a clean two-layer architecture:

| Layer | Files | Responsibility |
|---|---|---|
| **Logic** | `pawpal_system.py` | All scheduling, sorting, filtering, conflict detection |
| **UI** | `app.py` | Thin Streamlit layer — calls backend methods, renders results |
| **Tests** | `tests/test_pawpal.py` | 11 pytest tests covering all core behaviours |
| **CLI demo** | `main.py` | Terminal walkthrough of every feature |

See `uml_final.png` for the full class diagram.

---

## Getting Started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the CLI demo

```bash
python main.py
```

### Run the tests

```bash
python -m pytest
```

---

## Testing PawPal+

The suite in `tests/test_pawpal.py` covers 11 behaviours across five groups:

| Group | Tests | What is verified |
|---|---|---|
| **Task completion** | 2 | `mark_complete()` sets `completed=True`; calling it twice is safe |
| **Task addition** | 2 | `add_task()` increments count; the exact object is stored |
| **Sorting correctness** | 2 | `tasks_sorted_by_time()` returns chronological order regardless of input order; critical tasks always appear before flexible ones |
| **Recurrence** | 2 | Completing a daily task marks it done without spawning a duplicate; `task_count` stays at 1 |
| **Conflict detection** | 3 | Overlapping cross-pet slots are flagged; non-overlapping slots are not; `existing_plans` eliminates double-booking |

### Confidence level

⭐⭐⭐⭐ (4 / 5)

Core scheduling logic — priority ordering, deadline enforcement, earliest-start constraints, and cross-pet conflict avoidance — is fully covered and all 11 tests pass. The main gap is edge-case coverage: day windows shorter than a single task, tasks whose `earliest_start` is after `day_end`, and very large task lists are handled defensively in code (landing in `unscheduled`) but are not yet verified by automated tests.

---

## Suggested Workflow (for contributors)

1. Read the scenario and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python dataclass stubs.
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviours.
6. Connect logic to the Streamlit UI in `app.py`.
7. Refine UML to match what was actually built (`uml_final.png`).
