import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler, _parse_time, _format_time

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner: Owner | None = None

if "pets" not in st.session_state:
    st.session_state.pets: list[Pet] = []

if "plans" not in st.session_state:
    st.session_state.plans: dict = {}

# editing_task stores (pet_name, task_index) when a task is being edited
if "editing_task" not in st.session_state:
    st.session_state.editing_task: tuple | None = None

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

with st.form("owner_form"):
    col_o1, col_o2, col_o3 = st.columns(3)
    with col_o1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col_o2:
        day_start = st.text_input("Day starts at (HH:MM)", value="07:00")
    with col_o3:
        day_end = st.text_input("Day ends at (HH:MM)", value="21:00")
    save_owner = st.form_submit_button("Save owner")

if save_owner:
    st.session_state.owner = Owner(name=owner_name, day_start=day_start, day_end=day_end)
    st.session_state.plans = {}
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

with st.expander("➕ Add a pet", expanded=len(st.session_state.pets) == 0):
    with st.form("add_pet_form"):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            pet_name = st.text_input("Pet name", value="")
        with col_p2:
            species   = st.selectbox("Species", ["dog", "cat", "other"])
            age_years = st.number_input("Age (years)", min_value=0.0,
                                        max_value=30.0, value=3.0, step=0.5)
        with col_p3:
            special_raw = st.text_input("Special needs (comma-separated)", value="")
        add_pet = st.form_submit_button("Add pet")

    if add_pet:
        if not st.session_state.owner:
            st.error("Save your owner profile first (Section 1).")
        elif not pet_name.strip():
            st.error("Pet name cannot be empty.")
        else:
            existing = [p.name.lower() for p in st.session_state.pets]
            if pet_name.strip().lower() in existing:
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
                st.success(f"Added pet: {new_pet.summary()}")

if st.session_state.pets:
    st.markdown(f"**{len(st.session_state.pets)} pet(s) registered:**")
    for i, pet in enumerate(st.session_state.pets):
        col_l, col_r = st.columns([5, 1])
        with col_l:
            st.markdown(f"- {pet.summary()} &nbsp; `{pet.task_count()} task(s)`")
        with col_r:
            if st.button("Remove", key=f"remove_pet_{i}"):
                st.session_state.pets.pop(i)
                st.session_state.plans = {}
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
    pet_names   = [p.name for p in st.session_state.pets]
    target_name = st.selectbox("Assign task to", pet_names)
    target_pet  = next(p for p in st.session_state.pets if p.name == target_name)

    # Pre-fill defaults — used when editing an existing task
    edit_info = st.session_state.editing_task
    editing_this_pet = (
        edit_info is not None
        and edit_info[0] == target_pet.name
        and edit_info[1] < len(target_pet.tasks)
    )
    if editing_this_pet:
        et = target_pet.tasks[edit_info[1]]
        d_title    = et.title
        d_category = et.category
        d_duration = et.duration_minutes
        d_priority = et.priority
        d_earliest = et.earliest_start or ""
        d_deadline = et.deadline or ""
        d_notes    = et.notes
    else:
        d_title, d_category, d_duration = "", "walk", 20
        d_priority, d_earliest, d_deadline, d_notes = "high", "", "", ""

    form_label = f"✏️ Editing task #{edit_info[1]} for {target_pet.name}" \
        if editing_this_pet else "Add task"

    with st.form("add_task_form"):
        if editing_this_pet:
            st.info(f"Editing: **{d_title}** — submit to save changes, or cancel below.")
        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value=d_title)
            category   = st.selectbox(
                "Category",
                ["walk", "feed", "medication", "enrichment", "grooming", "vet"],
                index=["walk", "feed", "medication", "enrichment", "grooming", "vet"].index(d_category),
            )
        with col2:
            duration = st.number_input("Duration (min)", min_value=1,
                                       max_value=240, value=d_duration)
            priority = st.selectbox(
                "Priority", ["low", "medium", "high", "critical"],
                index=["low", "medium", "high", "critical"].index(d_priority),
            )
        with col3:
            earliest = st.text_input("Earliest start (HH:MM, optional)", value=d_earliest)
            deadline = st.text_input("Deadline (HH:MM, optional)", value=d_deadline)
            notes    = st.text_input("Notes (optional)", value=d_notes)
        submit_label = "Save changes" if editing_this_pet else "Add task"
        submitted = st.form_submit_button(submit_label)

    if editing_this_pet and st.button("Cancel edit"):
        st.session_state.editing_task = None
        st.rerun()

    if submitted:
        if not task_title.strip():
            st.error("Task title cannot be empty.")
        else:
            earliest_val = earliest.strip() or None
            deadline_val = deadline.strip() or None

            # Deadline validation: warn if task cannot finish before its deadline
            deadline_warning = None
            if earliest_val and deadline_val:
                e_min = _parse_time(earliest_val)
                d_min = _parse_time(deadline_val)
                finish = e_min + int(duration)
                if finish > d_min:
                    deadline_warning = (
                        f"Deadline {deadline_val} is too early — "
                        f"'{task_title}' starting at {earliest_val} "
                        f"would finish at {_format_time(finish)}, "
                        f"after the deadline. Adjust the deadline or duration."
                    )

            if deadline_warning:
                st.warning(f"⚠️ {deadline_warning}")
                st.info("Fix the deadline or duration above and resubmit.")
            else:
                task = Task(
                    title=task_title.strip(),
                    category=category,
                    duration_minutes=int(duration),
                    priority=priority,
                    earliest_start=earliest_val,
                    deadline=deadline_val,
                    notes=notes.strip(),
                )
                if editing_this_pet:
                    target_pet.tasks[edit_info[1]] = task
                    st.session_state.editing_task = None
                    st.session_state.plans.pop(target_pet.name, None)
                    st.success(f"Updated '{task.title}' for {target_pet.name}.")
                else:
                    target_pet.add_task(task)
                    st.session_state.plans.pop(target_pet.name, None)
                    st.success(
                        f"Added '{task.title}' to {target_pet.name} "
                        f"({target_pet.task_count()} task(s) total)"
                    )

    # ---- Task list with per-task Edit / Delete ----
    st.markdown("---")
    for pet in st.session_state.pets:
        if not pet.tasks:
            continue
        with st.expander(f"{pet.name} — {pet.task_count()} task(s)", expanded=True):
            for idx, t in enumerate(pet.tasks):
                cols = st.columns([3, 2, 1, 1, 1, 1])
                cols[0].markdown(f"**{t.title}**")
                cols[1].caption(f"{t.category} · {t.duration_minutes}min · {t.priority}")
                cols[2].caption(t.earliest_start or "—")
                cols[3].caption(t.deadline or "—")
                if cols[4].button("✏️", key=f"edit_{pet.name}_{idx}", help="Edit"):
                    st.session_state.editing_task = (pet.name, idx)
                    st.rerun()
                if cols[5].button("🗑️", key=f"del_{pet.name}_{idx}", help="Delete"):
                    pet.tasks.pop(idx)
                    st.session_state.plans.pop(pet.name, None)
                    if (st.session_state.editing_task and
                            st.session_state.editing_task == (pet.name, idx)):
                        st.session_state.editing_task = None
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
    schedule_options = [p.name for p in pets_with_tasks] if pets_with_tasks \
        else ["(no pets with tasks)"]
    schedule_for = st.selectbox("Generate schedule for", schedule_options)

    if st.button("Generate schedule", type="primary"):
        if not st.session_state.owner:
            st.error("Save your owner profile first (Section 1).")
        elif not pets_with_tasks:
            st.warning("Add at least one task to a pet before generating a schedule.")
        else:
            selected_pet = next(p for p in st.session_state.pets if p.name == schedule_for)
            scheduler = Scheduler()

            # Only warn about truly impossible scheduling (both tasks have tight deadlines)
            input_warnings = scheduler.check_input_conflicts(selected_pet.tasks)
            for w in input_warnings:
                st.warning(f"⚠️ {w}")

            try:
                plan = scheduler.generate(
                    st.session_state.owner,
                    selected_pet,
                    selected_pet.tasks,
                )
                st.session_state.plans[selected_pet.name] = plan
            except ValueError as exc:
                st.error(f"Scheduling error: {exc}")

    # Cross-pet conflict detection
    active_plans = list(st.session_state.plans.values())
    if len(active_plans) >= 2:
        scheduler = Scheduler()
        cross_conflicts = scheduler.detect_conflicts(active_plans)
        if cross_conflicts:
            st.error(
                f"⚠️ **{len(cross_conflicts)} cross-pet conflict(s)** — "
                f"{st.session_state.owner.name} is double-booked:"
            )
            for st_a, st_b in cross_conflicts:
                st.warning(
                    f"**{st_a.task.title}** ({st_a.start_time}–{st_a.end_time}) "
                    f"overlaps **{st_b.task.title}** ({st_b.start_time}–{st_b.end_time})"
                )

    current_plan = st.session_state.plans.get(schedule_for)
    if current_plan:
        plan = current_plan

        m1, m2, m3 = st.columns(3)
        m1.metric("Scheduled", f"{len(plan.scheduled)} tasks")
        m2.metric("Total time", f"{plan.total_minutes_scheduled} min")
        m3.metric("Unscheduled", f"{len(plan.unscheduled)} tasks")

        if plan.scheduled:
            st.markdown(f"#### Today's Plan — {plan.pet.name}")
            for st_task in plan.tasks_sorted_by_time():
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
