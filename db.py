"""
Cliente Supabase centralizado para Viral Video DB.
Todos los scripts importan get_db() desde aquí.
"""
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

_client: Client = None


def get_db() -> Client:
    """Retorna el cliente Supabase (singleton)."""
    global _client
    if _client is None:
        if "TU_SUPABASE" in SUPABASE_URL or "TU_SUPABASE" in SUPABASE_KEY:
            raise ValueError(
                "❌ Debes configurar SUPABASE_URL y SUPABASE_KEY en config.py\n"
                "   Obtén tus credenciales en: Supabase Dashboard → Settings → API\n"
                "   Usa la 'service_role' key para acceso completo desde scripts."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
