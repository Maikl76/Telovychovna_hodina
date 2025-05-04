import streamlit as st
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

# Inicializace Supabase klienta
def _get_supabase_client() -> Client:
    """Získá Supabase klienta z Streamlit secrets."""
    try:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Chyba při inicializaci Supabase klienta: {e}")
        # Fallback na lokální JSON soubor, pokud není Supabase dostupné
        return None

# Fallback na lokální JSON soubor, pokud není Supabase dostupné
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "exercises.json")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

def _load_db() -> Dict[str, Any]:
    """Načte databázi z JSON souboru (fallback)."""
    if not os.path.exists(DB_FILE):
        return {"exercises": [], "categories": []}
    
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Chyba při načítání databáze: {e}")
        return {"exercises": [], "categories": []}

def _save_db(data: Dict[str, Any]) -> bool:
    """Uloží databázi do JSON souboru (fallback)."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Chyba při ukládání databáze: {e}")
        return False

def get_exercises(construct_type: Optional[str] = None, subcategory: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Získá cviky z databáze, volitelně filtrované podle konstruktu a podkategorie.
    
    Args:
        construct_type: Typ konstruktu (Zdatnost, Manipulace s předměty, Lokomoce)
        subcategory: Podkategorie konstruktu
        
    Returns:
        Seznam cviků odpovídajících kritériím
    """
    supabase = _get_supabase_client()
    
    if supabase:
        try:
            # Použití Supabase
            if not construct_type and not subcategory:
                # Získání všech cviků
                response = supabase.table("exercises").select("*").execute()
                return response.data
            else:
                # Získání cviků podle kategorií
                query = supabase.table("exercise_categories").select(
                    "exercise_id"
                )
                
                if construct_type:
                    query = query.eq("construct_type", construct_type)
                
                if subcategory:
                    query = query.eq("subcategory", subcategory)
                
                response = query.execute()
                exercise_ids = [item["exercise_id"] for item in response.data]
                
                if not exercise_ids:
                    return []
                
                # Získání cviků podle ID
                response = supabase.table("exercises").select("*").in_("id", exercise_ids).execute()
                return response.data
        except Exception as e:
            st.error(f"Chyba při komunikaci se Supabase: {e}")
            # Fallback na lokální databázi
    
    # Fallback na lokální JSON soubor
    db = _load_db()
    exercises = db["exercises"]
    
    if not construct_type and not subcategory:
        return exercises
    
    filtered_exercises = []
    for exercise in exercises:
        # Získání kategorií pro tento cvik
        exercise_categories = [
            cat for cat in db["categories"] 
            if cat["exercise_id"] == exercise["id"]
        ]
        
        # Filtrování podle konstruktu a podkategorie
        if construct_type and subcategory:
            if any(cat["construct_type"] == construct_type and cat["subcategory"] == subcategory 
                  for cat in exercise_categories):
                filtered_exercises.append(exercise)
        elif construct_type:
            if any(cat["construct_type"] == construct_type for cat in exercise_categories):
                filtered_exercises.append(exercise)
        elif subcategory:
            if any(cat["subcategory"] == subcategory for cat in exercise_categories):
                filtered_exercises.append(exercise)
    
    return filtered_exercises

def add_exercise(
    name: str, 
    description: str, 
    location: str, 
    materials: List[str],
    construct_types: List[Dict[str, str]]
) -> bool:
    """
    Přidá nový cvik do databáze.
    
    Args:
        name: Název cviku
        description: Popis cviku
        location: Místo (Tělocvična, Hřiště, Obojí)
        materials: Seznam potřebného materiálu
        construct_types: Seznam slovníků s klíči "construct_type" a "subcategory"
        
    Returns:
        True, pokud byl cvik úspěšně přidán, jinak False
    """
    supabase = _get_supabase_client()
    
    if supabase:
        try:
            # Použití Supabase
            # Vytvoření nového cviku
            exercise = {
                "name": name,
                "description": description,
                "location": location,
                "materials": materials,
                "created_by": "admin"
            }
            
            # Přidání cviku do databáze
            response = supabase.table("exercises").insert(exercise).execute()
            
            if not response.data:
                return False
                
            exercise_id = response.data[0]["id"]
            
            # Přidání kategorií
            categories = []
            for ct in construct_types:
                category = {
                    "exercise_id": exercise_id,
                    "construct_type": ct["construct_type"],
                    "subcategory": ct["subcategory"]
                }
                categories.append(category)
            
            if categories:
                supabase.table("exercise_categories").insert(categories).execute()
            
            return True
        except Exception as e:
            st.error(f"Chyba při komunikaci se Supabase: {e}")
            # Fallback na lokální databázi
    
    # Fallback na lokální JSON soubor
    db = _load_db()
    
    # Generování ID
    exercise_id = str(uuid.uuid4())
    
    # Vytvoření nového cviku
    exercise = {
        "id": exercise_id,
        "name": name,
        "description": description,
        "location": location,
        "materials": materials
    }
    
    # Přidání cviku do databáze
    db["exercises"].append(exercise)
    
    # Přidání kategorií
    for ct in construct_types:
        category = {
            "exercise_id": exercise_id,
            "construct_type": ct["construct_type"],
            "subcategory": ct["subcategory"]
        }
        db["categories"].append(category)
    
    # Uložení databáze
    return _save_db(db)

def update_exercise(
    exercise_id: str,
    name: str, 
    description: str, 
    location: str, 
    materials: List[str],
    construct_types: List[Dict[str, str]]
) -> bool:
    """
    Aktualizuje existující cvik v databázi.
    
    Args:
        exercise_id: ID cviku
        name: Název cviku
        description: Popis cviku
        location: Místo (Tělocvična, Hřiště, Obojí)
        materials: Seznam potřebného materiálu
        construct_types: Seznam slovníků s klíči "construct_type" a "subcategory"
        
    Returns:
        True, pokud byl cvik úspěšně aktualizován, jinak False
    """
    supabase = _get_supabase_client()
    
    if supabase:
        try:
            # Použití Supabase
            # Aktualizace cviku
            exercise = {
                "name": name,
                "description": description,
                "location": location,
                "materials": materials,
                "updated_at": "now()"
            }
            
            response = supabase.table("exercises").update(exercise).eq("id", exercise_id).execute()
            
            if not response.data:
                return False
            
            # Odstranění starých kategorií
            supabase.table("exercise_categories").delete().eq("exercise_id", exercise_id).execute()
            
            # Přidání nových kategorií
            categories = []
            for ct in construct_types:
                category = {
                    "exercise_id": exercise_id,
                    "construct_type": ct["construct_type"],
                    "subcategory": ct["subcategory"]
                }
                categories.append(category)
            
            if categories:
                supabase.table("exercise_categories").insert(categories).execute()
            
            return True
        except Exception as e:
            st.error(f"Chyba při komunikaci se Supabase: {e}")
            # Fallback na lokální databázi
    
    # Fallback na lokální JSON soubor
    db = _load_db()
    
    # Nalezení cviku
    for i, exercise in enumerate(db["exercises"]):
        if exercise["id"] == exercise_id:
            # Aktualizace cviku
            db["exercises"][i] = {
                "id": exercise_id,
                "name": name,
                "description": description,
                "location": location,
                "materials": materials
            }
            
            # Odstranění starých kategorií
            db["categories"] = [cat for cat in db["categories"] if cat["exercise_id"] != exercise_id]
            
            # Přidání nových kategorií
            for ct in construct_types:
                category = {
                    "exercise_id": exercise_id,
                    "construct_type": ct["construct_type"],
                    "subcategory": ct["subcategory"]
                }
                db["categories"].append(category)
            
            # Uložení databáze
            return _save_db(db)
    
    return False

def delete_exercise(exercise_id: str) -> bool:
    """
    Odstraní cvik z databáze.
    
    Args:
        exercise_id: ID cviku
        
    Returns:
        True, pokud byl cvik úspěšně odstraněn, jinak False
    """
    supabase = _get_supabase_client()
    
    if supabase:
        try:
            # Použití Supabase
            # Odstranění kategorií
            supabase.table("exercise_categories").delete().eq("exercise_id", exercise_id).execute()
            
            # Odstranění cviku
            response = supabase.table("exercises").delete().eq("id", exercise_id).execute()
            
            return len(response.data) > 0
        except Exception as e:
            st.error(f"Chyba při komunikaci se Supabase: {e}")
            # Fallback na lokální databázi
    
    # Fallback na lokální JSON soubor
    db = _load_db()
    
    # Odstranění cviku
    db["exercises"] = [ex for ex in db["exercises"] if ex["id"] != exercise_id]
    
    # Odstranění kategorií
    db["categories"] = [cat for cat in db["categories"] if cat["exercise_id"] != exercise_id]
    
    # Uložení databáze
    return _save_db(db)

def get_exercise_categories(exercise_id: str) -> List[Dict[str, str]]:
    """
    Získá kategorie pro daný cvik.
    
    Args:
        exercise_id: ID cviku
        
    Returns:
        Seznam kategorií cviku
    """
    supabase = _get_supabase_client()
    
    if supabase:
        try:
            # Použití Supabase
            response = supabase.table("exercise_categories").select("*").eq("exercise_id", exercise_id).execute()
            return response.data
        except Exception as e:
            st.error(f"Chyba při komunikaci se Supabase: {e}")
            # Fallback na lokální databázi
    
    # Fallback na lokální JSON soubor
    db = _load_db()
    return [cat for cat in db["categories"] if cat["exercise_id"] == exercise_id]

def get_construct_types() -> List[str]:
    """
    Získá seznam všech typů konstruktů.
    
    Returns:
        Seznam typů konstruktů
    """
    return ["Zdatnost", "Manipulace s předměty", "Lokomoce"]

def get_subcategories(construct_type: str) -> List[str]:
    """
    Získá seznam podkategorií pro daný typ konstruktu.
    
    Args:
        construct_type: Typ konstruktu
        
    Returns:
        Seznam podkategorií
    """
    if construct_type == "Zdatnost":
        return ["Silová", "Vytrvalostní", "Rychlostní", "Obratnostní", "Pohyblivostní"]
    elif construct_type == "Manipulace s předměty":
        return ["Házení", "Chytání", "Kopání", "Ovládání náčiní"]
    elif construct_type == "Lokomoce":
        return ["Chůze", "Běh", "Skoky", "Lezení", "Plazení"]
    return []
