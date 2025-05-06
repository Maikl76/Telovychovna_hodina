import subprocess
import sys

def install_package(package_name, module_name=None):
    module_name = module_name or package_name
    try:
        __import__(module_name)
    except ImportError:
        print(f"Balíček '{package_name}' není nainstalován. Probíhá instalace...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"Balíček '{package_name}' byl úspěšně nainstalován.")

# Seznam závislostí
dependencies = [
    ("streamlit", None),
    ("pandas", None),
    ("openpyxl", None),
    ("fpdf2", "fpdf"),  # fpdf2 pro Unicode
    ("python-docx", "docx")
]
for pkg, mod in dependencies:
    install_package(pkg, mod)

import streamlit as st
import os
import base64
import io
import time
from datetime import datetime
import pandas as pd

# Importy pro admins a cviky
from utils.database import (
    get_resources, get_exercises, get_construct_types,
    get_subcategories, add_resource, delete_resource,
    get_exercise_categories, delete_exercise,
    add_exercise, get_construct_types as construct_types_list,
    get_subcategories as subcategories_list
)
from utils.ai_integration import generate_exercise_suggestion

# Vymazání dat
def clear_plan_data():
    keys = [
        "plan_title", "plan_goal_select", "plan_goal_custom", "lesson_goal",
        "brief_summary", "plan_date", "plan_place_select", "plan_place_custom",
        "plan_place", "plan_material", "plan_method_select", "plan_method_custom",
        "plan_methods", "plan_safety_select", "plan_safety_custom", "plan_safety",
        "plan_instructor", "prep_output", "main_output", "final_output"
    ]
    for k in keys:
        st.session_state.pop(k, None)

# Stránky

def page_intro():
    st.title("Úvod")
    st.write("Tato aplikace pomáhá vytvořit prompt pro custom GPT model...")
    st.session_state.class_grade = "3. třída"
    st.write("Vybraná třída: 3. třída")
    st.session_state.setdefault('selected_schools', [])
    st.session_state.setdefault('school_category', {})
    st.session_state.setdefault('frequency_by_category', {"Experimentální":"5 x týdně","Semi-experimentální":"2 x týdně"})


def page_environment_equipment():
    st.title("Výběr prostředí a vybavení")
    env = st.selectbox("Kde se hodina bude konat?", ["Tělocvična","Venkovní"])
    st.session_state.environment = env
    opts = get_resources("Vybaveni")
    equipment = sorted([r['value'] for r in opts])
    st.session_state.equipment = st.multiselect("Vybavení:", equipment, default=equipment[:2])


def page_roles():
    st.title("Nastavení rolí")
    st.session_state.preparatory_leader = "Trenér"
    st.session_state.main_leader = st.radio("Hlavní část vede:",["Učitel","Trenér"])
    st.session_state.final_leader = st.radio("Závěrečná část vede:",["Učitel","Trenér","Oba"])


def page_exercise_constructs():
    st.title("Výběr cvičebních konstruktů")
    z = get_resources("Zdatnost"); m = get_resources("Manipulace s predmety"); l = get_resources("Lokomoce")
    st.session_state.fitness = st.multiselect("Zdatnost:", sorted([r['value'] for r in z]), default=[r['value'] for r in z])
    st.session_state.manipulation = st.multiselect("Manipulace s předměty:", sorted([r['value'] for r in m]), default=[r['value'] for r in m])
    st.session_state.locomotion = st.multiselect("Lokomoce:", sorted([r['value'] for r in l]), default=[r['value'] for r in l][:2])


def page_select_exercises():
    st.title("🏋️‍♀️ Výběr konkrétních cviků pro hodinu")
    if 'environment' not in st.session_state:
        st.warning("Nejdříve vyberte prostředí a vybavení.")
        return
    env = st.session_state.environment
    equip = st.session_state.equipment
    for key,label in [('prep','Přípravná část'),('main','Hlavní část'),('final','Závěrečná část')]:
        st.subheader(label)
        types = construct_types_list()
        ct = st.selectbox(f"Typ konstruktu ({label}):", types, key=f"{key}_construct")
        sc = st.selectbox(f"Podkategorie ({label}):", subcategories_list(ct), key=f"{key}_subcategory")
        exs = get_exercises(ct, sc)
        filt = [e for e in exs if e['location'] in [env,'Obojí'] and all(m in equip for m in e.get('materials',[]))]
        if not filt:
            st.info("Žádné cviky pro zadané filtry.")
            continue
        opts = {f"{e['name']} – {e['description'][:50]}...":e['id'] for e in filt}
        sel = st.multiselect(f"Vyberte cviky pro {label}:", list(opts.keys()), key=f"{key}_sel")
        st.session_state[f"selected_exercises_{key}"] = [opts[s] for s in sel]


def page_time_allocation(): ...
def page_generate_prompt(): ...
def page_generate_plan(): ...
def page_saved_plans(): ...
def page_school_selection(): ...

def admin_login(): ...
def page_admin_resources(): ...
def page_admin_exercises(): ...
def page_admin_ai_exercise(): ...

# Hlavní

def main():
    st.sidebar.title("Tělovýchovná jednotka")
    mode = st.sidebar.selectbox("Režim:",["Vytvoření hodiny","Administrator"])
    if mode=="Vytvoření hodiny":
        pages={
          "Úvod":page_intro,
          "Výběr škol a kategorií":page_school_selection,
          "Výběr prostředí":page_environment_equipment,
          "Nastavení rolí":page_roles,
          "Výběr konstruktů":page_exercise_constructs,
          "Výběr cviků":page_select_exercises,
          "Časové rozdělení":page_time_allocation,
          "Generování promptu":page_generate_prompt,
          "Export přípravy":page_generate_plan,
          "Uložené":page_saved_plans
        }
        choice=st.sidebar.radio("Stránky:",list(pages.keys()))
        pages[choice]()
    else:
        if not admin_login(): return
        admin_pages={"Správa cviků":page_admin_exercises,"AI cviky":page_admin_ai_exercise,"Podklady":page_admin_resources}
        ap=st.sidebar.radio("Administrace:",list(admin_pages.keys()))
        admin_pages[ap]()

if __name__=='__main__': main()
