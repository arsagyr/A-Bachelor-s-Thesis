from typing import List, Optional
import psycopg2
from models.country import Country

class CountryRepository:
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def get_all(self) -> List[Country]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM countries ORDER BY id")
            rows = cur.fetchall()
            # rows — список словарей (из-за RealDictCursor)
            return [Country(id=row['id'], name=row['name']) for row in rows]

    def get_by_id(self, country_id: int) -> Optional[Country]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM countries WHERE id = %s", (country_id,))
            row = cur.fetchone()
            if row:
                return Country(id=row['id'], name=row['name'])
            return None

    def get_by_name(self, name: str) -> Optional[Country]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM countries WHERE name = %s", (name,))
            row = cur.fetchone()
            if row:
                return Country(id=row['id'], name=row['name'])
            return None

    def create(self, name: str) -> Country:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO countries (name) VALUES (%s) RETURNING id",
                (name,)
            )
            row = cur.fetchone()
            country_id = row['id']
            self.conn.commit()
            return Country(id=country_id, name=name)

    def delete(self, country_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM countries WHERE id = %s", (country_id,))
            deleted = cur.rowcount > 0
            self.conn.commit()
            return deleted