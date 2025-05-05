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
        url = st.secrets["groq"]["url"]
    except KeyError:
        st.error("Chybí [groq] v secrets.toml.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Ujistíme se, že požadujeme odpověď česky
    if "česky" not in prompt.lower():
        prompt += "\nOdpověz česky."

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.7,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Chyba volání Groq API: {e}")
        return None


# --- Sestavení promptu pro celou lekci ---
def build_lesson_prompt(
    series_meta: Dict[str, Any],
    current_params: Dict[str, Any],
    previous_lessons: List[Dict[str, Any]],
) -> str:
    """
    Sestaví prompt, který vezme historii lekcí,
    všechny parametry a dostupné cviky z current_params.
    """
    return (
        f"Jsi pedagogický asistent pro TV hodiny. Série meta:\n"
        f"{json.dumps(series_meta, ensure_ascii=False, indent=2)}\n\n"
        f"Dosud vedené lekce:\n"
        f"{json.dumps(previous_lessons, ensure_ascii=False, indent=2)}\n\n"
        f"Aktuální parametry:\n"
        f"{json.dumps(current_params, ensure_ascii=False, indent=2)}\n\n"
        "Vygeneruj lekci ve formátu JSON:\n"
        '{\n'
        '  "warmup": [{"name":"...","description":"...","duration_min":5}, …],\n'
        '  "main":   [ … ],\n'
        '  "cooldown":[ … ]\n'
        '}\n'
        "Použij maximálně 70 % času každé části na cviky, zbytek je pauzy/instrukce."
    )


# --- Generování celé lekce přes Groq ---
def generate_lesson_plan_groq(
    series_meta: Dict[str, Any],
    current_params: Dict[str, Any],
    previous_lessons: List[Dict[str, Any]],
) -> Dict[str, Any]:
    prompt = build_lesson_prompt(series_meta, current_params, previous_lessons)
    response_text = get_groq_completion(prompt, model="tv-lesson-planner")
    if not response_text:
        return {}

    # extrahujeme JSON z textu
    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        json_str = response_text[start:end]
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Chyba při parsování JSON z AI odpovědi: {e}")
        return {}
