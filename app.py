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
    # Nahrazeno načítáním z Supabase místo Excelu
    try:
        from utils.database import get_resources
    except ImportError:
        st.error("Modul database.py není dostupný. Zkontrolujte instalaci.")
        get_resources = lambda x: []  # Fallback, pokud modul chybí

    # Funkce pro načtení možností z Supabase
    def load_resource_options(resource_type):
        resources = get_resources(resource_type)
        if resources:
            # Řazení podle hodnoty abecedně
            return sorted([res['value'] for res in resources])
        else:
            st.warning(f"Žádné data pro typ '{resource_type}' nenalezena v databázi.")
            return []  # Vrátí prázdný seznam, pokud data chybí

    equipment_options = load_resource_options("Vybaveni")
    # Uživatel si může vybrat vybavení, defaultně se vyberou první dvě položky (pokud existují)
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
    
    # Nahrazeno načítáním z Supabase místo Excelu
    try:
        from utils.database import get_resources
    except ImportError:
        st.error("Modul database.py není dostupný. Zkontrolujte instalaci.")
        get_resources = lambda x: []  # Fallback, pokud modul chybí

    # Funkce pro načtení možností z Supabase
    def load_resource_options(resource_type):
        resources = get_resources(resource_type)
        if resources:
            # Řazení podle hodnoty abecedně
            return sorted([res['value'] for res in resources])
        else:
            st.warning(f"Žádné data pro typ '{resource_type}' nenalezena v databázi.")
            return []  # Vrátí prázdný seznam, pokud data chybí

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

# Stránka Časové rozdělení hodiny
def page_time_allocation():
    st.title("Časové rozdělení hodiny")
    st.write("Celkový čas hodiny: 45 minut")
    
    st.session_state.preparatory_time = st.number_input("Doba přípravné části (min):", min_value=1, max_value=45, value=10, step=1)
    st.session_state.main_time = st.number_input("Doba hlavní části (min):", min_value=1, max_value=45, value=25, step=1)
    st.session_state.final_time = st.number_input("Doba závěrečné části (min):", min_value=1, max_value=45, value=10, step=1)
    
    total_time = st.session_state.preparatory_time + st.session_state.main_time + st.session_state.final_time
    if total_time != 45:
        st.warning(f"Celkový čas musí být 45 minut. Aktuálně je: {total_time} minut.")
    else:
        st.success("Celkový čas je správně nastaven na 45 minut.")

# Stránka Generování promptu pro custom GPT model
def page_generate_prompt():
    st.title("Generování promptu pro custom GPT model")
    
    if 'class_grade' not in st.session_state or 'selected_schools' not in st.session_state or not st.session_state.selected_schools:
        st.error("Nejprve vyplňte předchozí kroky včetně výběru škol.")
        return
    
    equipment_text = ", ".join(st.session_state.equipment)
    # Dynamicky vytvoříme řetězec vybraných kategorií – spojíme volby z "Zdatnost", "Manipulace s předměty" a "Lokomoce"
    selected_categories = ", ".join(st.session_state.fitness + st.session_state.manipulation + st.session_state.locomotion)
    
    # Vytvoření přehledu škol a jejich kategorií
    schools_info = []
    exp_schools = []
    semi_exp_schools = []
    
    for school in st.session_state.selected_schools:
        category = st.session_state.school_category[school]
        frequency = st.session_state.frequency_by_category[category]
        schools_info.append(f"{school} ({category}, {frequency})")
        
        # Rozdělení škol podle kategorií
        if category == "Experimentální":
            exp_schools.append(school)
        else:
            semi_exp_schools.append(school)
    
    schools_text = ", ".join(schools_info)
    
    # Výpočet efektivního času pro cvičení (70% z celkového času)
    prep_effective_time = int(st.session_state.preparatory_time * 0.7)
    main_effective_time = int(st.session_state.main_time * 0.7)
    final_effective_time = int(st.session_state.final_time * 0.7)
    
    # Vytvoření specifických pokynů podle frekvence hodin
    exp_instructions = ""
    semi_exp_instructions = ""
    
    if exp_schools:
        exp_schools_text = ", ".join(exp_schools)
        exp_instructions = f"""
- Pro experimentální školy ({exp_schools_text}) s frekvencí 5x týdně:
  * Hodiny by měly být intenzivnější a zaměřené na systémový rozvoj pohybových dovedností
  * Každý den v týdnu by měl mít jiné zaměření (např. pondělí - koordinace, úterý - síla, středa - vytrvalost, atd.)
  * Cvičení by měla být rozmanitější a progresivně náročnější"""
    
    if semi_exp_schools:
        semi_exp_schools_text = ", ".join(semi_exp_schools)
        semi_exp_instructions = f"""
- Pro semi-experimentální školy ({semi_exp_schools_text}) s frekvencí 2x týdně:
  * Hodiny by měly být komplexnější a pokrývat více oblastí v jedné hodině
  * Zaměřit se na základní pohybové dovednosti a jejich kombinace
  * Cvičení by měla být přizpůsobena menší frekvenci a zaměřena na efektivitu"""
    
    prompt = f"""Navrhni školní tělovýchovnou hodinu pro {st.session_state.class_grade} základní školy, trvající 45 minut, rozdělenou na:
1. Přípravnou část (vede {st.session_state.preparatory_leader}) – zaměřenou na zahřívací, mobilizační a koordinační cviky. Použij databázi cviků pro přípravnou část.
2. Hlavní část (vede {st.session_state.main_leader}) – obsahující cvičení podporující: {selected_categories}.
   Pro každou z těchto kategorií vyber konkrétní cviky z databáze, které odpovídají věkovým specifikům žáků.
3. Závěrečnou část (vede {st.session_state.final_leader}) – zakončenou společným cvičením zaměřeným na statický strečink, relaxaci a mentální uklidnění. Použij databázi cviků pro závěrečnou část.

Výuka se bude konat v prostředí: {st.session_state.environment} s vybavením: {equipment_text}.

Časové rozdělení: 
Přípravná část: {st.session_state.preparatory_time} minut celkem, z toho max. {prep_effective_time} minut na samotná cvičení (zbytek času je vyhrazen na přestávky mezi cvičeními, přesun mezi stanovišti, instrukce, atd.)
Hlavní část: {st.session_state.main_time} minut celkem, z toho max. {main_effective_time} minut na samotná cvičení
Závěrečná část: {st.session_state.final_time} minut celkem, z toho max. {final_effective_time} minut na samotná cvičení

Tato hodina je určena pro následujících škol a jejich kategorie:
{schools_text}

Specifické pokyny podle frekvence hodin:{exp_instructions}{semi_exp_instructions}

Důležité pokyny:
1. Navrhni cvičení tak, aby zabrala MAXIMÁLNĚ 70% celkového času každé části. Zbytek času je vyhrazen na přestávky mezi cvičeními, přesun mezi stanovišti, instrukce, atd.
2. U každého cvičení uveď jeho název, popis a časovou dotaci v minutách.
3. Vedle detailního návrhu jednotlivých částí vytvoř také sekci "Stručný obsah", která shrnuje, jaké cviky a metody byly použity.
"""
    st.text_area("Vygenerovaný prompt:", prompt, height=500)
    
    b64 = base64.b64encode(prompt.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="prompt.txt">Stáhnout prompt</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.write("Zkopírujte prompt do vašeho custom GPT modelu a vygenerujte návrh hodiny. Poté zkopírujte výstup do stránky 'Vygenerování písemné přípravy a export'.")

# Stránka Vygenerování písemné přípravy a export (PDF) s rozšířenými poli
def page_generate_plan():
    st.title("Vygenerování písemné přípravy a export")
    
    # Tlačítko pro kompletní vymazání dat na této stránce
    if st.button("Vymazat vše"):
        clear_plan_data()
        st.rerun()
    
    # Nahrazeno načítáním z Supabase místo Excelu
    try:
        from utils.database import get_resources
    except ImportError:
        st.error("Modul database.py není dostupný. Zkontrolujte instalaci.")
        get_resources = lambda x: []  # Fallback, pokud modul chybí

    # Funkce pro načtení možností z Supabase
    def load_resource_options(resource_type):
        resources = get_resources(resource_type)
        if resources:
            # Řazení podle hodnoty abecedně
            return sorted([res['value'] for res in resources])
        else:
            st.warning(f"Žádné data pro typ '{resource_type}' nenalezena v databázi.")
            return []  # Vrátí prázdný seznam, pokud data chybí

    goal_options = load_resource_options("Cil")
    place_options = load_resource_options("Misto")
    safety_options = load_resource_options("Bezpecnost")
    method_options = load_resource_options("Metody")
    
    st.subheader("Zadejte základní informace o přípravě")
    plan_title = st.text_input("Nadpis přípravy:", key="plan_title")
    
    # Kombinovaná volba pro cíl hodiny
    if goal_options:
        goal_selected = st.selectbox("Cíl hodiny:", options=goal_options + ["Jiný (zadejte vlastní)"], key="plan_goal_select")
        if goal_selected == "Jiný (zadejte vlastní)":
            lesson_goal = st.text_input("Zadejte vlastní cíl hodiny:", key="plan_goal_custom")
        else:
            lesson_goal = goal_selected
    else:
        lesson_goal = st.text_input("Cíl hodiny:", key="lesson_goal")
    
    brief_summary = st.text_area("Stručný obsah (přípravná, hlavní, závěrečná část):", key="brief_summary")
    
    col1, col2 = st.columns(2)
    plan_date = col1.date_input("Datum:", key="plan_date")
    if place_options:
        place_selected = st.selectbox("Místo:", options=place_options + ["Jiný (zadejte vlastní)"], key="plan_place_select")
        if place_selected == "Jiný (zadejte vlastní)":
            plan_place = st.text_input("Zadejte vlastní místo:", key="plan_place_custom")
        else:
            plan_place = place_selected
    else:
        plan_place = st.text_input("Místo:", key="plan_place")
    
    # Materiál a vybavení – předvyplněno ze stránky Výběr prostředí a vybavení
    prepopulated_equipment = ", ".join(st.session_state.equipment) if "equipment" in st.session_state else ""
    plan_material = st.text_area("Materiál a vybavení:", key="plan_material", value=prepopulated_equipment)
    
    # Rozevírací nabídka pro Použité metody
    if method_options:
        method_selected = st.selectbox("Použité metody:", options=method_options + ["Jiné (zadejte vlastní)"], key="plan_method_select")
        if method_selected == "Jiné (zadejte vlastní)":
            plan_methods = st.text_input("Zadejte vlastní metody:", key="plan_method_custom")
        else:
            plan_methods = method_selected
    else:
        plan_methods = st.text_input("Použité metody:", key="plan_methods")
    
    # Rozevírací nabídka pro Bezpečnost
    if safety_options:
        safety_selected = st.selectbox("Bezpečnost:", options=safety_options + ["Jiná (zadejte vlastní)"], key="plan_safety_select")
        if safety_selected == "Jiná (zadejte vlastní)":
            plan_safety = st.text_input("Zadejte vlastní bezpečnost:", key="plan_safety_custom")
        else:
            plan_safety = safety_selected
    else:
        plan_safety = st.text_input("Bezpečnost:", key="plan_safety")
    
    plan_instructor = st.text_input("Jméno učitele/trenéra:", key="plan_instructor")
    
    st.info("Vložte výstupy z custom GPT modelu pro jednotlivé části hodiny.")
    prep_output = st.text_area("Výstup z custom GPT modelu - Přípravná část:", height=150, key="prep_output")
    main_output = st.text_area("Výstup z custom GPT modelu - Hlavní část:", height=150, key="main_output")
    final_output = st.text_area("Výstup z custom GPT modelu - Závěrečná část:", height=150, key="final_output")
    
    if not (prep_output or main_output or final_output):
        st.info("Zadejte výstupy pro všechny části hodiny.")
        return
    
    # Sestavení finální přípravy
    full_plan = f"""{plan_title} ({plan_date.strftime("%Y-%m-%d")})
Cíl hodiny: {lesson_goal}
Stručný obsah: {brief_summary}

Datum: {plan_date.strftime("%Y-%m-%d")}    Místo: {plan_place}
Materiál a vybavení: {plan_material}
Použité metody: {plan_methods}
Bezpečnost: {plan_safety}
Jméno učitele/trenéra: {plan_instructor}

--- PŘÍPRAVNÁ ČÁST ---
{prep_output}

--- HLAVNÍ ČÁST ---
{main_output}

--- ZÁVĚREČNÁ ČÁST ---
{final_output}
"""
    st.subheader("Finální písemná příprava na hodinu")
    st.text_area("Přehled přípravy", full_plan, height=300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Exportovat jako PDF"):
            try:
                from fpdf import FPDF
            except ImportError:
                st.error("Není nainstalován modul fpdf2. Nainstalujte jej pomocí 'pip install fpdf2'.")
            else:
                # Použití FPDF2 s podporou Unicode a fonty Times
                pdf = FPDF()
                pdf.add_page()
                
                # Kontrola, zda existují fonty Times a TimesBd
                import os
                times_exists = os.path.exists('times.ttf')
                timesbd_exists = os.path.exists('timesbd.ttf')
                
                if times_exists and timesbd_exists:
                    # Použití fontů Times a TimesBd
                    pdf.add_font('Times', '', fname='times.ttf', uni=True)
                    pdf.add_font('Times', 'B', fname='timesbd.ttf', uni=True)
                    
                    # Nastavení okrajů
                    pdf.set_margins(10, 10, 10)
                    
                    # Nadpis s tučným písmem
                    pdf.set_font('Times', 'B', 16)
                    pdf.cell(0, 10, plan_title, ln=True, align='C')
                    pdf.ln(5)
                    
                    # Základní informace v tabulce
                    col_width1 = 50  # Šířka prvního sloupce
                    col_width2 = 130  # Šířka druhého sloupce
                    row_height = 8
                    
                    # Tabulka pro základní informace
                    pdf.set_font('Times', 'B', 11)
                    
                    # Cíl hodiny
                    pdf.cell(col_width1, row_height, "Cíl hodiny:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, lesson_goal, border=1)
                    
                    # Stručný obsah
                    pdf.set_font('Times', 'B', 11)
                    pdf.cell(col_width1, row_height, "Stručný obsah:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, brief_summary, border=1)
                    
                    # Datum
                    pdf.set_font('Times', 'B', 11)
                    pdf.cell(col_width1, row_height, "Datum:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, plan_date.strftime('%Y-%m-%d'), border=1)
                    
                    # Místo
                    pdf.set_font('Times', 'B', 11)
                    pdf.cell(col_width1, row_height, "Místo:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, plan_place, border=1)
                    
                    # Materiál a vybavení
                    pdf.set_font('Times', 'B', 11)
                    pdf.cell(col_width1, row_height, "Materiál a vybavení:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, plan_material, border=1)
                    
                    # Použité metody
                    pdf.set_font('Times', 'B', 11)
                    pdf.cell(col_width1, row_height, "Použité metody:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, plan_methods, border=1)
                    
                    # Bezpečnost
                    pdf.set_font('Times', 'B', 11)
                    pdf.cell(col_width1, row_height, "Bezpečnost:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, plan_safety, border=1)
                    
                    # Jméno učitele/trenéra
                    pdf.set_font('Times', 'B', 11)
                    pdf.cell(col_width1, row_height, "Jméno učitele/trenéra:", border=1)
                    pdf.set_font('Times', '', 11)
                    pdf.multi_cell(col_width2, row_height, plan_instructor, border=1)
                    
                    pdf.ln(5)
                    
                    # Funkce pro parsování cvičení a vytvoření tabulky
                    def parse_exercises_and_create_table(section_title, section_text):
                        # Nadpis sekce
                        pdf.set_font('Times', 'B', 14)
                        pdf.cell(0, 10, section_title, ln=True)
                        pdf.ln(2)
                        
                        # Záhlaví tabulky cvičení
                        page_width = pdf.w - 2*pdf.l_margin  # Dostupná šířka stránky
                        col_width_desc = page_width * 0.8  # 80% šířky pro popis
                        col_width_time = page_width * 0.2  # 20% šířky pro čas
                        
                        pdf.set_font('Times', 'B', 11)
                        
                        # Cvičení
                        pdf.cell(col_width_desc, row_height, "Název a popis cvičení", border=1)
                        pdf.cell(col_width_time, row_height, "Čas (min)", border=1, ln=True, align='C')
                        
                        # Rozdělení textu na řádky a hledání cvičení
                        lines = section_text.split('\n')
                        i = 0
                        
                        while i < len(lines):
                            line = lines[i].strip()
                            
                            # Hledáme řádek, který obsahuje název cvičení a časovou dotaci
                            if line and not line.startswith('---'):
                                # Pokus o nalezení časové dotace na konci řádku (např. "... (5 min)")
                                exercise_name = line
                                exercise_time = ""
                                
                                # Hledáme časovou dotaci ve formátu (X min) nebo X min
                                if "min)" in line:
                                    parts = line.split("(")
                                    if len(parts) > 1 and "min)" in parts[-1]:
                                        exercise_name = "(".join(parts[:-1]).strip()
                                        exercise_time = parts[-1].strip()
                                        if exercise_time.endswith(")"):
                                            exercise_time = exercise_time[:-1]
                                elif "min" in line:
                                    parts = line.split()
                                    for j in range(len(parts)-1):
                                        if parts[j].isdigit() and parts[j+1] == "min":
                                            exercise_time = f"{parts[j]} min"
                                            exercise_name = line.replace(exercise_time, "").strip()
                                
                                # Sbíráme popis cvičení z následujících řádků
                                description = []
                                j = i + 1
                                while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("---"):
                                    # Kontrola, zda následující řádek není nové cvičení s časovou dotací
                                    next_line = lines[j].strip()
                                    if ("min)" in next_line and "(" in next_line) or (" min" in next_line and any(c.isdigit() for c in next_line)):
                                        break
                                    description.append(next_line)
                                    j += 1
                                
                                # Přidání řádku do tabulky
                                pdf.set_font('Times', 'B', 11)
                                pdf.cell(col_width_desc, row_height, exercise_name, border=1)
                                pdf.cell(col_width_time, row_height, exercise_time, border=1, ln=True, align='C')
                                
                                # Popis cvičení, pokud existuje
                                if description:
                                    pdf.set_font('Times', '', 11)
                                    # Ošetření znaků, které mohou způsobovat problémy
                                    desc_text = "\n".join(description)
                                    # Nahrazení speciálních znaků, které mohou způsobovat čtverečky
                                    desc_text = desc_text.replace('\u2022', '-')  # Nahrazení odrážky pomlčkou
                                    desc_text = desc_text.replace('\u2013', '-')  # Nahrazení dlouhé pomlčky krátkou
                                    desc_text = desc_text.replace('\u2014', '-')  # Nahrazení dlouhé pomlčky krátkou
                                    desc_text = desc_text.replace('\u2018', "'")  # Nahrazení uvozovek
                                    desc_text = desc_text.replace('\u2019', "'")  # Nahrazení uvozovek
                                    desc_text = desc_text.replace('\u201c', '"')  # Nahrazení uvozovek
                                    desc_text = desc_text.replace('\u201d', '"')  # Nahrazení uvozovek
                                    pdf.multi_cell(col_width_desc + col_width_time, row_height, desc_text, border=1)
                                
                                i = j  # Přeskočíme zpracované řádky
                            else:
                                i += 1
                        
                        pdf.ln(5)
                    
                    # Zpracování jednotlivých částí hodiny
                    parse_exercises_and_create_table("PŘÍPRAVNÁ ČÁST", prep_output)
                    parse_exercises_and_create_table("HLAVNÍ ČÁST", main_output)
                    parse_exercises_and_create_table("ZÁVĚREČNÁ ČÁST", final_output)
                else:
                    # Pokud fonty Times neexistují, zobrazíme varování
                    st.warning("Fonty times.ttf a timesbd.ttf nebyly nalezeny. PDF bude vygenerováno s náhradním fontem.")
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    # Nahrazení českých znaků a speciálních znaků
                    ascii_text = full_plan
                    # Nahrazení speciálních znaků, které mohou způsobovat čtverečky
                    ascii_text = ascii_text.replace('\u2022', '-')  # Nahrazení odrážky pomlčkou
                    ascii_text = ascii_text.replace('\u2013', '-')  # Nahrazení dlouhé pomlčky krátkou
                    ascii_text = ascii_text.replace('\u2014', '-')  # Nahrazení dlouhé pomlčky krátkou
                    ascii_text = ascii_text.replace('\u2018', "'")  # Nahrazení uvozovek
                    ascii_text = ascii_text.replace('\u2019', "'")  # Nahrazení uvozovek
                    ascii_text = ascii_text.replace('\u201c', '"')  # Nahrazení uvozovek
                    ascii_text = ascii_text.replace('\u201d', '"')  # Nahrazení uvozovek
                    # Pak teprve převedeme na ASCII
                    ascii_text = ascii_text.encode('ascii', 'replace').decode('ascii')
                    for line in ascii_text.split('\n'):
                        pdf.multi_cell(0, 10, line)
                
                # Export PDF
                try:
                    pdf_output = pdf.output(dest="S").encode("latin1") if (times_exists and timesbd_exists) else pdf.output(dest="S")
                    b64_pdf = base64.b64encode(pdf_output).decode()
                    pdf_href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="priprava.pdf">Stáhnout PDF</a>'
                    st.markdown(pdf_href, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Chyba při generování PDF: {e}")
                    st.info("Zkuste exportovat jako Word, který podporuje české znaky.")
    with col2:
        if st.button("Exportovat jako Word"):
            try:
                from docx import Document
                from docx.shared import Cm, Pt
                from docx.enum.text import WD_ALIGN_PARAGRAPH
            except ImportError:
                st.error("Není nainstalován modul python-docx. Nainstalujte jej pomocí 'pip install python-docx'.")
            else:
                document = Document()
                
                # Nastavení stylu dokumentu - použití fontu Times
                style = document.styles['Normal']
                style.font.name = 'Times New Roman'
                style.font.size = Pt(11)
                
                # Nastavení stylů nadpisů
                for i in range(1, 4):
                    heading_style = document.styles[f'Heading {i}']
                    heading_style.font.name = 'Times New Roman'
                    heading_style.font.bold = True
                
                # Nadpis dokumentu
                heading = document.add_heading(plan_title, level=1)
                heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Nastavení šířky stránky pro A4 s většími okraji
                section = document.sections[0]
                section.page_width = Cm(21)    # Šířka A4
                section.page_height = Cm(29.7)  # Výška A4
                section.left_margin = Cm(3.5)   # Levý okraj - zvětšeno
                section.right_margin = Cm(3.5)  # Pravý okraj - zvětšeno
                section.top_margin = Cm(2.5)    # Horní okraj
                section.bottom_margin = Cm(2.5)  # Dolní okraj
                
                # Vytvoření tabulky pro základní informace - upravené šířky pro formát A4
                info_table = document.add_table(rows=8, cols=2)  # Zvýšení počtu řádků na 8 (přidání samostatného řádku pro Místo)
                info_table.style = 'Table Grid'
                info_table.autofit = False
                
                # Nastavení šířky sloupců - výrazně zmenšeno pro A4
                info_table.columns[0].width = Cm(3)     # První sloupec
                info_table.columns[1].width = Cm(10)    # Druhý sloupec
                
                # Naplnění tabulky základními informacemi
                rows = info_table.rows
                
                # Cíl hodiny
                rows[0].cells[0].text = "Cíl hodiny:"
                rows[0].cells[1].text = lesson_goal
                
                # Stručný obsah
                rows[1].cells[0].text = "Stručný obsah:"
                rows[1].cells[1].text = brief_summary
                
                # Datum - samostatný řádek
                rows[2].cells[0].text = "Datum:"
                rows[2].cells[1].text = plan_date.strftime('%Y-%m-%d')
                
                # Místo - samostatný řádek
                rows[3].cells[0].text = "Místo:"
                rows[3].cells[1].text = plan_place
                
                # Materiál a vybavení - posunuto o jeden řádek níže
                rows[4].cells[0].text = "Materiál a vybavení:"
                rows[4].cells[1].text = plan_material
                
                # Použité metody - posunuto o jeden řádek níže
                rows[5].cells[0].text = "Použité metody:"
                rows[5].cells[1].text = plan_methods
                
                # Bezpečnost - posunuto o jeden řádek níže
                rows[6].cells[0].text = "Bezpečnost:"
                rows[6].cells[1].text = plan_safety
                
                # Jméno učitele/trenéra - posunuto o jeden řádek níže
                rows[7].cells[0].text = "Jméno učitele/trenéra:"
                rows[7].cells[1].text = plan_instructor
                
                # Nastavení tučného písma pro první sloupec
                for row in info_table.rows:
                    for cell in row.cells[:1]:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.bold = True
                
                # Přidání mezery po tabulce
                document.add_paragraph("")
                
                # Funkce pro parsování částí hodiny a vytváření tabulek se 2 sloupci
                def parse_exercises_and_create_table(section_text, document):
                    # Přidání nadpisu sekce
                    document.add_heading(section_text.split('\n')[0] if '\n' in section_text else "Cvičení", level=2)
                    
                    # Vytvoření tabulky se 2 sloupci - výrazně zmenšeno pro A4
                    table = document.add_table(rows=1, cols=2)
                    table.style = 'Table Grid'
                    table.autofit = False
                    
                    # Nastavení šířky sloupců (85% / 15%) - výrazně zmenšeno pro A4
                    table.columns[0].width = Cm(11)   # Sloupec pro název a popis cviku
                    table.columns[1].width = Cm(2)    # Sloupec pro čas
                    
                    # Nastavení záhlaví tabulky
                    hdr_cells = table.rows[0].cells
                    hdr_cells[0].text = "Název a popis cvičení"
                    hdr_cells[1].text = "Čas (min)"
                    
                    # Nastavení tučného písma pro záhlaví a zarovnání
                    for i, cell in enumerate(hdr_cells):
                        for paragraph in cell.paragraphs:
                            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            for run in paragraph.runs:
                                run.font.bold = True
                    
                    # Rozdělení textu na řádky a hledání cvičení
                    lines = section_text.split('\n')
                    i = 1  # Přeskočíme nadpis
                    
                    while i < len(lines):
                        line = lines[i].strip()
                        
                        # Hledáme řádek, který obsahuje název cvičení a časovou dotaci
                        if line and not line.startswith('---'):
                            # Pokus o nalezení časové dotace na konci řádku (např. "... (5 min)")
                            time_match = None
                            exercise_name = line
                            exercise_time = ""
                            
                            # Hledáme časovou dotaci ve formátu (X min) nebo X min
                            if "min)" in line:
                                parts = line.split("(")
                                if len(parts) > 1 and "min)" in parts[-1]:
                                    exercise_name = "(".join(parts[:-1]).strip()
                                    exercise_time = parts[-1].strip()
                                    if exercise_time.endswith(")"):
                                        exercise_time = exercise_time[:-1]
                            elif "min" in line:
                                parts = line.split()
                                for j in range(len(parts)-1):
                                    if parts[j].isdigit() and parts[j+1] == "min":
                                        exercise_time = f"{parts[j]} min"
                                        exercise_name = line.replace(exercise_time, "").strip()
                            
                            # Sbíráme popis cvičení z následujících řádků
                            description = []
                            j = i + 1
                            while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("---"):
                                # Kontrola, zda následující řádek není nové cvičení s časovou dotací
                                next_line = lines[j].strip()
                                if ("min)" in next_line and "(" in next_line) or (" min" in next_line and any(c.isdigit() for c in next_line)):
                                    break
                                description.append(next_line)
                                j += 1
                            
                            # Přidání řádku do tabulky
                            row_cells = table.add_row().cells
                            
                            # Název a popis cvičení v prvním sloupci
                            row_cells[0].text = ""
                            paragraph = row_cells[0].paragraphs[0]
                            
                            # Název cvičení tučně
                            run = paragraph.add_run(exercise_name)
                            run.font.bold = True
                            
                            # Popis cvičení normálním písmem pod názvem
                            if description:
                                desc_text = "\n" + "\n".join(description)
                                paragraph.add_run(desc_text)
                            
                            # Časová dotace zarovnaná na střed v druhém sloupci
                            row_cells[1].text = exercise_time
                            for paragraph in row_cells[1].paragraphs:
                                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            
                            i = j  # Přeskočíme zpracované řádky
                        else:
                            i += 1
                
                # Zpracování jednotlivých částí hodiny
                document.add_heading("PŘÍPRAVNÁ ČÁST", level=2)
                parse_exercises_and_create_table(prep_output, document)
                
                document.add_heading("HLAVNÍ ČÁST", level=2)
                parse_exercises_and_create_table(main_output, document)
                
                document.add_heading("ZÁVĚREČNÁ ČÁST", level=2)
                parse_exercises_and_create_table(final_output, document)
                
                # Uložení dokumentu
                f = io.BytesIO()
                document.save(f)
                f.seek(0)
                b64_docx = base64.b64encode(f.read()).decode()
                docx_href = f'<a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64_docx}" download="priprava.docx">Stáhnout Word</a>'
                st.markdown(docx_href, unsafe_allow_html=True)
    
    if st.button("Uložit přípravu"):
        if not os.path.exists("output"):
            os.makedirs("output")
        # Název uložené přípravy = Nadpis přípravy + Datum
        filename = f"output/{plan_title}_{plan_date.strftime('%Y%m%d')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(full_plan)
        st.success(f"Příprava uložena jako {filename}")

# Stránka Uložené přípravy
def page_saved_plans():
    st.title("Uložené přípravy")
    if not os.path.exists("output"):
        st.info("Žádné přípravy zatím nejsou uloženy.")
        return

    files = os.listdir("output")
    if files:
        files = sorted(files, key=lambda x: os.path.getmtime(os.path.join("output", x)), reverse=True)
        for file in files:
            file_path = os.path.join("output", file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            st.subheader(f"Příprava: {file}")
            st.text_area("Obsah přípravy", content, key=file)
            if st.button(f"Načíst {file}", key=f"load_{file}"):
                st.session_state.final_prompt = content
                st.success("Příprava načtena do editoru. Přejděte na stránku 'Vygenerování písemné přípravy a export'.")

# Stránka Výběr škol a kategorií
def page_school_selection():
    st.title("Výběr škol a kategorií")
    
    # Nahrazeno načítáním z Supabase místo Excelu
    try:
        from utils.database import get_resources
    except ImportError:
        st.error("Modul database.py není dostupný. Zkontrolujte instalaci.")
        get_resources = lambda x: []  # Fallback, pokud modul chybí

    # Funkce pro načtení možností z Supabase
    def load_resource_options(resource_type):
        resources = get_resources(resource_type)
        if resources:
            # Řazení podle hodnoty abecedně
            return sorted([res['value'] for res in resources])
        else:
            st.warning(f"Žádné data pro typ '{resource_type}' nenalezena v databázi.")
            return []  # Vrátí prázdný seznam, pokud data chybí

    school_options = load_resource_options("Misto")  # Pro školy
    category_options = load_resource_options("Kategorie školy")  # Pro kategorie škol
    
    # Výběr škol
    selected_schools = st.multiselect("Vyberte školy:", school_options, 
                                    default=st.session_state.selected_schools if st.session_state.selected_schools else [])
    st.session_state.selected_schools = selected_schools
    
    # Pro každou vybranou školu nastavit kategorii
    st.subheader("Kategorie škol")
    st.write("Experimentální školy mají tělovýchovnou hodinu 5 x týdně")
    st.write("Semi-experimentální školy mají tělovýchovnou hodinu 2 x týdně")
    
    # Vytvoření nebo aktualizace slovníku kategorií škol
    for school in selected_schools:
        if school not in st.session_state.school_category:
            st.session_state.school_category[school] = "Experimentální"  # Výchozí hodnota
        
        category = st.radio(f"Kategorie pro {school}:", category_options, 
                           index=category_options.index(st.session_state.school_category[school]) if st.session_state.school_category[school] in category_options else 0,
                           key=f"category_{school}")
        st.session_state.school_category[school] = category
    
    # Zobrazení přehledu
    if selected_schools:
        st.subheader("Přehled vybraných škol a jejich kategorií")
        for school in selected_schools:
            category = st.session_state.school_category[school]
            frequency = st.session_state.frequency_by_category[category]
            st.write(f"• {school}: {category} ({frequency})")
    else:
        st.warning("Nebyly vybrány žádné školy.")

# Administrátorské přihlášení

def admin_login():
    st.title("Administrátorské přihlášení")
    # Kontrola, zda je nastavené heslo v secrets
    try:
        admin_password = st.secrets["admin"]["password"]
    except Exception:
        admin_password = "admin123"  # Výchozí heslo pro vývoj
        st.warning("Není nastavené administrátorské heslo v secrets. Používá se výchozí heslo.")
    password = st.text_input("Heslo", type="password")
    if st.button("Přihlásit"):
        if password == admin_password:
            st.session_state.admin_logged_in = True
            st.success("Přihlášení úspěšné!")
            st.rerun()
        else:
            st.error("Nesprávné heslo!")
    return st.session_state.get("admin_logged_in", False)

# Administrátorské stránky – Správa podkladů
def page_admin_resources():
    if st.session_state.get("resource_deleted") or st.session_state.get("resource_added"):
        st.session_state.pop("resource_deleted", None)
        st.session_state.pop("resource_added", None)
        st.experimental_rerun()
    st.title("Správa podkladů")
    try:
        from utils.database import get_resources, add_resource, update_resource, delete_resource
    except ImportError:
        st.error("Nepodařilo se načíst modul database.py. Zkontrolujte, zda je soubor správně umístěn v adresáři utils.")
        return
    resource_types = [
        ("Vybavení", "Vybaveni"),
        ("Zdatnost", "Zdatnost"),
        ("Manipulace s předměty", "Manipulace s predmety"),
        ("Lokomoce", "Lokomoce"),
        ("Cíl", "Cil"),
        ("Místo", "Misto"),
        ("Bezpečnost", "Bezpecnost"),
        ("Metody", "Metody"),
        ("Kategorie školy", "Kategorie školy")
    ]
    tabs = st.tabs([label for label, key in resource_types])
    for (label, key), tab in zip(resource_types, tabs):
        with tab:
            st.subheader(label)
            with st.form(f"add_{key}"):
                new_val = st.text_input("Nový podklad:")
                submitted = st.form_submit_button("Přidat")
                if submitted:
                    if add_resource(key, new_val):
                        st.success("Podklad přidán.")
                        st.experimental_rerun()
                    else:
                        st.error("Nepodařilo se přidat podklad.")
            resources = get_resources(key)
            if not resources:
                st.info("Žádné podklady.")
            else:
                for res in resources:
                    with st.expander(res["value"]):
                        # Tlačítko pro smazání podkladu
                        if st.button("Smazat", key=f"delete_{key}_{res['id']}"):
                            if delete_resource(res["id"]):
                                st.session_state["resource_deleted"] = True
                                st.success("Podklad byl smazán.")
                                # rerun provedeme až na začátku funkce
                            else:
                                st.error("Nepodařilo se smazat podklad.")

def page_admin_exercises():
    st.title("Správa cviků")
    
    try:
        from utils.database import get_exercises, delete_exercise, get_exercise_categories
    except ImportError:
        st.error("Nepodařilo se načíst modul database.py. Zkontrolujte, zda je soubor správně umístěn v adresáři utils.")
        return
    
    # Získání cviků z databáze
    exercises = get_exercises()
    
    if not exercises:
        st.info("Zatím nejsou žádné cviky v databázi.")
    else:
        st.write(f"Počet cviků v databázi: {len(exercises)}")
        
        for ex in exercises:
            with st.expander(f"{ex['name']} ({ex['location']})"):
                st.write(f"**Popis:** {ex['description']}")
                st.write(f"**Materiál:** {', '.join(ex['materials'])}")
                
                # Získání kategorií cviku
                categories = get_exercise_categories(ex['id'])
                if categories:
                    st.write("**Kategorie:**")
                    for cat in categories:
                        st.write(f"- {cat['construct_type']}: {cat['subcategory']}")
                
                if st.button(f"Smazat cvik #{ex['id']}", key=f"delete_{ex['id']}"):
                    if delete_exercise(ex['id']):
                        st.success("Cvik byl smazán.")
                        st.rerun()
                    else:
                        st.error("Nepodařilo se smazat cvik.")

def page_admin_ai_exercise():
    st.title("Vytvoření cviku s pomocí AI")
    
    try:
        from utils.ai_integration import generate_exercise_suggestion
        from utils.database import add_exercise, get_construct_types, get_subcategories
    except ImportError:
        st.error("Nepodařilo se načíst potřebné moduly. Zkontrolujte, zda jsou soubory správně umístěny v adresáři utils.")
        return
    
    construct_type = st.selectbox("Typ konstruktu:", get_construct_types())
    subcategory = st.selectbox("Podkategorie:", get_subcategories(construct_type))
    location = st.selectbox("Místo:", ["Tělocvična", "Hřiště", "Obojí"])
    materials_input = st.text_input("Materiál (oddělený čárkami):")
    materials = [m.strip() for m in materials_input.split(",") if m.strip()] if materials_input else []
    
    if st.button("Vygenerovat návrh cviku"):
        with st.spinner("Generuji návrh..."):
            suggestion = generate_exercise_suggestion(
                construct_type, subcategory, location, materials
            )
        
        if suggestion:
            st.success("Návrh byl vygenerován!")
            
            name = st.text_input("Název cviku:", value=suggestion.get("name", ""))
            description = st.text_area("Popis cviku:", value=suggestion.get("description", ""))
            
            if st.button("Uložit cvik"):
                if add_exercise(
                    name, description, location, materials,
                    [{"construct_type": construct_type, "subcategory": subcategory}]
                ):
                    st.success("Cvik byl úspěšně uložen!")
                    st.rerun()
                else:
                    st.error("Nepodařilo se uložit cvik.")
        else:
            st.error("Nepodařilo se vygenerovat návrh cviku. Zkuste to znovu nebo upravte parametry.")

# Hlavní funkce aplikace
def main():
    # Inicializace session state
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    
    # Hlavní menu
    st.sidebar.title("Tělovýchovná jednotka")
    app_mode = st.sidebar.selectbox(
        "Vyberte režim:",
        ["Vytvoření hodiny", "Administrator"]
    )
    
    # Rozdělení podle režimu
    if app_mode == "Vytvoření hodiny":
        # Původní workflow pro vytvoření hodiny
        st.sidebar.title("Navigace")
        pages = {
            "Úvod": page_intro,
            "Výběr škol a kategorií": page_school_selection,
            "Výběr prostředí a vybavení": page_environment_equipment,
            "Nastavení rolí": page_roles,
            "Výběr cvičebních konstruktů": page_exercise_constructs,
            "Časové rozdělení hodiny": page_time_allocation,
            "Generování promptu": page_generate_prompt,
            "Vygenerování písemné přípravy a export": page_generate_plan,
            "Uložené přípravy": page_saved_plans
        }
        choice = st.sidebar.radio("Vyberte stránku:", list(pages.keys()))
        pages[choice]()
    
    elif app_mode == "Administrator":
        # Administrátorská část
        if not admin_login():
            st.info("Pro přístup do administrace se musíte přihlásit.")
            return  # Zabrání vykreslení dalších částí administrace
        else:
            admin_pages = {
                "Správa cviků": page_admin_exercises,
                "Vytvoření cviku s AI": page_admin_ai_exercise,
                "Správa podkladů": page_admin_resources,
            }
            admin_choice = st.sidebar.radio("Administrace:", list(admin_pages.keys()))
            admin_pages[admin_choice]()

if __name__ == '__main__':
    main()
