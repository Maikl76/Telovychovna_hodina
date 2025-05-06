import os
import sys

# Zajistíme, aby byl podsložka utils v path
sys.path.append(os.path.dirname(__file__))

import streamlit as st
from fpdf import FPDF
import base64
import io
from datetime import datetime
import utils.database as db

# --- Utility ---
def clear_plan_data():
    for key in list(st.session_state.keys()):
        if key.startswith(("selected_exercises_", "fitness", "manipulation", "locomotion", "environment", "equipment", "main_leader", "final_leader", "prep_time", "main_time", "final_time", "selected_schools", "school_category")):
            del st.session_state[key]

# --- Page functions ---

def page_intro():
    st.title("Úvod")
    st.session_state.setdefault("class_grade", "3. třída")
    st.write(f"Vybraná třída: {st.session_state.class_grade}")


def page_school_selection():
    st.title("Výběr škol a kategorií")
    schools = [r["value"] for r in db.get_resources("Misto")]
    selected = st.multiselect(
        "Vyber školy:", schools,
        default=st.session_state.get("selected_schools", []),
        key="selected_schools"
    )
    st.session_state.selected_schools = selected

    categories = [r["value"] for r in db.get_resources("Kategorie školy")]
    st.session_state.setdefault("school_category", {})
    for school in selected:
        default = st.session_state.school_category.get(school, categories[0] if categories else "")
        cat = st.radio(
            f"Kategorie pro {school}:", categories,
            index=categories.index(default),
            key=f"cat_{school}"
        )
        st.session_state.school_category[school] = cat


def page_environment_equipment():
    st.title("Výběr prostředí a vybavení")
    env = st.selectbox(
        "Kde se hodina koná?", ["Tělocvična", "Hřiště"],
        index=["Tělocvična","Hřiště"].index(st.session_state.get("environment","Tělocvična")),
        key="environment"
    )
    st.session_state.environment = env

    equip_opts = [r["value"] for r in db.get_resources("Vybaveni")]
    equipment = st.multiselect(
        "Vybavení:", equip_opts,
        default=st.session_state.get("equipment", []),
        key="equipment"
    )
    st.session_state.equipment = equipment


def page_roles():
    st.title("Nastavení rolí")
    st.session_state.prep_leader = "Trenér"
    st.session_state.main_leader = st.radio(
        "Hlavní část vede:", ["Učitel","Trenér"],
        index=["Učitel","Trenér"].index(st.session_state.get("main_leader","Učitel")),
        key="main_leader"
    )
    st.session_state.final_leader = st.radio(
        "Závěrečná část vede:", ["Učitel","Trenér","Oba"],
        index=["Učitel","Trenér","Oba"].index(st.session_state.get("final_leader","Oba")),
        key="final_leader"
    )


def page_exercise_constructs():
    st.title("Výběr cvičebních konstruktů")
    st.session_state.fitness = st.multiselect(
        "Zdatnost:", [r["value"] for r in db.get_resources("Zdatnost")],
        default=st.session_state.get("fitness", []),
        key="fitness"
    )
    st.session_state.manipulation = st.multiselect(
        "Manipulace s předměty:", [r["value"] for r in db.get_resources("Manipulace s predmety")],
        default=st.session_state.get("manipulation", []),
        key="manipulation"
    )
    st.session_state.locomotion = st.multiselect(
        "Lokomoce:", [r["value"] for r in db.get_resources("Lokomoce")],
        default=st.session_state.get("locomotion", []),
        key="locomotion"
    )


def page_select_exercises():
    st.title("Výběr cviků pro hodinu")
    if "environment" not in st.session_state:
        st.warning("Nejdříve vyberte prostředí a vybavení.")
        return
    env = st.session_state.environment
    equip = st.session_state.equipment
    for section, label in [("prep","Přípravná část"),("main","Hlavní část"),("final","Závěrečná část")]:
        st.subheader(label)
        ct_key = f"{section}_ct"
        sub_key = f"{section}_sub"
        sel_key = f"selected_exercises_{section}"

        ct = st.selectbox(
            f"Konstrukt ({label})", db.get_construct_types(),
            index=db.get_construct_types().index(st.session_state.get(ct_key, db.get_construct_types()[0])),
            key=ct_key
        )
        sub = st.selectbox(
            f"Podkategorie ({label})", db.get_subcategories(ct),
            index=db.get_subcategories(ct).index(st.session_state.get(sub_key, db.get_subcategories(ct)[0])),
            key=sub_key
        )

        candidates = [e for e in db.get_exercises(ct, sub, section=section)
                      if e["location"] in [env, "Obojí"] and all(m in equip for m in e.get("materials", []))]
        options = [f"{c['name']} – {c['description'][:50]}..." for c in candidates]
        defaults = [options.index(o) for o in st.session_state.get(sel_key, []) if o in options]

        selected = st.multiselect(
            f"Vyber cviky ({label}):", options,
            default=[options[i] for i in defaults],
            key=sel_key
        )
        st.session_state[sel_key] = selected


def page_time_allocation():
    st.title("Časové rozdělení hodiny")
    st.session_state.prep_time = st.number_input(
        "Přípravná část (min):", 1, 45, st.session_state.get("prep_time",10), key="prep_time"
    )
    st.session_state.main_time = st.number_input(
        "Hlavní část (min):", 1, 45, st.session_state.get("main_time",25), key="main_time"
    )
    st.session_state.final_time = st.number_input(
        "Závěrečná část (min):", 1, 45, st.session_state.get("final_time",10), key="final_time"
    )


def page_generate_plan():
    st.title("Písemná příprava")
    for section in ["prep","main","final"]:
        if not st.session_state.get(f"selected_exercises_{section}"):
            st.error("Vyberte cviky ve všech částech.")
            return
    lines = [f"{st.session_state.class_grade} – Příprava hodiny {datetime.today().date()}", ""]
    for section, label in [("prep","Přípravná část"),("main","Hlavní část"),("final","Závěrečná část")]:
        minutes = st.session_state.get(f"{section}_time", 0)
        lines.append(f"--- {label} ({minutes} min) ---")
        for opt in st.session_state.get(f"selected_exercises_{section}", []):
            pass
        lines.append("")
    plan_text = "\n".join(lines)
    st.text_area("Výsledná příprava", plan_text, height=400)


def page_saved_plans():
    st.title("Uložené přípravy")
    os.makedirs("output", exist_ok=True)
    files = sorted(os.listdir("output"))
    for fname in files:
        with open(os.path.join("output", fname), "r", encoding="utf-8") as f:
            content = f.read()
        st.subheader(fname)
        st.text_area(fname, content, height=200)


def page_admin_exercises():
    st.title("Administrace: Správa cviků")
    exercises = db.get_exercises()
    for ex in exercises:
        with st.expander(ex["name"]):
            st.write(ex["description"])
            st.write("Sekce:", ", ".join(db.get_exercise_sections(ex["id"])))
            if st.button("Smazat cvik", key=f"del_{ex['id']}"):
                db.delete_exercise(ex["id"])
    st.write("---")
    st.subheader("Přidat / upravit cvik")
    ex_id = st.text_input("ID (prázdné=nový)", key="ex_id")
    name = st.text_input("Název", key="ex_name")
    desc = st.text_area("Popis", key="ex_desc")
    loc = st.selectbox("Místo", ["Tělocvična","Hřiště","Obojí"], key="ex_loc")
    mats = st.text_input("Materiály (čárka)", key="ex_mats")
    ct = st.selectbox("Konstrukt", db.get_construct_types(), key="ex_ct")
    sub = st.selectbox("Podkategorie", db.get_subcategories(ct), key="ex_sub")
    secs = st.multiselect("Sekce hodiny", ["prep","main","final"], key="ex_secs")
    if st.button("Uložit cvik"):
        mats_list = [m.strip() for m in mats.split(",") if m.strip()]
        ct_payload = [{"construct_type": ct, "subcategory": sub}]
        if ex_id:
            db.update_exercise(ex_id, name, desc, loc, mats_list, ct_payload, secs)
        else:
            db.add_exercise(name, desc, loc, mats_list, ct_payload, secs)

def page_admin_resources():
    st.title("Administrace: Podklady")
    for label, key in [
        ("Vybavení","Vybaveni"),("Zdatnost","Zdatnost"),
        ("Manipulace s předměty","Manipulace s predmety"),("Lokomoce","Lokomoce"),
        ("Kategorie školy","Kategorie školy"),("Místo","Misto")
    ]:
        st.subheader(label)
        with st.form(f"res_{key}"):
            value = st.text_input("Nový podklad", key=f"new_{key}")
            if st.form_submit_button("Přidat"):
                db.add_resource(key, value)
        for r in db.get_resources(key):
            if st.button(f"Smazat {r['value']}", key=f"del_{key}_{r['id']}"):
                db.delete_resource(r['id'])


def main():
    st.sidebar.title("Tělovýchovná jednotka")
    mode = st.sidebar.selectbox("Režim:", ["Vytvoření hodiny","Administrace"], index=["Vytvoření hodiny","Administrace"].index(st.session_state.get("mode","Vytvoření hodiny")))
    st.session_state.mode = mode
    pages = {
        "Vytvoření hodiny": [page_intro, page_school_selection, page_environment_equipment, page_roles, page_exercise_constructs, page_select_exercises, page_time_allocation, page_generate_plan, page_saved_plans],
        "Administrace": [page_admin_exercises, page_admin_resources]
    }
    step = st.sidebar.radio("Stránky:", [f.__name__.replace('page_','').replace('_',' ').title() for f in pages[mode]])
    for f in pages[mode]:
        name = f.__name__.replace('page_','').replace('_',' ').title()
        if name == step:
            f()

if __name__ == "__main__":
    main()
