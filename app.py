import os
import sys

# Přidáme složku utils do cesty pro import modulů
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))

import streamlit as st
import pandas as pd
from fpdf import FPDF
from docx import Document
from supabase import create_client
import base64
import io
from datetime import datetime

# Nyní importujeme database a AI moduly
import database as db
import ai_integration as ai

# Načteme Llama model cache
tokenizer, llama_model = ai.load_llama_model()

# 🍀 Utility pro vyčištění session state
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
    st.write("Tato aplikace pomáhá vytvářet přípravu na tělovýchovnou hodinu.")
    st.session_state.setdefault("class_grade", "3. třída")
    st.write(f"Vybraná třída: {st.session_state.class_grade}")

# 2) Výběr škol a kategorií

def page_school_selection():
    st.title("Výběr škol a kategorií")
    schools = [r["value"] for r in db.get_resources("Misto")]
    st.multiselect("Vyber školy:", schools, key="selected_schools")
    st.session_state.setdefault("school_category", {})
    categories = [r["value"] for r in db.get_resources("Kategorie školy")]
    for school in st.session_state.get("selected_schools", []):
        default = st.session_state.school_category.get(school, categories[0] if categories else "")
        cat = st.radio(
            f"Kategorie pro {school}:", categories,
            index=categories.index(default) if default in categories else 0,
            key=f"cat_{school}"
        )
        st.session_state.school_category[school] = cat

# 3) Výběr prostředí a vybavení

def page_environment_equipment():
    st.title("Výběr prostředí a vybavení")
    st.selectbox("Kde se hodina koná?", ["Tělocvična", "Hřiště"], key="environment")
    equip_opts = [r["value"] for r in db.get_resources("Vybaveni")]
    st.multiselect("Vybavení:", equip_opts, key="equipment")

# 4) Nastavení rolí

def page_roles():
    st.title("Nastavení rolí")
    st.session_state.prep_leader = "Trenér"
    st.radio("Hlavní část vede:", ["Učitel","Trenér"], key="main_leader")
    st.radio("Závěrečná část vede:", ["Učitel","Trenér","Oba"], key="final_leader")

# 5) Výběr cvičebních konstruktů

def page_exercise_constructs():
    st.title("Výběr cvičebních konstruktů")
    st.multiselect("Zdatnost:", db.get_resources("Zdatnost"), key="fitness")
    st.multiselect("Manipulace s předměty:", db.get_resources("Manipulace s predmety"), key="manipulation")
    st.multiselect("Lokomoce:", db.get_resources("Lokomoce"), key="locomotion")

# 6) Správa cviků (admin)

def page_admin_exercises():
    st.title("Administrace: Správa cviků")
    exercises = db.get_exercises()
    for ex in exercises:
        with st.expander(ex["name"]):
            st.write(ex["description"])
            st.write("Sekce:", ", ".join(db.get_exercise_sections(ex["id"])))
            if st.button("Smazat cvik", key=f"del_{ex['id']}"):
                db.delete_exercise(ex["id"])
                st.experimental_rerun()
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
        st.experimental_rerun()

# 7) Výběr cviků pro hodinu

def page_select_exercises():
    st.title("Výběr cviků pro hodinu")
    if "environment" not in st.session_state:
        st.warning("Nejdříve vyberte prostředí a vybavení.")
        return
    env = st.session_state.environment
    equip = st.session_state.equipment
    for key,label in [("prep","Přípravná část"),("main","Hlavní část"),("final","Závěrečná část")]:
        st.subheader(label)
        ct = st.selectbox(f"Konstrukt ({label})", db.get_construct_types(), key=f"{key}_ct2")
        sub = st.selectbox(f"Podkategorie ({label})", db.get_subcategories(ct), key=f"{key}_sub2")
        candidates = [e for e in db.get_exercises(ct, sub, section=key)
                      if e["location"] in [env,"Obojí"] and all(m in equip for m in e.get("materials",[]))]
        opts = [f"{c['name']} – {c['description'][:50]}..." for c in candidates]
        sel = st.multiselect(f"Vyber cviky ({label}):", opts, key=f"{key}_sel2")
        st.session_state[f"selected_exercises_{key}"] = [candidates[opts.index(s)]["id"] for s in sel]

# 8) Časové rozdělení

def page_time_allocation():
    st.title("Časové rozdělení hodiny")
    st.session_state.prep_time = st.number_input("Přípravná část (min):",1,45,10,key="prep_time")
    st.session_state.main_time = st.number_input("Hlavní část (min):",1,45,25,key="main_time")
    st.session_state.final_time = st.number_input("Závěrečná část (min):",1,45,10,key="final_time")

# 9) Generování finální přípravy
def page_generate_plan():
    st.title("Písemná příprava")
    for part in ["prep","main","final"]:
        if not st.session_state.get(f"selected_exercises_{part}"):
            st.error("Vyberte cviky ve všech částech.")
            return
    lines = []
    lines.append(f"{st.session_state.class_grade} — Písemná příprava {datetime.today().date()}")
    lines.append("")
    for part,label in [("prep","Přípravná část"),("main","Hlavní část"),("final","Závěrečná část")]:
        minutes = st.session_state[f"{part}_time"]
        lines.append(f"--- {label} ({minutes} min) ---")
        for ex in db.get_exercises():
            if ex["id"] in st.session_state[f"selected_exercises_{part}"]:
                lines.append(f"- {ex['name']}: {ex['description']}")
        lines.append("")
    plan = "\n".join(lines)
    st.text_area("Výsledná příprava", plan, height=400)
    if st.button("Export PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for row in plan.split("\n"):
            pdf.multi_cell(0,10,row)
        b64 = base64.b64encode(pdf.output(dest="S").encode("latin1")).decode()
        st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="plan.pdf">Stáhnout PDF</a>', unsafe_allow_html=True)

# 10) Uložené přípravy

def page_saved_plans():
    st.title("Uložené přípravy")
    os.makedirs("output", exist_ok=True)
    for fname in sorted(os.listdir("output")):
        with open(os.path.join("output", fname),"r",encoding="utf-8") as f:
            content = f.read()
        st.subheader(fname)
        st.text_area(fname, content, height=200)
        if st.button(f"Načíst {fname}", key=f"load_{fname}"):
            st.session_state["loaded_plan"] = content

# 11) Administrace podkladů

def page_admin_resources():
    st.title("Administrace: Podklady")
    for label,key in [("Vybavení","Vybaveni"),("Zdatnost","Zdatnost"),("Manipulace","Manipulace s predmety"),("Lokomoce","Lokomoce"),("Kategorie školy","Kategorie školy"),("Místo","Misto")]:
        st.subheader(label)
        with st.form(f"res_{key}"):
            val = st.text_input("Nový podklad", key=f"val_{key}")
            if st.form_submit_button("Přidat"):
                db.add_resource(key,val)
                st.experimental_rerun()
        for r in db.get_resources(key):
            if st.button(f"Smazat {r['value']}", key=f"delres_{r['id']}"):
                db.delete_resource(r['id'])
                st.experimental_rerun()

# Hlavní funkce

def main():
    st.sidebar.title("Tělovýchovná jednotka")
    mode = st.sidebar.selectbox("Režim:",["Vytvoření hodiny","Administrace"])
    if mode=="Vytvoření hodiny":
        pages={
            "Úvod":page_intro,
            "Školy":page_school_selection,
            "Prostředí/vybavení":page_environment_equipment,
            "Role":page_roles,
            "Konstrukt":page_exercise_constructs,
            "Výběr cviků":page_select_exercises,
            "Čas":page_time_allocation,
            "Výstup":page_generate_plan,
            "Uložené":page_saved_plans
        }
    else:
        pages={
            "Správa cviků":page_admin_exercises,
            "Podklady":page_admin_resources
        }
    choice=st.sidebar.radio("Stránky:",list(pages.keys()))
    pages[choice]()

if __name__=="__main__":
    main()
