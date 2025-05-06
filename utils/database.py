# utils/database.py
import streamlit as st
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from postgrest import APIError

# --- Inicializace Supabase klienta ---

def _get_supabase_client() -> Optional[Client]:
    """
    Vrátí Supabase client nebo None, pokud inicializace selže.
    """
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Chyba při inicializaci Supabase klienta: {e}")
        return None

# --- Lokální fallback do JSON souboru ---
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "db.json")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)


def _load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_FILE):
        return {"exercises": [], "categories": [], "series": [], "plans": [], "resources": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Chyba při načítání lokální DB: {e}")
        return {"exercises": [], "categories": [], "series": [], "plans": [], "resources": []}


def _save_db(data: Dict[str, Any]) -> bool:
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Chyba při ukládání lokální DB: {e}")
        return False

# --- CRUD pro cviky ---

def get_exercises(construct_type: Optional[str] = None,
                  subcategory: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Načte cviky podle filtru z Supabase nebo fallback lokálně.
    """
    supabase = _get_supabase_client()
    if supabase:
        try:
            query = supabase.table("exercises").select("*")
            if construct_type or subcategory:
                # spojení s kategoriemi
                cats = supabase.table("exercise_categories").select("exercise_id,construct_type,subcategory")
                if construct_type:
                    cats = cats.eq("construct_type", construct_type)
                if subcategory:
                    cats = cats.eq("subcategory", subcategory)
                ids = [c["exercise_id"] for c in cats.execute().data]
                if not ids:
                    return []
                query = query.in_("id", ids)
            return query.order("name").execute().data
        except APIError as e:
            st.error(f"Chyba Supabase při get_exercises: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při get_exercises: {e}")
    # fallback
    db = _load_db()
    exs = db.get("exercises", [])
    cats = db.get("categories", [])
    def match(e):
        rel = [c for c in cats if c["exercise_id"] == e["id"]]
        if construct_type and not any(r["construct_type"] == construct_type for r in rel):
            return False
        if subcategory and not any(r["subcategory"] == subcategory for r in rel):
            return False
        return True
    return [e for e in exs if match(e)]


def add_exercise(name: str,
                 description: str,
                 location: str,
                 materials: List[str],
                 construct_types: List[Dict[str, str]]) -> bool:
    """
    Přidá cvik do Supabase nebo fallback lokálně.
    construct_types = [{"construct_type":..., "subcategory":...}, ...]
    """
    supabase = _get_supabase_client()
    if supabase:
        try:
            ex = {"name": name, "description": description, "location": location, "materials": materials}
            res = supabase.table("exercises").insert(ex).execute()
            ex_id = res.data[0]["id"]
            cat_rows = [{"exercise_id": ex_id, **ct} for ct in construct_types]
            if cat_rows:
                supabase.table("exercise_categories").insert(cat_rows).execute()
            return True
        except APIError as e:
            st.error(f"Chyba Supabase při add_exercise: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při add_exercise: {e}")
    # fallback
    db = _load_db()
    ex_id = str(uuid.uuid4())
    db["exercises"].append({
        "id": ex_id,
        "name": name,
        "description": description,
        "location": location,
        "materials": materials
    })
    for ct in construct_types:
        db["categories"].append({"exercise_id": ex_id, **ct})
    return _save_db(db)


def delete_exercise(ex_id: str) -> bool:
    """Smaže cvik v Supabase nebo fallback lokálně."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("exercise_categories").delete().eq("exercise_id", ex_id).execute()
            supabase.table("exercises").delete().eq("id", ex_id).execute()
            return True
        except APIError as e:
            st.error(f"Chyba Supabase při delete_exercise: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při delete_exercise: {e}")
    # fallback
    db = _load_db()
    db["exercises"] = [e for e in db["exercises"] if e["id"] != ex_id]
    db["categories"] = [c for c in db["categories"] if c["exercise_id"] != ex_id]
    return _save_db(db)


def get_exercise_categories(ex_id: str) -> List[Dict[str, str]]:
    """Načte kategorie cviku ze Supabase nebo fallback."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            return supabase.table("exercise_categories").select("*").eq("exercise_id", ex_id).execute().data
        except APIError as e:
            st.error(f"Chyba Supabase při get_exercise_categories: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při get_exercise_categories: {e}")
    db = _load_db()
    return [c for c in db.get("categories", []) if c["exercise_id"] == ex_id]

# --- CRUD pro resources ---

def get_resources(resource_type: str) -> List[Dict[str, Any]]:
    supabase = _get_supabase_client()
    if supabase:
        try:
            return supabase.table("resources").select("*").eq("resource_type", resource_type).order("value").execute().data
        except APIError as e:
            st.error(f"Chyba Supabase při get_resources: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při get_resources: {e}")
    db = _load_db()
    return [r for r in db.get("resources", []) if r.get("resource_type") == resource_type]


def add_resource(resource_type: str, value: str) -> bool:
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("resources").insert({"resource_type": resource_type, "value": value}).execute()
            return True
        except APIError as e:
            st.error(f"Chyba Supabase při add_resource: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při add_resource: {e}")
    db = _load_db()
    db.setdefault("resources", []).append({"id": str(uuid.uuid4()), "resource_type": resource_type, "value": value})
    return _save_db(db)


def delete_resource(res_id: str) -> bool:
    supabase = _get_supabase_client()
    if supabase:
        try:
            supabase.table("resources").delete().eq("id", res_id).execute()
            return True
        except APIError as e:
            st.error(f"Chyba Supabase při delete_resource: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při delete_resource: {e}")
    db = _load_db()
    db["resources"] = [r for r in db.get("resources", []) if r["id"] != res_id]
    return _save_db(db)

# --- CRUD pro série a lekce ---

def get_series_for_teacher(teacher_id: str) -> List[Dict[str, Any]]:
    """
    Načte všechny série lekcí pro daného učitele.
    V případě chyby vrátí prázdný seznam.
    """
    supabase = _get_supabase_client()
    if supabase:
        try:
            resp = (
                supabase.table("lesson_series")
                         .select("*")
                         .eq("teacher_id", teacher_id)
                         .order("created_at", desc=True)
                         .execute()
            )
            return resp.data
        except APIError as e:
            st.error(f"Chyba Supabase při get_series_for_teacher: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při get_series_for_teacher: {e}")
    # fallback
    db = _load_db()
    return [s for s in db.get("series", []) if s.get("teacher_id") == teacher_id]


def create_series(teacher_id: str,
                  school_id: str,
                  class_name: str,
                  subject: str,
                  school_year: str) -> Dict[str, Any]:
    """Vytvoří novou sérii řádek v Supabase nebo fallback lokálně."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            res = supabase.table("lesson_series").insert({
                "teacher_id": teacher_id,
                "school_id": school_id,
                "class_name": class_name,
                "subject": subject,
                "school_year": school_year
            }).execute()
            return res.data[0]
        except APIError as e:
            st.error(f"Chyba Supabase při create_series: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při create_series: {e}")
    # fallback
    db = _load_db()
    series_id = str(uuid.uuid4())
    entry = {
        "id": series_id,
        "teacher_id": teacher_id,
        "school_id": school_id,
        "class_name": class_name,
        "subject": subject,
        "school_year": school_year
    }
    db.setdefault("series", []).append(entry)
    _save_db(db)
    return entry


def get_last_lessons(series_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Načte poslední lekce z Supabase nebo fallback.
    """
    supabase = _get_supabase_client()
    if supabase:
        try:
            data = supabase.table("lesson_plan").select("*")
            data = data.eq("series_id", series_id)
            data = data.order("sequence_index", desc=True).limit(limit)
            res = data.execute().data
            # vrátíme obsah ve správném pořadí
            return [r["content"] for r in reversed(res)]
        except APIError as e:
            st.error(f"Chyba Supabase při get_last_lessons: {e}")
        except Exception as e:
            st.error(f"Neočekávaná chyba při get_last_lessons: {e}")
    # fallback
    db = _load_db()
    plans = [p for p in db.get("plans", []) if p.get("series_id") == series_id]
    plans = sorted(plans, key=lambda p: p.get("sequence_index", 0), reverse=True)[:limit]
    return [p.get("content") for p in reversed(plans)]


def get_next_sequence_index(series_id: str) -> int:
    """Vrátí další index pro sekvenci lekcí."""
    supabase = _get_supabase_client()
    if supabase:
        try:
            row = (
                supabase.table("lesson_plan").select("sequence_index")
                         .eq("series_id", series_id)
                         .order("sequence_index", desc=True)
                         .limit(1)
                         .execute().data
            )
            return (row[0]["sequence_index"] + 1) if row else 1
        except APIError:
            return 1
        except Exception:
            return 1
    # fallback
    db = _load_db()
    plans = [p for p in db.get("plans", []) if p.get("series_id") == series_id]
    if not plans:
        return 1
    return max(p.get("sequence_index", 0) for p in plans) + 1


def add_lesson_plan(series_id: str,
                    sequence_index: int,
                    params: Dict[str, Any],
                    content: Dict[str, Any],
                    date: str) -> bool:
    """Přidá lekci do Supabase nebo fallback lokálně."""
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
        except APIError as e:
            st.error(f"
