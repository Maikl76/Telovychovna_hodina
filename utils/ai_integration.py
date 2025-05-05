import streamlit as st
import json
import requests
from typing import Dict, Any, List, Optional

# --- Groq API completion ---
def get_groq_completion(prompt: str, model: str = "llama3-8b-8192") -> Optional[str]:
    """
    Žádost o completion od Groq API, odpověď v češtině.
    """
    try:
        api_key = st.secrets["groq"]["api_key"]
        url     = st.secrets["groq"]["url"]
    except Exception:
        st.error("Chybí [groq] v secrets.toml.")
        return None

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # přidej instrukci česky
    if "česky" not in prompt.lower():
        prompt += "\nOdpověz česky."

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.7
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Chyba volání Groq API: {e}")
        return None

# --- Generování jednoho cviku (existující) ---
def generate_exercise_suggestion(
    construct_type: str,
    subcategory: str,
    location: str,
    materials: List[str] = None
) -> Dict[str, Any]:
    # ... (ponechávám bez změny) ...

# --- Optimalizace existujícího plánu cviků (existující) ---
def optimize_exercise_plan(exercises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # ... (ponechávám bez změny) ...

# --- NOVÉ: Generování celé lekce ---
def build_lesson_prompt(
    series_meta: Dict[str, Any],
    current_params: Dict[str, Any],
    previous_lessons: List[Dict[str, Any]]
) -> str:
    """
    Sestaví prompt, který vezme historii lekcí,
    všechny parametry a dostupné cviky z current_params.
    """
    return f"""
Jsi pedagogický asistent pro TV hodiny. Série meta:
{json.dumps(series_meta, ensure_ascii=False, indent=2)}

Dosud vedené lekce:
{json.dumps(previous_lessons, ensure_ascii=False, indent=2)}

Aktuální parametry:
{json.dumps(current_params, ensure_ascii=False, indent=2)}

Vygeneruj lekci ve formátu JSON:
{{
  "warmup": [{{"name":"...","description":"...","duration_min":5}}, …],
  "main":   [ … ],
  "cooldown":[ … ]
}}
Použij maximálně 70 % času každé části na cviky, zbytek je pauzy/instrukce.
"""

def generate_lesson_plan_groq(
    series_meta: Dict[str, Any],
    current_params: Dict[str, Any],
    previous_lessons: List[Dict[str, Any]]
) -> Dict[str, Any]:
    prompt = build_lesson_prompt(series_meta, current_params, previous_lessons)
    resp = get_groq_completion(prompt, model="tv-lesson-planner")
    if not resp:
        return {}
    # extrakce JSON objektu z textu
    try:
        start = resp.find("{")
        end   = resp.rfind("}") + 1
        js    = resp[start:end]
        return json.loads(js)
    except Exception as e:
        st.error(f"Chyba při parsování lekce z AI: {e}")
        return {}
