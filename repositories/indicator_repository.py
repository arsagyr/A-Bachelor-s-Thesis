from typing import List, Optional
import psycopg2
from models.indicator import Indicator

class IndicatorRepository:
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def get_all(self) -> List[Indicator]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM indicators ORDER BY id")
            rows = cur.fetchall()
            return [Indicator(id=row['id'], name=row['name']) for row in rows]

    def get_by_id(self, indicator_id: int) -> Optional[Indicator]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM indicators WHERE id = %s", (indicator_id,))
            row = cur.fetchone()
            if row:
                return Indicator(id=row['id'], name=row['name'])
            return None

    def get_by_name(self, name: str) -> Optional[Indicator]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM indicators WHERE name = %s", (name,))
            row = cur.fetchone()
            if row:
                return Indicator(id=row['id'], name=row['name'])
            return None

    def create(self, name: str) -> Indicator:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO indicators (name) VALUES (%s) RETURNING id",
                (name,)
            )
            row = cur.fetchone()
            indicator_id = row['id']
            self.conn.commit()
            return Indicator(id=indicator_id, name=name)

    def delete(self, indicator_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM indicators WHERE id = %s", (indicator_id,))
            deleted = cur.rowcount > 0
            self.conn.commit()
            return deleted