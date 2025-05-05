import streamlit as st
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

# --- Inicializace Supabase klienta ---
def _get_supabase_client() -> Optional[Client]:
    """Získá Supabase klienta z Streamlit secrets."""
    try:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Chyba při inicializaci Supabase klienta: {e}")
        return None

# --- Lokální fallback na JSON soubor ---
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "db.json")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

def _load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_FILE):
        return {"exercises": [], "categories": [], "series": [], "plans": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Chyba při načítání lokální DB: {e}")
        return {"exercises": [], "categories": [], "series": [], "plans": []}

def _save_db(data: Dict[str, Any]) -> bool:
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Chyba při ukládání lokální DB: {e}")
        return False

# --- CRUD pro cviky ---
def get_exercises(construct_type: Optional[str] = None, subcategory: Optional[str] = None) -> List[Dict[str, Any]]:
    """Načte cviky ze Supabase nebo lokálně, s volnými filtry."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            if not construct_type and not subcategory:
                return supabase.table("exercises").select("*").execute().data
            # nejprve nalezneme ID cviků podle kategorie
            query = supabase.table("exercise_categories").select("exercise_id")
            if construct_type:
                query = query.eq("construct_type", construct_type)
            if subcategory:
                query = query.eq("subcategory", subcategory)
            ids = [r["exercise_id"] for r in query.execute().data]
            if not ids:
                return []
            return supabase.table("exercises").select("*").in_("id", ids).execute().data
        except Exception as e:
            st.error(f"Chyba Supabase při get_exercises: {e}")
    # fallback lokálně
    db = _load_db()
    exs = db["exercises"]
    cats = db["categories"]
    def matches(e):
        rel = [c for c in cats if c["exercise_id"] == e["id"]]
        if construct_type and not any(r["construct_type"] == construct_type for r in rel):
            return False
        if subcategory and not any(r["subcategory"] == subcategory for r in rel):
            return False
        return True
    return [e for e in exs if matches(e)]

def add_exercise(
    name: str,
    description: str,
    location: str,
    materials: List[str],
    construct_types: List[Dict[str, str]]
) -> bool:
    """Přidá cvik do Supabase (nebo lokálně)."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            ex = {"name": name, "description": description, "location": location, "materials": materials}
            resp = supabase.table("exercises").insert(ex).execute()
            ex_id = resp.data[0]["id"]
            cats = [{"exercise_id": ex_id, **ct} for ct in construct_types]
            if cats:
                supabase.table("exercise_categories").insert(cats).execute()
            return True
        except Exception as e:
            st.error(f"Chyba Supabase při add_exercise: {e}")
    # fallback lokálně
    db = _load_db()
    ex_id = str(uuid.uuid4())
    db["exercises"].append({"id": ex_id, "name": name, "description": description, "location": location, "materials": materials})
    for ct in construct_types:
        db["categories"].append({"exercise_id": ex_id, **ct})
    return _save_db(db)

def update_exercise(
    exercise_id: str,
    name: str,
    description: str,
    location: str,
    materials: List[str],
    construct_types: List[Dict[str, str]]
) -> bool:
    """Aktualizuje cvik v Supabase (nebo lokálně)."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("exercises").update({
                "name": name,
                "description": description,
                "location": location,
                "materials": materials,
                "updated_at": "now()"
            }).eq("id", exercise_id).execute()
            supabase.table("exercise_categories").delete().eq("exercise_id", exercise_id).execute()
            cats = [{"exercise_id": exercise_id, **ct} for ct in construct_types]
            if cats:
                supabase.table("exercise_categories").insert(cats).execute()
            return True
        except Exception as e:
            st.error(f"Chyba Supabase při update_exercise: {e}")
    # fallback lokálně
    db = _load_db()
    # update exercise
    for i,e in enumerate(db["exercises"]):
        if e["id"] == exercise_id:
            db["exercises"][i] = {"id": exercise_id, "name": name, "description": description, "location": location, "materials": materials}
    # update categories
    db["categories"] = [c for c in db["categories"] if c["exercise_id"] != exercise_id]
    for ct in construct_types:
        db["categories"].append({"exercise_id": exercise_id, **ct})
    return _save_db(db)

def delete_exercise(exercise_id: str) -> bool:
    """Smaže cvik v Supabase (nebo lokálně)."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("exercise_categories").delete().eq("exercise_id", exercise_id).execute()
            supabase.table("exercises").delete().eq("id", exercise_id).execute()
            return True
        except Exception as e:
            st.error(f"Chyba Supabase při delete_exercise: {e}")
    # fallback lokálně
    db = _load_db()
    db["exercises"] = [e for e in db["exercises"] if e["id"] != exercise_id]
    db["categories"] = [c for c in db["categories"] if c["exercise_id"] != exercise_id]
    return _save_db(db)

def get_exercise_categories(exercise_id: str) -> List[Dict[str, str]]:
    """Načte kategorie pro cvik."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            return supabase.table("exercise_categories").select("*").eq("exercise_id", exercise_id).execute().data
        except Exception as e:
            st.error(f"Chyba Supabase při get_exercise_categories: {e}")
    db = _load_db()
    return [c for c in db["categories"] if c["exercise_id"] == exercise_id]

def get_construct_types() -> List[str]:
    return ["Zdatnost", "Manipulace s předměty", "Lokomoce"]

def get_subcategories(construct_type: str) -> List[str]:
    if construct_type == "Zdatnost":
        return ["Silová", "Vytrvalostní", "Rychlostní", "Obratnostní", "Pohyblivostní"]
    if construct_type == "Manipulace s předměty":
        return ["Házení", "Chytání", "Kopání", "Ovládání náčiní"]
    if construct_type == "Lokomoce":
        return ["Chůze", "Běh", "Skoky", "Lezení", "Plazení"]
    return []

# --- CRUD pro podklady (resources) ---
def get_resources(resource_type: str) -> List[Dict[str, str]]:
    supabase = _get_supabase_client()
    if supabase:
        try:
            return supabase.table("resources").select("*").eq("resource_type", resource_type).execute().data
        except Exception as e:
            st.error(f"Chyba Supabase při get_resources: {e}")
    return []

def add_resource(resource_type: str, value: str) -> bool:
    if not value.strip():
        st.error("Hodnota nesmí být prázdná.")
        return False
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("resources").insert({"resource_type": resource_type, "value": value}).execute()
            return True
        except Exception as e:
            st.error(f"Chyba Supabase při add_resource: {e}")
    else:
        st.error("Supabase klient není dostupný.")
    return False

def update_resource(resource_id: str, value: str) -> bool:
    if not value.strip():
        st.error("Hodnota nesmí být prázdná.")
        return False
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("resources").update({"value": value}).eq("id", resource_id).execute()
            return True
        except Exception as e:
            st.error(f"Chyba Supabase při update_resource: {e}")
    else:
        st.error("Supabase klient není dostupný.")
    return False

def delete_resource(resource_id: str) -> bool:
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("resources").delete().eq("id", resource_id).execute()
            return True
        except Exception as e:
            st.error(f"Chyba Supabase při delete_resource: {e}")
    else:
        st.error("Supabase klient není dostupný.")
    return False

# --- CRUD pro série lekcí a jednotlivé lekce ---
def get_series_for_teacher(teacher_id: str) -> List[Dict[str, Any]]:
    supabase = _get_supabase_client()
    if supabase:
        return supabase.table("lesson_series").select("*").eq("teacher_id", teacher_id).order("created_at", desc=True).execute().data
    st.error("Supabase klient není dostupný.")
    return []

def create_series(
    teacher_id: str,
    school_id: str,
    class_name: str,
    subject: str,
    school_year: str
) -> Optional[Dict[str, Any]]:
    supabase = _get_supabase_client()
    if supabase:
        res = supabase.table("lesson_series").insert({
            "teacher_id": teacher_id,
            "school_id": school_id,
            "class_name": class_name,
            "subject": subject,
            "school_year": school_year
        }).execute().data
        return res[0] if res else None
    st.error("Supabase klient není dostupný.")
    return None

def get_last_lessons(series_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    supabase = _get_supabase_client()
    if supabase:
        data = supabase.table("lesson_plan").select("*") \
            .eq("series_id", series_id) \
            .order("sequence_index", desc=True) \
            .limit(limit).execute().data
        # vrátíme list content JSON zpět v chronologickém pořadí
        return [item["content"] for item in reversed(data)]
    st.error("Supabase klient není dostupný.")
    return []

def get_next_sequence_index(series_id: str) -> int:
    supabase = _get_supabase_client()
    if supabase:
        row = supabase.table("lesson_plan").select("sequence_index") \
            .eq("series_id", series_id).order("sequence_index", desc=True) \
            .limit(1).execute().data
        return (row[0]["sequence_index"] + 1) if row else 1
    st.error("Supabase klient není dostupný.")
    return 1

def add_lesson_plan(
    series_id: str,
    sequence_index: int,
    params: Dict[str, Any],
    content: Dict[str, Any],
    date: str
) -> bool:
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("lesson_plan").insert({
                "series_id": series_id,
                "sequence_index": sequence_index,
                "date": date,
                "params": params,
                "content": content
            }).execute()
            return True
        except Exception as e:
            st.error(f"Chyba při ukládání lekce: {e}")
            return False
    st.error("Supabase klient není dostupný.")
    return False
