import streamlit as st
from datetime import date

from utils.database import (
    get_resources, add_resource, delete_resource,
    get_exercises, add_exercise, delete_exercise, get_exercise_categories,
    get_series_for_teacher, create_series,
    get_last_lessons, get_next_sequence_index, add_lesson_plan
)
from utils.ai_integration import generate_lesson_plan_groq

st.set_page_config(page_title="TV Lekce", layout="wide")

# --- Volba režimu ---
mode = st.sidebar.selectbox("Režim", ["Vytvoření lekce", "Uložené lekce", "Administrator"])

if mode == "Vytvoření lekce":
    st.title("Generátor tělovýchovné lekce")
    teacher_id = st.session_state.get("user_id", "anon")

    # 1) Výběr nebo vytvoření série
    series = get_series_for_teacher(teacher_id)
    opts = {f"{s['class_name']} ({s['school_year']})": s for s in series}
    choice = st.selectbox("Vyber sérii nebo Nová série", list(opts.keys()) + ["Nová série"])
    if choice == "Nová série":
        with st.form("new_series"):
            school_id   = st.text_input("School ID")
            class_name  = st.text_input("Třída (např. 6.B)")
            subject     = st.text_input("Předmět", "TV")
            school_year = st.text_input("Školní rok", "2024/2025")
            if st.form_submit_button("Vytvořit"):
                meta = create_series(teacher_id, school_id, class_name, subject, school_year)
                st.success("Série vytvořena.")
                st.experimental_rerun()
    else:
        meta      = opts[choice]
        series_id = meta["id"]

    # 2) Zobrazení posledních lekcí
    prev = get_last_lessons(series_id, limit=3)
    if prev:
        st.subheader("Poslední lekce:")
        for l in prev:
            st.json(l)

    # 3) Formulář pro novou lekci
    with st.form("new_lesson"):
        lec_date    = st.date_input("Datum lekce", value=date.today())
        environment = st.selectbox("Prostředí", ["tělocvična", "venku", "hala"])
        equipment   = st.multiselect("Vybavení", get_resources("Vybavení"))
        goal        = st.text_input("Cíl lekce")

        # načtení cviků z databáze (můžete doplnit filtry podle potřeby)
        prep = get_exercises(construct_type=None, subcategory=None)
        main = get_exercises(construct_type=None, subcategory=None)
        cool = get_exercises(construct_type=None, subcategory=None)

        submitted = st.form_submit_button("Generovat lekci")
        if submitted:
            params = {
                "environment": environment,
                "equipment": equipment,
                "goal": goal,
                "prep_exercises": prep,
                "main_exercises": main,
                "cooldown_exercises": cool
            }
            plan = generate_lesson_plan_groq(meta, params, prev)
            st.session_state["new_plan"] = (plan, params, lec_date)

    # 4) Zobrazení a uložení vygenerované lekce
    if "new_plan" in st.session_state:
        plan, params, lec_date = st.session_state["new_plan"]
        st.subheader("Vygenerovaná lekce")
        st.json(plan)

        if st.button("Uložit do DB"):
            idx = get_next_sequence_index(series_id)
            ok  = add_lesson_plan(series_id, idx, params, plan, lec_date.isoformat())
            if ok:
                st.success(f"Lekce uložena jako číslo {idx}.")
            else:
                st.error("Ukládání selhalo.")

elif mode == "Uložené lekce":
    st.title("Uložené lekce")
    teacher_id = st.session_state.get("user_id", "anon")
    series     = get_series_for_teacher(teacher_id)
    sel        = st.selectbox("Vyber sérii", [f"{s['class_name']} ({s['school_year']})" for s in series])
    meta       = next(s for s in series if f"{s['class_name']} ({s['school_year']})" == sel)
    lessons    = get_last_lessons(meta["id"], limit=100)

    for i, l in enumerate(lessons, start=1):
        st.subheader(f"Lekce {i}")
        st.json(l)

else:  # Administrator
    st.title("Administrace")

    # 5a) Správa podkladů (resources)
    st.subheader("Správa podkladů")
    resource_types = ["Vybavení","Zdatnost","Manipulace s předměty","Lokomoce",
                      "Cíl","Místo","Bezpečnost","Metody","Kategorie školy"]
    tabs = st.tabs(resource_types)
    for tab, rtype in zip(tabs, resource_types):
        with tab:
            st.write(f"**{rtype}**")
            # přidání nové hodnoty
            with st.form(f"add_{rtype}"):
                val = st.text_input("Nová položka")
                if st.form_submit_button("Přidat"):
                    if add_resource(rtype, val):
                        st.success("Přidáno.")
                        st.experimental_rerun()
            # výpis existujících
            items = get_resources(rtype)
            for itm in items:
                cols = st.columns((6,1))
                cols[0].write(itm["value"])
                if cols[1].button("🗑", key=f"del_{rtype}_{itm['id']}"):
                    if delete_resource(itm["id"]):
                        st.experimental_rerun()

    # 5b) Správa cviků
    st.subheader("Správa cviků")
    exs = get_exercises()
    if not exs:
        st.info("Žádné cviky.")
    else:
        for ex in exs:
            with st.expander(ex["name"]):
                st.write(ex["description"])
                st.write("Lokalita:", ex.get("location", ""))
                st.write("Materiál:", ", ".join(ex.get("materials", [])))
                cats = get_exercise_categories(ex["id"])
                if cats:
                    st.write("Kategorie:")
                    for c in cats:
                        st.write(f"- {c['construct_type']}: {c['subcategory']}")
                if st.button("Smazat cvik", key=f"del_ex_{ex['id']}"):
                    delete_exercise(ex["id"])
                    st.experimental_rerun()
