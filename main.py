"""
main.py — CLI demo script for PawPal+
Run with: python main.py
"""
from pawpal_system import Owner, Pet, Task, Scheduler


def main() -> None:
    # --- Owner ---
    owner = Owner(name="Jordan", day_start="07:00", day_end="21:00")

    # --- Pets ---
    mochi = Pet(name="Mochi", species="cat", age_years=3.0)
    buddy = Pet(name="Buddy", species="dog", age_years=8.5, special_needs=["joint supplement"])

    scheduler = Scheduler()

    # -----------------------------------------------------------------------
    # Mochi's tasks
    # -----------------------------------------------------------------------
    mochi_tasks = [
        Task(
            title="Insulin Shot",
            category="medication",
            duration_minutes=5,
            priority="critical",
            deadline="08:30",
            notes="0.5 units, always before breakfast",
        ),
        # Recurring feeding every 6 hours — expand_recurring_tasks inside
        # Scheduler.generate() will produce timed copies across the day.
        Task(
            title="Feeding",
            category="feed",
            duration_minutes=10,
            priority="high",
            earliest_start="08:30",
            recur_every_hours=6,
        ),
        Task(
            title="Enrichment Play",
            category="enrichment",
            duration_minutes=20,
            priority="medium",
            earliest_start="10:00",
        ),
    ]

    # -----------------------------------------------------------------------
    # Buddy's tasks
    # -----------------------------------------------------------------------
    buddy_tasks = [
        Task(
            title="Morning Walk",
            category="walk",
            duration_minutes=30,
            priority="high",
            earliest_start="07:00",
        ),
        Task(
            title="Joint Supplement",
            category="medication",
            duration_minutes=5,
            priority="critical",
            deadline="09:00",
            notes="Mix into food",
        ),
        Task(
            title="Afternoon Walk",
            category="walk",
            duration_minutes=45,
            priority="medium",
            earliest_start="15:00",
        ),
        Task(
            title="Grooming Brush",
            category="grooming",
            duration_minutes=15,
            priority="low",
        ),
    ]

    # -----------------------------------------------------------------------
    # Populate each pet's task list so filter_tasks works on the source tasks
    # -----------------------------------------------------------------------
    for t in mochi_tasks:
        mochi.add_task(t)
    for t in buddy_tasks:
        buddy.add_task(t)

    # -----------------------------------------------------------------------
    # Generate plans
    # -----------------------------------------------------------------------
    separator = "\n" + "=" * 50 + "\n"

    print(separator.strip())
    print(f"  PawPal+ — Today's Schedule for {owner.name}")
    print(f"  Window: {owner.day_start} – {owner.day_end}"
          f"  ({owner.total_available_minutes()} min available)")
    print(separator.strip())

    mochi_plan = scheduler.generate(owner, mochi, mochi_tasks)
    buddy_plan = scheduler.generate(owner, buddy, buddy_tasks)

    print(mochi_plan.summary())
    print()
    print(buddy_plan.summary())
    print()

    # -----------------------------------------------------------------------
    # filter_tasks demo
    # -----------------------------------------------------------------------
    mochi_incomplete = mochi.filter_tasks(completed=False)
    buddy_walks = buddy.filter_tasks(category="walk")
    print(separator.strip())
    print("  Task Filter Results")
    print(separator.strip())
    print(f"  Mochi — incomplete tasks : {len(mochi_incomplete)}")
    print(f"  Buddy — walk tasks       : {len(buddy_walks)}")
    print()

    # -----------------------------------------------------------------------
    # tasks_sorted_by_time demo — first 3 tasks for each pet
    # -----------------------------------------------------------------------
    print(separator.strip())
    print("  Chronological Task Order (tasks_sorted_by_time)")
    print(separator.strip())
    for plan in (mochi_plan, buddy_plan):
        print(f"  {plan.pet.name}:")
        for st in plan.tasks_sorted_by_time():
            print(f"    {st.start_time} – {st.end_time}  {st.task.title}")
    print()

    # -----------------------------------------------------------------------
    # detect_conflicts
    # -----------------------------------------------------------------------
    conflicts = scheduler.detect_conflicts([mochi_plan, buddy_plan])
    print(separator.strip())
    print("  Cross-Pet Scheduling Conflicts")
    print(separator.strip())
    if not conflicts:
        print("  No conflicts detected.")
    else:
        for st_a, st_b in conflicts:
            print(
                f"  CONFLICT: [{st_a.start_time}-{st_a.end_time}] {st_a.task.title}"
                f"  <->  [{st_b.start_time}-{st_b.end_time}] {st_b.task.title}"
            )
    print()


if __name__ == "__main__":
    main()
