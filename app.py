import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner: Owner | None = None

if "pets" not in st.session_state:
    st.session_state.pets: list[Pet] = []   # all pets for this owner

if "plan" not in st.session_state:
    st.session_state.plan = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🐾 PawPal+")
st.caption("A smart pet care scheduler for busy owners.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Owner profile
# ---------------------------------------------------------------------------

st.subheader("1. Owner Profile")

col_o1, col_o2, col_o3 = st.columns(3)
with col_o1:
    owner_name = st.text_input("Your name", value="Jordan")
with col_o2:
    day_start = st.text_input("Day starts at (HH:MM)", value="07:00")
with col_o3:
    day_end = st.text_input("Day ends at (HH:MM)", value="21:00")

if st.button("Save owner"):
    st.session_state.owner = Owner(name=owner_name, day_start=day_start, day_end=day_end)
    st.session_state.plan = None
    st.success(
        f"Owner saved — **{owner_name}** | "
        f"{st.session_state.owner.total_available_minutes()} min available today"
    )

if st.session_state.owner:
    st.info(
        f"Active owner: **{st.session_state.owner.name}** "
        f"({st.session_state.owner.day_start}–{st.session_state.owner.day_end})"
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 2 — Pet management
# ---------------------------------------------------------------------------

st.subheader("2. Pets")

# --- Add a new pet ---
with st.expander("➕ Add a pet", expanded=len(st.session_state.pets) == 0):
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        pet_name   = st.text_input("Pet name", value="Mochi")
    with col_p2:
        species    = st.selectbox("Species", ["dog", "cat", "other"])
        age_years  = st.number_input("Age (years)", min_value=0.0, max_value=30.0,
                                     value=3.0, step=0.5)
    with col_p3:
        special_raw = st.text_input("Special needs (comma-separated, optional)", value="")

    if st.button("Add pet"):
        if not st.session_state.owner:
            st.error("Save your owner profile first (Section 1).")
        else:
            # Check for duplicate name
            existing_names = [p.name.lower() for p in st.session_state.pets]
            if pet_name.strip().lower() in existing_names:
                st.warning(f"A pet named '{pet_name}' is already added.")
            else:
                special_needs = [s.strip() for s in special_raw.split(",") if s.strip()]
                new_pet = Pet(
                    name=pet_name.strip(),
                    species=species,
                    age_years=age_years,
                    special_needs=special_needs,
                )
                st.session_state.pets.append(new_pet)
                st.session_state.plan = None
                st.success(f"Added pet: {new_pet.summary()}")

# --- Show registered pets ---
if st.session_state.pets:
    st.markdown(f"**{len(st.session_state.pets)} pet(s) registered:**")
    for i, pet in enumerate(st.session_state.pets):
        col_l, col_r = st.columns([5, 1])
        with col_l:
            st.markdown(f"- {pet.summary()} &nbsp; `{pet.task_count()} task(s)`")
        with col_r:
            if st.button("Remove", key=f"remove_pet_{i}"):
                st.session_state.pets.pop(i)
                st.session_state.plan = None
                st.rerun()
else:
    st.info("No pets yet — add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Section 3 — Task management
# ---------------------------------------------------------------------------

st.subheader("3. Add Tasks")

if not st.session_state.pets:
    st.info("Add at least one pet (Section 2) before adding tasks.")
else:
    # Pet selector — choose which pet gets this task
    pet_names   = [p.name for p in st.session_state.pets]
    target_name = st.selectbox("Assign task to", pet_names)
    target_pet  = next(p for p in st.session_state.pets if p.name == target_name)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
        category   = st.selectbox("Category",
                                  ["walk", "feed", "medication", "enrichment", "grooming", "vet"])
    with col2:
        duration   = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        priority   = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=2)
    with col3:
        earliest   = st.text_input("Earliest start (HH:MM, optional)", value="")
        deadline   = st.text_input("Deadline (HH:MM, optional)", value="")
        notes      = st.text_input("Notes (optional)", value="")

    if st.button("Add task"):
        task = Task(
            title=task_title,
            category=category,
            duration_minutes=int(duration),
            priority=priority,
            earliest_start=earliest.strip() or None,
            deadline=deadline.strip() or None,
            notes=notes.strip(),
        )
        target_pet.add_task(task)
        st.session_state.plan = None
        st.success(
            f"Added '{task_title}' to {target_pet.name} "
            f"({target_pet.task_count()} task(s) total)"
        )

    # Show each pet's current task list
    st.markdown("---")
    for pet in st.session_state.pets:
        if pet.tasks:
            with st.expander(f"{pet.name} — {pet.task_count()} task(s)", expanded=True):
                rows = [
                    {
                        "Title": t.title,
                        "Category": t.category,
                        "Duration": t.duration_minutes,
                        "Priority": t.priority,
                        "Earliest": t.earliest_start or "—",
                        "Deadline": t.deadline or "—",
                    }
                    for t in pet.tasks
                ]
                st.table(rows)
                if st.button(f"Clear {pet.name}'s tasks", key=f"clear_{pet.name}"):
                    pet.tasks.clear()
                    st.session_state.plan = None
                    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------

st.subheader("4. Generate Schedule")

if not st.session_state.pets:
    st.info("Add pets and tasks first.")
else:
    pets_with_tasks = [p for p in st.session_state.pets if p.tasks]
    schedule_for    = st.selectbox(
        "Generate schedule for",
        [p.name for p in pets_with_tasks] if pets_with_tasks else ["(no pets with tasks)"],
    )

    if st.button("Generate schedule", type="primary"):
        if not st.session_state.owner:
            st.error("Save your owner profile first (Section 1).")
        elif not pets_with_tasks:
            st.warning("Add at least one task to a pet before generating a schedule.")
        else:
            selected_pet = next(p for p in st.session_state.pets if p.name == schedule_for)
            try:
                st.session_state.plan = Scheduler().generate(
                    st.session_state.owner,
                    selected_pet,
                    selected_pet.tasks,
                )
            except ValueError as exc:
                st.error(f"Scheduling error: {exc}")

if st.session_state.plan:
    plan = st.session_state.plan

    m1, m2, m3 = st.columns(3)
    m1.metric("Scheduled", f"{len(plan.scheduled)} tasks")
    m2.metric("Total time", f"{plan.total_minutes_scheduled} min")
    m3.metric("Unscheduled", f"{len(plan.unscheduled)} tasks")

    if plan.scheduled:
        st.markdown(f"#### Today's Plan — {plan.pet.name}")
        for st_task in sorted(plan.scheduled, key=lambda s: s.start_time):
            st.markdown(
                f"**{st_task.start_time} – {st_task.end_time}** &nbsp; "
                f"`{st_task.task.priority}` &nbsp; **{st_task.task.title}**  \n"
                f"*{st_task.reason}*"
            )

    if plan.unscheduled:
        st.markdown("#### ⚠️ Could Not Schedule")
        for task, reason in plan.unscheduled:
            st.warning(f"**{task.title}** ({task.duration_minutes} min) — {reason}")

    with st.expander("Full plain-text summary"):
        st.text(plan.summary())
