"""
main.py — CLI demo script for PawPal+
Run with: python main.py

Phase 3 focus: sorting and filtering
  - Tasks are added OUT OF ORDER on purpose to prove sorted() + lambda works
  - filter_tasks() is exercised with category, completed, and combined filters
  - tasks_sorted_by_time() shows the corrected chronological order post-schedule
"""
from pawpal_system import Owner, Pet, Task, Scheduler


SEP = "=" * 52


def header(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def main() -> None:
    owner = Owner(name="Jordan", day_start="07:00", day_end="21:00")
    mochi = Pet(name="Mochi", species="cat", age_years=3.0)
    buddy = Pet(name="Buddy", species="dog", age_years=8.5,
                special_needs=["joint supplement"])
    scheduler = Scheduler()

    # -----------------------------------------------------------------------
    # Tasks added INTENTIONALLY OUT OF ORDER
    # The scheduler's sort key is:  lambda t: _parse_time(t.earliest_start or "00:00")
    # We prove below that the output is always chronological regardless.
    # -----------------------------------------------------------------------

    # Mochi — added: enrichment (10:00), then medication (07:00), then recurring feed (08:30)
    mochi.add_task(Task(
        title="Enrichment Play",
        category="enrichment",
        duration_minutes=20,
        priority="medium",
        earliest_start="10:00",   # added first — latest window
    ))
    mochi.add_task(Task(
        title="Insulin Shot",
        category="medication",
        duration_minutes=5,
        priority="critical",
        deadline="08:30",
        notes="0.5 units, before breakfast",
                          # added second — but must go first
    ))
    mochi.add_task(Task(
        title="Feeding",
        category="feed",
        duration_minutes=10,
        priority="high",
        earliest_start="08:30",
        recur_every_hours=6,       # added third — expands into 3 copies
    ))

    # Buddy — added: grooming (no window), afternoon walk (15:00), morning walk (07:00), medication (deadline 09:00)
    buddy.add_task(Task(
        title="Grooming Brush",
        category="grooming",
        duration_minutes=15,
        priority="low",            # added first — no time constraint
    ))
    buddy.add_task(Task(
        title="Afternoon Walk",
        category="walk",
        duration_minutes=45,
        priority="medium",
        earliest_start="15:00",   # added second — latest slot
    ))
    buddy.add_task(Task(
        title="Morning Walk",
        category="walk",
        duration_minutes=30,
        priority="high",
        earliest_start="07:00",   # added third — earliest slot
    ))
    buddy.add_task(Task(
        title="Joint Supplement",
        category="medication",
        duration_minutes=5,
        priority="critical",
        deadline="09:00",
        notes="Mix into food",     # added last — deadline-driven
    ))

    # -----------------------------------------------------------------------
    # Show input order (scrambled) before scheduling
    # -----------------------------------------------------------------------
    header("Input Order (as added — intentionally scrambled)")
    for pet in (mochi, buddy):
        print(f"\n  {pet.name}:")
        for i, t in enumerate(pet.tasks, 1):
            constraint = f"earliest={t.earliest_start}" if t.earliest_start else \
                         f"deadline={t.deadline}" if t.deadline else "no time constraint"
            print(f"    {i}. [{t.priority:8}] {t.title:<22}  {constraint}")

    # -----------------------------------------------------------------------
    # Generate schedules — Scheduler._sort_tasks() uses:
    #   key=lambda t: (_parse_time(t.deadline or 'inf'), _PRIORITY_ORDER[t.priority])
    # for mandatory tasks, and priority/duration for flexible ones.
    # -----------------------------------------------------------------------
    mochi_plan = scheduler.generate(owner, mochi, mochi.tasks)
    buddy_plan  = scheduler.generate(owner, buddy, buddy.tasks)

    header("Generated Schedules")
    print(mochi_plan.summary())
    print()
    print(buddy_plan.summary())

    # -----------------------------------------------------------------------
    # tasks_sorted_by_time() — proves the schedule output is chronological
    # regardless of what order tasks were added in
    # -----------------------------------------------------------------------
    header("Sorted Output (tasks_sorted_by_time)")
    print("  tasks_sorted_by_time() uses:  sorted(scheduled, key=lambda s: _parse_time(s.start_time))\n")
    for plan in (mochi_plan, buddy_plan):
        print(f"  {plan.pet.name}:")
        for st in plan.tasks_sorted_by_time():
            print(f"    {st.start_time} – {st.end_time}  [{st.task.priority:8}]  {st.task.title}")
        print()

    # -----------------------------------------------------------------------
    # filter_tasks() — category filter, status filter, combined filter
    # -----------------------------------------------------------------------
    header("Filtering with filter_tasks()")

    # Mark one of Mochi's tasks complete so the status filter has something to show
    mochi.tasks[1].mark_complete()   # Insulin Shot → completed

    filters = [
        ("Buddy",  dict(category="walk"),                 "category='walk'"),
        ("Mochi",  dict(completed=False),                 "completed=False"),
        ("Mochi",  dict(completed=True),                  "completed=True"),
        ("Buddy",  dict(category="medication"),           "category='medication'"),
        ("Mochi",  dict(category="feed", completed=False),"category='feed', completed=False"),
    ]

    pet_map = {"Mochi": mochi, "Buddy": buddy}

    for pet_name, kwargs, label in filters:
        pet = pet_map[pet_name]
        results = pet.filter_tasks(**kwargs)
        titles = ", ".join(t.title for t in results) or "(none)"
        print(f"  {pet_name}.filter_tasks({label})")
        print(f"    → {len(results)} task(s): {titles}")

    # -----------------------------------------------------------------------
    # detect_conflicts() — cross-pet double-bookings for the same owner
    # -----------------------------------------------------------------------
    header("Cross-Pet Conflict Detection")
    conflicts = scheduler.detect_conflicts([mochi_plan, buddy_plan])
    if not conflicts:
        print("  No conflicts detected.")
    else:
        print(f"  {len(conflicts)} conflict(s) found — Jordan is double-booked:\n")
        for st_a, st_b in conflicts:
            print(f"  ⚠  {st_a.start_time}–{st_a.end_time}  {st_a.task.title}")
            print("     overlaps with")
            print(f"     {st_b.start_time}–{st_b.end_time}  {st_b.task.title}\n")
    print()


if __name__ == "__main__":
    main()
