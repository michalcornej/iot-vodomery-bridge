import logging
from contextlib import contextmanager

from psycopg2.pool import ThreadedConnectionPool

from app.config import settings

logger = logging.getLogger(__name__)

_pool: ThreadedConnectionPool | None = None


def init_pool() -> None:
    """Vytvoří pool spojení. Volá se jednou při startu aplikace."""
    global _pool
    if _pool is not None:
        return
    _pool = ThreadedConnectionPool(
        minconn=settings.DB_POOL_MIN,
        maxconn=settings.DB_POOL_MAX,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD.get_secret_value(),
        connect_timeout=5,
    )
    logger.info("Pool spojení do PostgreSQL vytvořen (%s:%s/%s)", settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def get_db_cursor():
    """Půjčí spojení z poolu a vrátí kurzor v rámci jedné transakce.

    Při úspěchu se transakce potvrdí, při výjimce vrátí zpět.
    """
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    broken = False
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            broken = True  # spojení je mrtvé, do poolu ho nevracíme
        raise
    finally:
        _pool.putconn(conn, close=broken or bool(conn.closed))
