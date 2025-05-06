import streamlit as st
from datetime import date
from postgrest import APIError

from utils.database import (
    get_resources,
    add_resource,
    delete_resource,
    get_exercises,
    add_exercise,
    delete_exercise,
    get_exercise_categories,
    get_series_for_teacher,
    create_series,
    get_last_lessons,
    get_next_sequence_index,
    add_lesson_plan
)
from utils.ai_integration import generate_lesson_plan_groq

# Nastavení stránky
st.set_page_config(page_title="TV Lekce", layout="wide")

def main():
    mode = st.sidebar.selectbox("Režim", ["Vytvoření lekce", "Uložené lekce", "Administrator"])
    if mode == "Vytvoření lekce":
        render_create_lesson()
    elif mode == "Uložené lekce":
        render_saved_lessons()
    else:
        render_admin()

def render_create_lesson():
    st.title("Generátor tělovýchovné lekce")

    # 1) Kontrola uživatele
    teacher_id = st.session_state.get("user_id")
    if not teacher_id:
        st.error("Nejste přihlášen(a) jako učitel. Prosím přihlašte se.")
        return

    # 2) Načtení existujících sérií
    try:
        series = get_series_for_teacher(teacher_id)
    except APIError as e:
        st.error(f"Chyba při načítání sérií: {e}")
        series = []

    opts = {f"{s['class_name']} ({s['school_year']})": s for s in series}
    choice = st.selectbox("Vyber sérii nebo Nová série", list(opts.keys()) + ["Nová série"])
    if choice == "Nová série":
        with st.form("new_series"):
            school_id   = st.text_input("School ID")
            class_name  = st.text_input("Třída (např. 6.B)")
            subject     = st.text_input("Předmět", "TV")
            school_year = st.text_input("Školní rok", "2024/2025")
            if st.form_submit_button("Vytvořit sérii"):
                try:
                    create_series(teacher_id, school_id, class_name, subject, school_year)
                    st.success("Nová série vytvořena.")
                    st.experimental_rerun()
                except APIError as e:
                    st.error(f"Chyba při vytváření série: {e}")
        return

    meta = opts[choice]
    series_id = meta["id"]

    # 3) Historie lekcí
    try:
        prev = get_last_lessons(series_id, limit=3)
    except APIError as e:
        st.error(f"Chyba při načítání historie lekcí: {e}")
        prev = []
    if prev:
        st.subheader("Poslední lekce")
        for lesson in prev:
            st.json(lesson)

    # 4) Formulář generování
    with st.form("new_lesson"):
        lec_date    = st.date_input("Datum lekce", value=date.today())
        environment = st.selectbox("Prostředí", get_resources("Místo") or ["tělocvična","venku","hala"])
        equipment   = st.multiselect("Vybavení", get_resources("Vybavení"))
        goal        = st.text_input("Cíl lekce")

        prep = get_exercises()
        main = get_exercises()
        cool = get_exercises()

        if st.form_submit_button("Generovat lekci"):
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

    # 5) Zobrazení a uložení
    if "new_plan" in st.session_state:
        plan, params, lec_date = st.session_state["new_plan"]
        st.subheader("Vygenerovaná lekce")
        st.json(plan)
        if st.button("Uložit lekci"):
            try:
                idx = get_next_sequence_index(series_id)
                success = add_lesson_plan(series_id, idx, params, plan, lec_date.isoformat())
                if success:
                    st.success(f"Lekce uložena jako číslo {idx}.")
                else:
                    st.error("Ukládání selhalo.")
            except APIError as e:
                st.error(f"Chyba při ukládání lekce: {e}")

def render_saved_lessons():
    st.title("Uložené lekce")

    teacher_id = st.session_state.get("user_id")
    if not teacher_id:
        st.error("Nejste přihlášen(a) jako učitel. Prosím přihlašte se.")
        return

    try:
        series = get_series_for_teacher(teacher_id)
    except APIError as e:
        st.error(f"Chyba při načítání sérií: {e}")
        return

    if not series:
        st.info("Žádné uložené série lekcí.")
        return

    sel = st.selectbox("Vyber sérii", [f"{s['class_name']} ({s['school_year']})" for s in series])
    meta = next(s for s in series if f"{s['class_name']} ({s['school_year']})" == sel)

    try:
        lessons = get_last_lessons(meta["id"], limit=100)
    except APIError as e:
        st.error(f"Chyba při načítání lekcí: {e}")
        return

    if not lessons:
        st.info("Pro tuto sérii nejsou žádné lekce.")
    else:
        for i, lesson in enumerate(lessons, start=1):
            st.subheader(f"Lekce {i}")
            st.json(lesson)

def render_admin():
    st.title("Administrace")

    st.subheader("Správa zdrojů")
    resource_types = [
        "Vybavení","Místo","Cíl","Bezpečnost",
        "Metody","Kategorie školy","Zdatnost",
        "Manipulace s předměty","Lokomoce"
    ]
    tabs = st.tabs(resource_types)
    for tab, rtype in zip(tabs, resource_types):
        with tab:
            st.write(f"**{rtype}**")
            with st.form(f"add_{rtype}"):
                val = st.text_input("Nová položka")
                if st.form_submit_button("Přidat"):
                    try:
                        add_resource(rtype, val)
                        st.success("Přidáno.")
                        st.experimental_rerun()
                    except APIError as e:
                        st.error(f"Chyba při přidávání zdroje: {e}")
            try:
                items = get_resources(rtype)
            except APIError as e:
                st.error(f"Chyba při načítání zdrojů: {e}")
                items = []
            for itm in items:
                cols = st.columns((6,1))
                cols[0].write(itm["value"])
                if cols[1].button("🗑", key=f"del_{rtype}_{itm['id']}"):
                    try:
                        delete_resource(itm["id"])
                        st.experimental_rerun()
                    except APIError as e:
                        st.error(f"Chyba při mazání zdroje: {e}")

    st.subheader("Správa cviků")
    try:
        exercises = get_exercises()
    except APIError as e:
        st.error(f"Chyba při načítání cviků: {e}")
        exercises = []

    if not exercises:
        st.info("Žádné cviky k dispozici.")
    else:
        for ex in exercises:
            with st.expander(ex["name"]):
                st.write(ex["description"])
                st.write("Lokalita:", ex.get("location",""))
                st.write("Materiál:", ", ".join(ex.get("materials",[])))
                cats = get_exercise_categories(ex["id"])
                if cats:
                    st.write("Kategorie:")
                    for c in cats:
                        st.write(f"- {c['construct_type']}: {c['subcategory']}")
                if st.button("Smazat cvik", key=f"del_ex_{ex['id']}"):
                    try:
                        delete_exercise(ex["id"])
                        st.experimental_rerun()
                    except APIError as e:
                        st.error(f"Chyba při mazání cviku: {e}")

if __name__ == "__main__":
    main()
