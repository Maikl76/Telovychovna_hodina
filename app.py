import subprocess
import sys

def install_package(package_name, module_name=None):
    # Pokud není uvedeno, použijeme název balíčku jako název modulu
    module_name = module_name or package_name
    try:
        __import__(module_name)
    except ImportError:
        print(f"Balíček '{package_name}' není nainstalován. Probíhá instalace...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"Balíček '{package_name}' byl úspěšně nainstalován.")

# Seznam závislostí ve formě (název pro pip, název modulu pro import, pokud se liší)
dependencies = [
    ("streamlit", None),
    ("pandas", None),
    ("openpyxl", None),
    ("fpdf2", "fpdf"),  # Použijeme fpdf2 místo fpdf pro lepší podporu Unicode
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

# Funkce pro vymazání dat na stránce přípravy
def clear_plan_data():
    keys_to_clear = [
        "plan_title",
        "plan_goal_select",
        "plan_goal_custom",
        "lesson_goal",
        "brief_summary",
        "plan_date",
        "plan_place_select",
        "plan_place_custom",
        "plan_place",
        "plan_material",
        "plan_method_select",
        "plan_method_custom",
        "plan_methods",
        "plan_safety_select",
        "plan_safety_custom",
        "plan_safety",
        "plan_instructor",
        "prep_output",
        "main_output",
        "final_output"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# Stránka Úvod
def page_intro():
    st.title("Úvod")
    st.write("Tato aplikace pomáhá vytvořit prompt pro custom GPT model a následně generovat písemnou přípravu na školní tělovýchovnou hodinu.")
    # Fixně nastavíme 3. třídu
    st.session_state.class_grade = "3. třída"
    st.write("Vybraná třída: 3. třída")
    
    # Inicializace session state pro školy a kategorie, pokud ještě neexistují
    if 'selected_schools' not in st.session_state:
        st.session_state.selected_schools = []
    if 'school_category' not in st.session_state:
        st.session_state.school_category = {}
    if 'frequency_by_category' not in st.session_state:
        st.session_state.frequency_by_category = {
            "Experimentální": "5 x týdně",
            "Semi-experimentální": "2 x týdně"
        }

# Stránka Výběr prostředí a vybavení
def page_environment_equipment():
    st.title("Výběr prostředí a vybavení")
    env = st.selectbox("Vyberte, kde se hodina bude konat:", ["Tělocvična", "Venkovní"])
    st.session_state.environment = env
    st.write("Vybrané prostředí:", env)
    
    st.write("Vyberte dostupné vybavení:")
    try:
        from utils.database import get_resources
    except ImportError:
        st.error("Modul database.py není dostupný. Zkontrolujte instalaci.")
        get_resources = lambda x: []

    def load_resource_options(resource_type):
        resources = get_resources(resource_type)
        if resources:
            return sorted([res['value'] for res in resources])
        else:
            st.warning(f"Žádné data pro typ '{resource_type}' nenalezena v databázi.")
            return []

    equipment_options = load_resource_options("Vybaveni")
    equipment_selected = st.multiselect("Vybavení:", equipment_options, default=equipment_options[:2] if equipment_options else [])
    st.session_state.equipment = equipment_selected

# Stránka Nastavení rolí vedoucích
def page_roles():
    st.title("Nastavení rolí vedoucích")
    st.write("Přípravná část: Vede trenér (neměnitelné)")
    st.session_state.preparatory_leader = "Trenér"
    
    main_leader = st.radio("Hlavní část: Vyberte vedoucího:", ["Učitel", "Trenér"])
    st.session_state.main_leader = main_leader
    
    final_leader = st.radio("Závěrečná část: Vyberte vedoucího:", ["Učitel", "Trenér", "Oba"])
    st.session_state.final_leader = final_leader
    
    st.write("Nastavené role:")
    st.write("• Přípravná část: Trenér")
    st.write("• Hlavní část:", main_leader)
    st.write("• Závěrečná část:", final_leader)

# Stránka Výběr cvičebních konstruktů a podkategorií
def page_exercise_constructs():
    st.title("Výběr cvičebních konstruktů a podkategorií")
    
    try:
        from utils.database import get_resources
    except ImportError:
        st.error("Modul database.py není dostupný. Zkontrolujte instalaci.")
        get_resources = lambda x: []

    def load_resource_options(resource_type):
        resources = get_resources(resource_type)
        if resources:
            return sorted([res['value'] for res in resources])
        else:
            st.warning(f"Žádné data pro typ '{resource_type}' nenalezena v databázi.")
            return []

    fitness_options = load_resource_options("Zdatnost")
    manipulation_options = load_resource_options("Manipulace s predmety")
    locomotion_options = load_resource_options("Lokomoce")
    
    st.write("**Zdatnost:**")
    fitness_selected = st.multiselect("Zdatnost:", fitness_options, default=fitness_options)
    st.session_state.fitness = fitness_selected
    
    st.write("**Manipulace s předměty:**")
    manipulation_selected = st.multiselect("Manipulace s předměty:", manipulation_options, default=manipulation_options)
    st.session_state.manipulation = manipulation_selected
    
    st.write("**Lokomoce:**")
    locomotion_selected = st.multiselect("Lokomoce:", locomotion_options, default=locomotion_options[:2] if locomotion_options else [])
    st.session_state.locomotion = locomotion_selected

# === Nová stránka: Výběr konkrétních cviků pro hodinu ===
from utils.database import get_exercises, get_subcategories

def page_select_exercises():
    st.title("🏋️‍♀️ Výběr konkrétních cviků pro hodinu")

    if "environment" not in st.session_state:
        st.warning("Nejdříve vyberte prostředí a vybavení v předchozí sekci.")
        return

    environment = st.session_state.get("environment", "Tělocvična")
    equipment = st.session_state.get("equipment", [])

    section_configs = [
        ("prep", "Přípravná část"),
        ("main", "Hlavní část"),
        ("final", "Závěrečná část")
    ]

    for section_key, section_label in section_configs:
        st.subheader(section_label)

        construct_type = st.selectbox(
            f"Typ konstruktu ({section_label}):",
            get_subcategories(None),
            key=f"{section_key}_construct"
        )
        subcategory = st.selectbox(
            f"Podkategorie ({section_label}):",
            get_subcategories(construct_type),
            key=f"{section_key}_subcategory"
        )

        all_exercises = get_exercises(construct_type, subcategory)
        filtered_exercises = [
            ex for ex in all_exercises
            if ex["location"] in [environment, "Obojí"] and
               all(m in equipment for m in ex.get("materials", []))
        ]

        if not filtered_exercises:
            st.info("Nenalezeny vhodné cviky pro dané filtrování.")
            continue

        options = {f"{ex['name']} – {ex['description'][:40]}...": ex['id'] for ex in filtered_exercises}
        selected = st.multiselect(
            f"Vyberte cviky pro {section_label}:",
            options=list(options.keys()),
            key=f"{section_key}_selected"
        )
        st.session_state[f"selected_exercises_{section_key}"] = [options[label] for label in selected]

# ... pokračují ostatní stránky: page_time_allocation, page_generate_prompt, page_generate_plan, page_saved_plans, page_school_selection, admin_login, page_admin_resources, page_admin_exercises, page_admin_ai_exercise
def main():
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    st.sidebar.title("Tělovýchovná jednotka")
    app_mode = st.sidebar.selectbox(
        "Vyberte režim:",
        ["Vytvoření hodiny", "Administrator"]
    )

    if app_mode == "Vytvoření hodiny":
        st.sidebar.title("Navigace")
        pages = {
            "Úvod": page_intro,
            "Výběr škol a kategorií": page_school_selection,
            "Výběr prostředí a vybavení": page_environment_equipment,
            "Nastavení rolí": page_roles,
            "Výběr cvičebních konstruktů": page_exercise_constructs,
            "Výběr cviků": page_select_exercises,
            "Časové rozdělení hodiny": page_time_allocation,
            "Generování promptu": page_generate_prompt,
            "Vygenerování písemné přípravy a export": page_generate_plan,
            "Uložené přípravy": page_saved_plans
        }
        choice = st.sidebar.radio("Vyberte stránku:", list(pages.keys()))
        pages[choice]()

    elif app_mode == "Administrator":
        if not admin_login():
            st.info("Pro přístup do administrace se musíte přihlásit.")
            return
        admin_pages = {
            "Správa cviků": page_admin_exercises,
            "Vytvoření cviku s AI": page_admin_ai_exercise,
            "Správa podkladů": page_admin_resources,
        }
        admin_choice = st.sidebar.radio("Administrace:", list(admin_pages.keys()))
        admin_pages[admin_choice]()

if __name__ == '__main__':
    main()
