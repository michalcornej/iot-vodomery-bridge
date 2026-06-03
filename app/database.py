import psycopg2
import logging
from contextlib import contextmanager
from app.config import settings

logger = logging.getLogger(__name__)

@contextmanager
def get_db_cursor():
    """Context manager pro bezpečnou práci s PostgreSQL kurzorem."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        cur = conn.cursor()
        yield cur
        conn.commit()  # Pokud vše proběhne v pořádku, potvrdíme transakci
    except Exception as e:
        if conn:
            conn.rollback()  # Při chybě vrátíme změny zpět
        logger.error(f"Databázová chyba: {e}")
        raise e
    finally:
        if conn:
            conn.close()