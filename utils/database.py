import streamlit as st
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

# Inicializace Supabase klienta
def _get_supabase_client() -> Optional[Client]:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Chyba při inicializaci Supabase klienta: {e}")
        return None

# Fallback na lokální JSON soubor, pokud Supabase není dostupné
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "exercises.json")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

def _load_db() -> Dict[str, Any]:
    """Načte databázi z JSON souboru (fallback)."""
    if not os.path.exists(DB_FILE):
        return {"exercises": [], "categories": [], "sections": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Zajistí, že klíče existují
        data.setdefault("exercises", [])
        data.setdefault("categories", [])
        data.setdefault("sections", [])
        return data
    except Exception as e:
        st.error(f"Chyba při načítání lokální databáze: {e}")
        return {"exercises": [], "categories": [], "sections": []}

def _save_db(data: Dict[str, Any]) -> bool:
    """Uloží databázi do JSON souboru (fallback)."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Chyba při ukládání lokální databáze: {e}")
        return False

# CRUD cviků + sekcí

def get_exercises(
    construct_type: Optional[str] = None,
    subcategory: Optional[str] = None,
    section: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Získá cviky z databáze, volitelně filtrované podle:
    - construct_type
    - subcategory
    - section ('prep', 'main', 'final')
    """
    supabase = _get_supabase_client()
    if supabase:
        # Nejprve sestavíme base query
        query = supabase.table("exercises").select("*")
        if construct_type:
            query = query.eq("construct_type", construct_type)
        if subcategory:
            query = query.eq("subcategory", subcategory)
        # Filtrovat podle sekce: získat nejprve ID cviků z exercise_sections
        if section:
            resp = supabase.table("exercise_sections") \
                           .select("exercise_id") \
                           .eq("section_tag", section) \
                           .execute()
            ids = [r["exercise_id"] for r in resp.data]
            if not ids:
                return []
            query = query.in_("id", ids)
        resp = query.execute()
        return resp.data

    # Fallback na lokální JSON
    db = _load_db()
    exercises = db["exercises"]
    # Filtrace podle construct_type & subcategory
    if construct_type:
        exercises = [e for e in exercises if e.get("construct_type")==construct_type]
    if subcategory:
        exercises = [e for e in exercises if e.get("subcategory")==subcategory]
    # Filtrace podle sekce
    if section:
        sec = [s["exercise_id"] for s in db["sections"] if s["section_tag"]==section]
        exercises = [e for e in exercises if e["id"] in sec]
    return exercises

def add_exercise(
    name: str,
    description: str,
    location: str,
    materials: List[str],
    construct_types: List[Dict[str, str]],
    section_tags: List[str]
) -> bool:
    """
    Přidá nový cvik a jeho kategorie + sekce.
    """
    supabase = _get_supabase_client()
    if supabase:
        # Vložíme základní cvik
        ex = {
            "name": name,
            "description": description,
            "location": location,
            "materials": materials,
            "created_by": st.session_state.get("user", "admin")
        }
        resp = supabase.table("exercises").insert(ex).execute()
        if not resp.data:
            return False
        exercise_id = resp.data[0]["id"]
        # Kategorie
        cats = []
        for ct in construct_types:
            cats.append({
                "exercise_id": exercise_id,
                "construct_type": ct["construct_type"],
                "subcategory": ct["subcategory"]
            })
        if cats:
            supabase.table("exercise_categories").insert(cats).execute()
        # Sekce
        secs = []
        for tag in section_tags:
            secs.append({
                "exercise_id": exercise_id,
                "section_tag": tag
            })
        if secs:
            supabase.table("exercise_sections").insert(secs).execute()
        return True

    # Fallback JSON
    db = _load_db()
    exercise_id = str(uuid.uuid4())
    db["exercises"].append({
        "id": exercise_id,
        "name": name,
        "description": description,
        "location": location,
        "materials": materials
    })
    for ct in construct_types:
        db["categories"].append({
            "exercise_id": exercise_id,
            "construct_type": ct["construct_type"],
            "subcategory": ct["subcategory"]
        })
    for tag in section_tags:
        db["sections"].append({
            "exercise_id": exercise_id,
            "section_tag": tag
        })
    return _save_db(db)

def update_exercise(
    exercise_id: str,
    name: str,
    description: str,
    location: str,
    materials: List[str],
    construct_types: List[Dict[str, str]],
    section_tags: List[str]
) -> bool:
    """
    Aktualizuje existující cvik + kategorie + sekce.
    """
    supabase = _get_supabase_client()
    if supabase:
        # Aktualizace základních polí
        ex = {
            "name": name,
            "description": description,
            "location": location,
            "materials": materials,
            "updated_at": "now()"
        }
        resp = supabase.table("exercises") \
                       .update(ex) \
                       .eq("id", exercise_id) \
                       .execute()
        if not resp.data:
            return False
        # Kategorie: nejprve smazat
        supabase.table("exercise_categories").delete().eq("exercise_id", exercise_id).execute()
        # a vložit nové
        cats = [{"exercise_id": exercise_id, **ct} for ct in construct_types]
        if cats:
            supabase.table("exercise_categories").insert(cats).execute()
        # Sekce: analogicky
        supabase.table("exercise_sections").delete().eq("exercise_id", exercise_id).execute()
        secs = [{"exercise_id": exercise_id, "section_tag": tag} for tag in section_tags]
        if secs:
            supabase.table("exercise_sections").insert(secs).execute()
        return True

    # Fallback JSON
    db = _load_db()
    # Najdi index cviku
    for i, ex in enumerate(db["exercises"]):
        if ex["id"] == exercise_id:
            db["exercises"][i] = {
                "id": exercise_id,
                "name": name,
                "description": description,
                "location": location,
                "materials": materials
            }
            break
    # Kategorie
    db["categories"] = [c for c in db["categories"] if c["exercise_id"] != exercise_id]
    for ct in construct_types:
        db["categories"].append({
            "exercise_id": exercise_id,
            **ct
        })
    # Sekce
    db["sections"] = [s for s in db["sections"] if s["exercise_id"] != exercise_id]
    for tag in section_tags:
        db["sections"].append({
            "exercise_id": exercise_id,
            "section_tag": tag
        })
    return _save_db(db)

def delete_exercise(exercise_id: str) -> bool:
    """
    Odstraní cvik (i kategorie a sekce díky ON DELETE CASCADE).
    """
    supabase = _get_supabase_client()
    if supabase:
        # Supabase cascade smaže i exercise_sections a exercise_categories
        resp = supabase.table("exercises").delete().eq("id", exercise_id).execute()
        return len(resp.data) > 0

    # Fallback JSON
    db = _load_db()
    db["exercises"]  = [e for e in db["exercises"]  if e["id"] != exercise_id]
    db["categories"] = [c for c in db["categories"] if c["exercise_id"] != exercise_id]
    db["sections"]   = [s for s in db["sections"]   if s["exercise_id"] != exercise_id]
    return _save_db(db)

def get_exercise_sections(exercise_id: str) -> List[str]:
    """
    Získá seznam sekcí (prep/main/final) pro daný cvik.
    """
    supabase = _get_supabase_client()
    if supabase:
        resp = supabase.table("exercise_sections") \
                       .select("section_tag") \
                       .eq("exercise_id", exercise_id) \
                       .execute()
        return [r["section_tag"] for r in resp.data]

    # Fallback JSON
    db = _load_db()
    return [s["section_tag"] for s in db["sections"] if s["exercise_id"] == exercise_id]

def get_construct_types() -> List[str]:
    return ["Zdatnost", "Manipulace s předměty", "Lokomoce"]

def get_subcategories(construct_type: str) -> List[str]:
    if construct_type == "Zdatnost":
        return ["Silová", "Vytrvalostní", "Rychlostní", "Obratnostní", "Pohyblivostní"]
    elif construct_type == "Manipulace s předměty":
        return ["Házení", "Chytání", "Kopání", "Ovládání náčiní"]
    elif construct_type == "Lokomoce":
        return ["Chůze", "Běh", "Skoky", "Lezení", "Plazení"]
    return []

def get_resources(resource_type: str) -> List[Dict[str, str]]:
    """
    Získá seznam podkladů z tabulky resources podle typu.
    """
    supabase = _get_supabase_client()
    if supabase:
        resp = supabase.table("resources") \
                       .select("*") \
                       .eq("resource_type", resource_type) \
                       .execute()
        return resp.data
    return []

def add_resource(resource_type: str, value: str) -> bool:
    """
    Přidá nový podklad do tabulky resources.
    """
    if not value:
        st.error("Hodnota podkladu nesmí být prázdná.")
        return False
    supabase = _get_supabase_client()
    if supabase:
        supabase.table("resources").insert({"resource_type": resource_type, "value": value}).execute()
        return True
    st.error("Supabase klient není dostupný.")
    return False

def update_resource(resource_id: str, value: str) -> bool:
    """
    Aktualizuje existující podklad podle ID.
    """
    if not value:
        st.error("Hodnota podkladu nesmí být prázdná.")
        return False
    supabase = _get_supabase_client()
    if supabase:
        supabase.table("resources").update({"value": value}).eq("id", resource_id).execute()
        return True
    st.error("Supabase klient není dostupný.")
    return False

def delete_resource(resource_id: str) -> bool:
    """
    Odstraní podklad podle ID.
    """
    supabase = _get_supabase_client()
    if supabase:
        supabase.table("resources").delete().eq("id", resource_id).execute()
        return True
    st.error("Supabase klient není dostupný.")
    return False
