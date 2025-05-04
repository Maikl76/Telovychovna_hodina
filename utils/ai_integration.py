import streamlit as st
import requests
import json
import os
from typing import Dict, Any, List, Optional

def get_groq_completion(prompt: str, model: str = "llama-3.1-8b-instant") -> Optional[str]:
    """
    Získá odpověď z Groq API.
    
    Args:
        prompt: Textový prompt pro AI model
        model: Název modelu k použití
        
    Returns:
        Odpověď z AI modelu nebo None v případě chyby
    """
    # Pokud jsme v testovacím režimu, vrátíme ukázkovou odpověď
    if os.environ.get("STREAMLIT_TEST_MODE") == "true":
        return "Toto je ukázková odpověď z AI modelu."
    
    # Získání API klíče
    try:
        api_key = st.secrets["groq"]["api_key"]
    except Exception:
        st.error("Chybí API klíč pro Groq. Nastavte jej v .streamlit/secrets.toml nebo v Streamlit Cloud.")
        return None
    
    # API endpoint (corrected path)
    api_url = "https://api.groq.com/v1/openai/chat/completions"
    
    # Hlavičky požadavku
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Data požadavku
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        # Odeslání požadavku
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()  # Vyvolá výjimku, pokud status kód není 2xx
        
        # Zpracování odpovědi
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Chyba při komunikaci s Groq API: {e}")
        return None

def generate_exercise_suggestion(
    construct_type: str, 
    subcategory: str, 
    location: str, 
    materials: List[str] = None
) -> Dict[str, Any]:
    """
    Vygeneruje návrh cviku pomocí AI.
    
    Args:
        construct_type: Typ konstruktu (Zdatnost, Manipulace s předměty, Lokomoce)
        subcategory: Podkategorie konstruktu
        location: Místo (Tělocvična, Hřiště, Obojí)
        materials: Seznam dostupného materiálu
        
    Returns:
        Slovník s návrhem cviku nebo prázdný slovník v případě chyby
    """
    # Sestavení promptu
    materials_text = ", ".join(materials) if materials else "žádné"
    
    prompt = f"""
    Navrhni cvik pro školní tělovýchovnou hodinu s následujícími parametry:
    - Cvičební konstrukt: {construct_type}
    - Podkategorie: {subcategory}
    - Místo: {location}
    - Dostupné materiály: {materials_text}
    
    Odpověz ve formátu JSON s následujícími klíči:
    - name: Název cviku (krátký a výstižný)
    - description: Detailní popis cviku včetně provedení
    - time: Doporučený čas v minutách (pouze číslo)
    
    Příklad odpovědi:
    {{
        "name": "Člunkový běh",
        "description": "Rozmístěte kužely do řady s rozestupy 5 metrů. Žáci startují od prvního kuželu, běží k druhému, dotknou se ho, vrátí se k prvnímu, dotknou se ho, běží ke třetímu atd.",
        "time": 5
    }}
    """
    
    # Získání odpovědi z AI
    response = get_groq_completion(prompt)
    if not response:
        return {}
    
    # Zpracování odpovědi
    try:
        # Extrakce JSON z odpovědi (může být obklopena dalším textem)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            exercise = json.loads(json_str)
            return exercise
        else:
            st.warning("Nepodařilo se extrahovat JSON z odpovědi AI.")
            return {}
    except Exception as e:
        st.error(f"Chyba při zpracování odpovědi AI: {e}")
        return {}

def optimize_exercise_plan(exercises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Optimalizuje plán cvičení pomocí AI.
    
    Args:
        exercises: Seznam cviků
        
    Returns:
        Optimalizovaný seznam cviků
    """
    # Sestavení promptu
    exercises_json = json.dumps(exercises, ensure_ascii=False)
    
    prompt = f"""
    Optimalizuj následující plán cvičení pro školní tělovýchovnou hodinu:
    {exercises_json}
    
    Seřaď cviky v logickém pořadí, uprav časovou dotaci tak, aby součet nepřesáhl 70% celkového času hodiny, a případně navrhni úpravy cviků.
    
    Odpověz ve formátu JSON jako seznam cviků se stejnou strukturou jako vstup.
    """
    
    # Získání odpovědi z AI
    response = get_groq_completion(prompt)
    if not response:
        return exercises
    
    # Zpracování odpovědi
    try:
        # Extrakce JSON z odpovědi
        json_start = response.find("[")
        json_end = response.rfind("]") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            optimized_exercises = json.loads(json_str)
            return optimized_exercises
        else:
            st.warning("Nepodařilo se extrahovat JSON z odpovědi AI.")
            return exercises
    except Exception as e:
        st.error(f"Chyba při zpracování odpovědi AI: {e}")
        return exercises
