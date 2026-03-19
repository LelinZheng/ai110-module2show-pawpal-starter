import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session state initialisation
# st.session_state works like a dictionary that survives page re-runs.
# We check "key not in st.session_state" before assigning so we never
# overwrite data the user already entered.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner: Owner | None = None

if "pet" not in st.session_state:
    st.session_state.pet: Pet | None = None

if "plan" not in st.session_state:
    st.session_state.plan = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🐾 PawPal+")
st.caption("A smart pet care scheduler for busy owners.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Owner & Pet profile
# ---------------------------------------------------------------------------

st.subheader("1. Owner & Pet Profile")

col_o, col_p = st.columns(2)

with col_o:
    st.markdown("**Owner**")
    owner_name  = st.text_input("Your name", value="Jordan")
    day_start   = st.text_input("Day starts at (HH:MM)", value="07:00")
    day_end     = st.text_input("Day ends at (HH:MM)", value="21:00")

with col_p:
    st.markdown("**Pet**")
    pet_name    = st.text_input("Pet name", value="Mochi")
    species     = st.selectbox("Species", ["dog", "cat", "other"])
    age_years   = st.number_input("Age (years)", min_value=0.0, max_value=30.0,
                                  value=3.0, step=0.5)
    special_raw = st.text_input("Special needs (comma-separated, optional)", value="")

if st.button("Save profile"):
    special_needs = [s.strip() for s in special_raw.split(",") if s.strip()]
    st.session_state.owner = Owner(
        name=owner_name,
        day_start=day_start,
        day_end=day_end,
    )
    # Pet carries its own task list — tasks added via add_task() live here
    st.session_state.pet = Pet(
        name=pet_name,
        species=species,
        age_years=age_years,
        special_needs=special_needs,
    )
    st.session_state.plan = None   # reset any previous schedule
    st.success(
        f"Profile saved — {owner_name} & {st.session_state.pet.summary()} "
        f"| {st.session_state.owner.total_available_minutes()} min available today"
    )

# Show a compact reminder of what's currently saved so the user knows
# session state is working.
if st.session_state.owner:
    st.info(
        f"Active profile: **{st.session_state.owner.name}** "
        f"({st.session_state.owner.day_start}–{st.session_state.owner.day_end}) "
        f"with **{st.session_state.pet.summary()}**"
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 2 — Task management
# ---------------------------------------------------------------------------

st.subheader("2. Add Tasks")

col1, col2, col3 = st.columns(3)
with col1:
    task_title  = st.text_input("Task title", value="Morning walk")
    category    = st.selectbox("Category",
                               ["walk", "feed", "medication", "enrichment", "grooming", "vet"])
with col2:
    duration    = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    priority    = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=2)
with col3:
    earliest    = st.text_input("Earliest start (HH:MM, optional)", value="")
    deadline    = st.text_input("Deadline (HH:MM, optional)", value="")
    notes       = st.text_input("Notes (optional)", value="")

if st.button("Add task"):
    if not st.session_state.pet:
        st.error("Save your owner & pet profile first (Section 1).")
    else:
        task = Task(
            title=task_title,
            category=category,
            duration_minutes=int(duration),
            priority=priority,
            earliest_start=earliest.strip() or None,
            deadline=deadline.strip() or None,
            notes=notes.strip(),
        )
        # Route through the domain method so pet.task_count() stays accurate
        st.session_state.pet.add_task(task)
        st.session_state.plan = None   # new task → old schedule is stale
        st.success(
            f"Added '{task_title}' to {st.session_state.pet.name} "
            f"({st.session_state.pet.task_count()} task(s) total)"
        )

# Read the task list directly from the Pet object — single source of truth
pet_tasks = st.session_state.pet.tasks if st.session_state.pet else []

if pet_tasks:
    st.markdown(f"**{st.session_state.pet.task_count()} task(s) assigned to {st.session_state.pet.name}:**")
    rows = [
        {
            "Title": t.title,
            "Category": t.category,
            "Duration": t.duration_minutes,
            "Priority": t.priority,
            "Earliest": t.earliest_start or "—",
            "Deadline": t.deadline or "—",
        }
        for t in pet_tasks
    ]
    st.table(rows)

    if st.button("Clear all tasks"):
        st.session_state.pet.tasks.clear()   # clear via the Pet object
        st.session_state.plan = None
        st.rerun()
else:
    st.info("No tasks yet — add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Section 3 — Generate schedule
# ---------------------------------------------------------------------------

st.subheader("3. Generate Schedule")

if st.button("Generate schedule", type="primary"):
    if not st.session_state.owner or not st.session_state.pet:
        st.error("Save your owner & pet profile first (Section 1).")
    elif not st.session_state.pet.tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        try:
            scheduler = Scheduler()
            # Pass pet.tasks — the list populated by pet.add_task()
            st.session_state.plan = scheduler.generate(
                st.session_state.owner,
                st.session_state.pet,
                st.session_state.pet.tasks,
            )
        except ValueError as exc:
            st.error(f"Scheduling error: {exc}")

if st.session_state.plan:
    plan = st.session_state.plan

    # Summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Scheduled", f"{len(plan.scheduled)} tasks")
    m2.metric("Total time", f"{plan.total_minutes_scheduled} min")
    m3.metric("Unscheduled", f"{len(plan.unscheduled)} tasks")

    # Scheduled task cards
    if plan.scheduled:
        st.markdown("#### Today's Plan")
        for st_task in sorted(plan.scheduled, key=lambda s: s.start_time):
            st.markdown(
                f"**{st_task.start_time} – {st_task.end_time}** &nbsp; "
                f"`{st_task.task.priority}` &nbsp; **{st_task.task.title}**  \n"
                f"*{st_task.reason}*"
            )

    # Unscheduled warnings
    if plan.unscheduled:
        st.markdown("#### ⚠️ Could Not Schedule")
        for task, reason in plan.unscheduled:
            st.warning(f"**{task.title}** ({task.duration_minutes} min) — {reason}")

    # Raw text summary in an expander
    with st.expander("Full plain-text summary"):
        st.text(plan.summary())
