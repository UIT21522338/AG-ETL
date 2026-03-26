import os
import psycopg2
import psycopg2.extras
from shared.logging.logger import get_logger

logger = get_logger("pg_client")

class PGClient:
    def __init__(self):
        self._conn = None

    def connect(self):
        self._conn = psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=int(os.getenv("PG_PORT", 5432)),
            dbname=os.getenv("PG_DATABASE"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD")
        )
        logger.info("PostgreSQL connected")

    def fetchall(self, query: str, params=None) -> list:
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def execute(self, query: str, params=None):
        with self._conn.cursor() as cur:
            cur.execute(query, params)
        self._conn.commit()

    def execute_returning(self, query: str, params=None):
        with self._conn.cursor() as cur:
            cur.execute(query, params)
            self._conn.commit()
            return cur.fetchone()[0]

    def close(self):
        if self._conn:
            self._conn.close()
