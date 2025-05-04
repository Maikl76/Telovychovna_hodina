import streamlit as st
import json
from typing import Dict, Any, List, Optional
from transformers import LlamaTokenizer, LlamaForCausalLM
import torch

@st.cache_resource
def load_llama_model(model_id: str = "meta-llama/Llama-3-8b-instant-128k"):
    """Načte a vrátí tokenizer a model Llama 3.1 8B Instant 128k."""
    tokenizer = LlamaTokenizer.from_pretrained(model_id)
    model = LlamaForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        max_seq_len=131072
    )
    return tokenizer, model

def get_groq_completion(prompt: str, model: str = "meta-llama/Llama-3-8b-instant-128k") -> Optional[str]:
    """
    Získá odpověď z lokálního Llama 3.1 8B Instant 128k modelu.
    """
    # Lokální inference Llama modelu
    tokenizer, llm = load_llama_model(model)
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(llm.device) for k, v in inputs.items()}
    outputs = llm.generate(
        **inputs,
        max_new_tokens=1024,
        temperature=0.7,
        do_sample=False
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

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
