import streamlit as st
import pandas as pd
from fpdf import FPDF
from docx import Document
from supabase import create_client
import os
import base64
import io
from datetime import datetime

from utils.database import (
    get_resources,
    get_exercises,
    add_exercise,
    update_exercise,
    delete_exercise,
    get_exercise_sections,
    get_construct_types,
    get_subcategories,
    add_resource,
    delete_resource
)

# Vymazání starých dat v session
def clear_plan_data():
    keys = [
        "plan_title", "lesson_goal", "brief_summary", "plan_date", "plan_place",
        "plan_material", "plan_methods", "plan_safety", "plan_instructor",
        "selected_exercises_prep", "selected_exercises_main", "selected_exercises_final",
        "prep_time", "main_time", "final_time"
    ]
    for k in keys:
        st.session_state.pop(k, None)

# 1) Úvod
def page_intro():
    st.title("Úvod")
    st.write("Aplikace pro tvorbu tělovýchovné hodiny.")
    st.session_state.setdefault("class_grade", "3. třída")
    st.write(f"Vybraná třída: {st.session_state.class_grade}")

# 2) Výběr škol a kategorií
def page_school_selection():
    st.title("Výběr škol a kategorií")
    schools = [r["value"] for r in get_resources("Misto")]
    selected = st.multiselect("Vyber školy:", schools, key="selected_schools")
    st.session_state.selected_schools = selected

    categories = [r["value"] for r in get_resources("Kategorie školy")]
    st.session_state.setdefault("school_category", {})
    for s in selected:
        default = st.session_state.school_category.get(s, categories[0] if categories else "")
        cat = st.radio(
            f"Kategorie pro {s}:",
            categories,
            index=categories.index(default) if default in categories else 0,
            key=f"cat_{s}"
        )
        st.session_state.school_category[s] = cat

# 3) Prostředí a vybavení
def page_environment_equipment():
    st.title("Výběr prostředí a vybavení")
    env = st.selectbox("Kde se hodina koná?", ["Tělocvična", "Hřiště"], key="environment")
    st.session_state.environment = env

    equip_opts = [r["value"] for r in get_resources("Vybaveni")]
    equip = st.multiselect("Vybavení:", equip_opts, key="equipment")
    st.session_state.equipment = equip

# 4) Nastavení rolí
def page_roles():
    st.title("Nastavení rolí")
    st.session_state.prep_leader = "Trenér"
    st.session_state.main_leader = st.radio("Hlavní část vede:", ["Učitel", "Trenér"], key="main_leader")
    st.session_state.final_leader = st.radio("Závěrečná část vede:", ["Učitel", "Trenér", "Oba"], key="final_leader")

# 5) Výběr cvičebních konstruktů
def page_exercise_constructs():
    st.title("Výběr cvičebních konstruktů")
    st.session_state.fitness = st.multiselect("Zdatnost:", get_resources("Zdatnost"), key="fitness")
    st.session_state.manipulation = st.multiselect("Manipulace s předměty:", get_resources("Manipulace s predmety"), key="manipulation")
    st.session_state.locomotion = st.multiselect("Lokomoce:", get_resources("Lokomoce"), key="locomotion")

# 6) Administrace: správa cviků
def page_admin_exercises():
    st.title("Administrace: Správa cviků")
    exercises = get_exercises()
    for ex in exercises:
        with st.expander(f"{ex['name']}"):
            st.write(ex["description"])
            st.write("Sekce:", ", ".join(get_exercise_sections(ex["id"])))
            if st.button("Smazat", key=f"del_{ex['id']}"):
                delete_exercise(ex["id"])
                st.experimental_rerun()

    st.write("---")
    st.subheader("Přidat / upravit cvik")
    ex_id = st.text_input("ID (ponechat prázdné pro nový)", key="ex_id")
    name = st.text_input("Název", key="ex_name")
    desc = st.text_area("Popis", key="ex_desc")
    loc = st.selectbox("Místo", ["Tělocvična", "Hřiště", "Obojí"], key="ex_loc")
    mats = st.text_input("Materiály (čárkou)", key="ex_mats")
    ct = st.selectbox("Konstrukt", get_construct_types(), key="ex_ct")
    sub = st.selectbox("Podkategorie", get_subcategories(ct), key="ex_sub")
    sections = st.multiselect("Sekce hodiny", ["prep", "main", "final"], key="ex_sections")

    if st.button("Uložit cvik"):
        mats_list = [m.strip() for m in mats.split(",") if m.strip()]
        construct_types = [{"construct_type": ct, "subcategory": sub}]
        if ex_id:
            update_exercise(ex_id, name, desc, loc, mats_list, construct_types, sections)
        else:
            add_exercise(name, desc, loc, mats_list, construct_types, sections)
        st.success("Cvik uložen.")
        st.experimental_rerun()

# 7) Výběr cviků pro hodinu
def page_select_exercises():
    st.title("Výběr cviků pro hodinu")
    if "environment" not in st.session_state:
        st.warning("Nejdříve vyberte prostředí a vybavení.")
        return

    env = st.session_state.environment
    equip = st.session_state.equipment

    for key, label in [("prep", "Přípravná část"), ("main", "Hlavní část"), ("final", "Závěrečná část")]:
        st.subheader(label)
        ct = st.selectbox(f"Konstrukt ({label})", get_construct_types(), key=f"{key}_ct2")
        sub = st.selectbox(f"Podkategorie ({label})", get_subcategories(ct), key=f"{key}_sub2")
        candidates = [
            e for e in get_exercises(ct, sub, section=key)
            if e["location"] in [env, "Obojí"] and all(m in equip for m in e.get("materials", []))
        ]
        options = [f"{c['name']} – {c['description'][:50]}..." for c in candidates]
        sel = st.multiselect(f"Vyber cviky ({label}):", options, key=f"{key}_sel2")
        st.session_state[f"selected_exercises_{key}"] = [
            candidates[options.index(s)]["id"] for s in sel
        ]

# 8) Časové rozdělení hodiny
def page_time_allocation():
    st.title("Časové rozdělení hodiny")
    st.session_state.prep_time = st.number_input("Přípravná část (min):", 1, 45, 10, key="prep_time")
    st.session_state.main_time = st.number_input("Hlavní část (min):", 1, 45, 25, key="main_time")
    st.session_state.final_time = st.number_input("Závěrečná část (min):", 1, 45, 10, key="final_time")

# 9) Generování finální přípravy a export
def page_generate_plan():
    st.title("Generování písemné přípravy")
    # Zkontrolovat, že cviky jsou vybrané
    for part in ["prep", "main", "final"]:
        if not st.session_state.get(f"selected_exercises_{part}"):
            st.error("Vyberte cviky ve všech částech.")
            return

    lines = []
    lines.append(f"{st.session_state.class_grade} – Písemná příprava hodiny {datetime.today().date()}")
    lines.append("")  # prázdný řádek
    for part, label in [("prep", "Přípravná část"), ("main", "Hlavní část"), ("final", "Závěrečná část")]:
        minutes = st.session_state[f"{part}_time"]
        lines.append(f"--- {label} ({minutes} min) ---")
        ids = st.session_state[f"selected_exercises_{part}"]
        for ex in get_exercises():
            if ex["id"] in ids:
                lines.append(f"- {ex['name']}: {ex['description']}")
        lines.append("")  # prázdný řádek

    full_plan = "\n".join(lines)
    st.text_area("Výsledná příprava", full_plan, height=400)

    if st.button("Exportovat PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for row in full_plan.split("\n"):
            pdf.multi_cell(0, 10, row)
        pdf_bytes = pdf.output(dest="S").encode("latin1")
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="plan.pdf">Stáhnout PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

# 10) Uložené přípravy
def page_saved_plans():
    st.title("Uložené přípravy")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    files = sorted(os.listdir(output_dir))
    for fname in files:
        path = os.path.join(output_dir, fname)
        with open(path, "r", encoding="utf-8") as fp:
            content = fp.read()
        st.subheader(fname)
        st.text_area(fname, content, height=200)
        if st.button(f"Načíst {fname}", key=f"load_{fname}"):
            # zde můžete načíst obsah zpět do session
            st.session_state["loaded_plan"] = content
            st.success("Načteno.")

# 11) Administrace: podklady
def page_admin_resources():
    st.title("Administrace: Podklady")
    types = [
        ("Vybavení", "Vybaveni"),
        ("Zdatnost", "Zdatnost"),
        ("Manipulace s předměty", "Manipulace s predmety"),
        ("Lokomoce", "Lokomoce"),
        ("Kategorie školy", "Kategorie školy"),
        ("Misto", "Misto")
    ]
    for label, rtype in types:
        st.subheader(label)
        with st.form(f"add_{rtype}"):
            val = st.text_input("Nová hodnota", key=f"res_{rtype}")
            if st.form_submit_button("Přidat"):
                add_resource(rtype, val)
                st.experimental_rerun()
        items = get_resources(rtype)
        for item in items:
            if st.button(f"Smazat {item['value']}", key=f"delres_{item['id']}"):
                delete_resource(item["id"])
                st.experimental_rerun()

# Hlavní funkce
def main():
    st.sidebar.title("Tělovýchovná jednotka")
    mode = st.sidebar.selectbox("Režim:", ["Vytvoření hodiny", "Administrace"])
    if mode == "Vytvoření hodiny":
        pages = {
            "Úvod": page_intro,
            "Výběr škol": page_school_selection,
            "Prostředí/vybavení": page_environment_equipment,
            "Role": page_roles,
            "Konstrukt": page_exercise_constructs,
            "Výběr cviků": page_select_exercises,
            "Čas": page_time_allocation,
            "Výstup": page_generate_plan,
            "Uložené": page_saved_plans
        }
    else:
        pages = {
            "Správa cviků": page_admin_exercises,
            "Podklady": page_admin_resources
        }
    choice = st.sidebar.radio("Stránky:", list(pages.keys()))
    pages[choice]()

if __name__ == "__main__":
    main()
