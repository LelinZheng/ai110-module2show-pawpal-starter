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
        Task(
            title="Breakfast Feeding",
            category="feed",
            duration_minutes=10,
            priority="high",
            earliest_start="08:30",
        ),
        Task(
            title="Enrichment Play",
            category="enrichment",
            duration_minutes=20,
            priority="medium",
            earliest_start="10:00",
        ),
        Task(
            title="Dinner Feeding",
            category="feed",
            duration_minutes=10,
            priority="high",
            earliest_start="17:00",
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
    # Generate and print plans
    # -----------------------------------------------------------------------
    separator = "\n" + "=" * 50 + "\n"

    print(separator.strip())
    print(f"  PawPal+ — Today's Schedule for {owner.name}")
    print(f"  Window: {owner.day_start} – {owner.day_end}"
          f"  ({owner.total_available_minutes()} min available)")
    print(separator.strip())

    for pet, tasks in [(mochi, mochi_tasks), (buddy, buddy_tasks)]:
        plan = scheduler.generate(owner, pet, tasks)
        print(plan.summary())
        print()


if __name__ == "__main__":
    main()
