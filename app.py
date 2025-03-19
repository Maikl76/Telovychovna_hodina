import streamlit as st
import os
import base64
import io
import time
from datetime import datetime
import pandas as pd

# Stránka Úvod
def page_intro():
    st.title("Úvod")
    st.write("Tato aplikace pomáhá vytvořit prompt pro custom GPT model a následně generovat písemnou přípravu na školní tělovýchovnou hodinu.")
    # Fixně nastavíme 3. třídu
    st.session_state.class_grade = "3. třída"
    st.write("Vybraná třída: 3. třída")

# Stránka Výběr prostředí a vybavení
def page_environment_equipment():
    st.title("Výběr prostředí a vybavení")
    env = st.selectbox("Vyberte, kde se hodina bude konat:", ["Tělocvična", "Venkovní"])
    st.session_state.environment = env
    st.write("Vybrané prostředí:", env)
    
    st.write("Vyberte dostupné vybavení:")
    # Načtení vybavení z Excel souboru "Podklady.xlsx" ze sloupce "Vybaveni"
    try:
        podklady = pd.read_excel("Podklady.xlsx", engine='openpyxl')
        equipment_options = sorted(podklady["Vybaveni"].dropna().unique())
    except Exception as e:
        st.error("Nepodařilo se načíst vybavení z excel souboru Podklady.xlsx.")
        equipment_options = ["Míče", "Kužely", "Švihadla"]  # záložní možnosti
    
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
    
    st.write("**Zdatnost:**")
    fitness_options = ["Silové schopnosti", "Vytrvalostní schopnosti", "Agilita"]
    fitness_selected = st.multiselect("Zdatnost:", fitness_options, default=fitness_options)
    st.session_state.fitness = fitness_selected
    
    st.write("**Manipulace s předměty:**")
    manipulation_options = ["Koordinační schopnosti", "Reakční schopnosti", "Rovnovážné schopnosti", "Orientace v prostoru"]
    manipulation_selected = st.multiselect("Manipulace s předměty:", manipulation_options, default=manipulation_options)
    st.session_state.manipulation = manipulation_selected
    
    st.write("**Lokomoce:**")
    locomotion_options = ["Běh", "Skákání", "Chůze"]
    locomotion_selected = st.multiselect("Lokomoce:", locomotion_options, default=["Běh", "Skákání"])
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
    
    if 'class_grade' not in st.session_state:
        st.error("Nejprve vyplňte předchozí kroky.")
        return
    
    equipment_text = ", ".join(st.session_state.equipment)
    # Dynamicky vytvoříme řetězec vybraných kategorií – spojíme volby z "Zdatnost", "Manipulace s předměty" a "Lokomoce"
    selected_categories = ", ".join(st.session_state.fitness + st.session_state.manipulation + st.session_state.locomotion)
    
    prompt = f"""Navrhni školní tělovýchovnou hodinu pro {st.session_state.class_grade} základní školy, trvající 45 minut, rozdělenou na:
1. Přípravnou část (vede {st.session_state.preparatory_leader}) – zaměřenou na zahřívací, mobilizační a koordinační cviky. Použij databázi cviků pro přípravnou část.
2. Hlavní část (vede {st.session_state.main_leader}) – obsahující cvičení podporující: {selected_categories}.
   Pro každou z těchto kategorií vyber konkrétní cviky z databáze, které odpovídají věkovým specifikům žáků.
3. Závěrečnou část (vede {st.session_state.final_leader}) – zakončenou společným cvičením zaměřeným na statický strečink, relaxaci a mentální uklidnění. Použij databázi cviků pro závěrečnou část.

Výuka se bude konat v prostředí: {st.session_state.environment} s vybavením: {equipment_text}.
Časové rozdělení: Přípravná část: {st.session_state.preparatory_time} minut, Hlavní část: {st.session_state.main_time} minut, Závěrečná část: {st.session_state.final_time} minut.

Vedle detailního návrhu jednotlivých částí vytvoř také sekci "Stručný obsah", která shrnuje, jaké cviky a metody byly použity.
"""
    st.text_area("Vygenerovaný prompt:", prompt, height=300)
    
    b64 = base64.b64encode(prompt.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="prompt.txt">Stáhnout prompt</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.write("Zkopírujte prompt do vašeho custom GPT modelu a vygenerujte návrh hodiny. Poté zkopírujte výstup do stránky 'Vygenerování písemné přípravy a export'.")

# Stránka Vygenerování písemné přípravy a export (PDF) s rozšířenými poli
def page_generate_plan():
    st.title("Vygenerování písemné přípravy a export")
    
    # Načtení excel souboru Podklady.xlsx s možnostmi pro rozevírací nabídky
    try:
        podklady = pd.read_excel("Podklady.xlsx", engine='openpyxl')
        goal_options = sorted(podklady["Cil"].dropna().unique())
        place_options = sorted(podklady["Misto"].dropna().unique())
        safety_options = sorted(podklady["Bezpecnost"].dropna().unique())
        method_options = sorted(podklady["Metody"].dropna().unique())
    except Exception as e:
        st.error("Nepodařilo se načíst soubor Podklady.xlsx. Ujistěte se, že soubor existuje a je ve správném formátu.")
        goal_options = []
        place_options = []
        safety_options = []
        method_options = []
    
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
    
    # Rozevírací nabídka pro Bezpečnost (původně Bezpečnostní vybavení)
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
                st.error("Není nainstalován modul fpdf. Nainstalujte jej pomocí 'pip install fpdf'.")
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                for line in full_plan.split('\n'):
                    pdf.multi_cell(0, 10, line)
                pdf_output = pdf.output(dest="S").encode("latin1")
                b64_pdf = base64.b64encode(pdf_output).decode()
                pdf_href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="priprava.pdf">Stáhnout PDF</a>'
                st.markdown(pdf_href, unsafe_allow_html=True)
    with col2:
        if st.button("Exportovat jako Word"):
            try:
                from docx import Document
            except ImportError:
                st.error("Není nainstalován modul python-docx. Nainstalujte jej pomocí 'pip install python-docx'.")
            else:
                document = Document()
                for line in full_plan.split('\n'):
                    document.add_paragraph(line)
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

# Hlavní funkce aplikace
def main():
    st.sidebar.title("Navigace")
    pages = {
        "Úvod": page_intro,
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

if __name__ == '__main__':
    main()
