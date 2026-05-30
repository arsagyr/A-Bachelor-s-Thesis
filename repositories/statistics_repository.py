from typing import List, Optional, Tuple
import psycopg2
from models.statistics import Statistics

class StatisticsRepository:
    def __init__(self, conn: psycopg2.extensions.connection):
        self.conn = conn

    def get_by_country_and_year(self, country_id: int, year: int) -> List[Statistics]:
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT country_id, year, indicator_id, value
                   FROM statistics
                   WHERE country_id = %s AND year = %s""",
                (country_id, year)
            )
            rows = cur.fetchall()
            return [Statistics(country_id=r['country_id'], year=r['year'], 
                               indicator_id=r['indicator_id'], value=r['value']) for r in rows]

    def get_by_country(self, country_id: int) -> List[Statistics]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT country_id, year, indicator_id, value FROM statistics WHERE country_id = %s",
                (country_id,)
            )
            rows = cur.fetchall()
            return [Statistics(country_id=r['country_id'], year=r['year'],
                               indicator_id=r['indicator_id'], value=r['value']) for r in rows]

    def get_value(self, country_id: int, year: int, indicator_id: int) -> Optional[float]:
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT value FROM statistics
                   WHERE country_id = %s AND year = %s AND indicator_id = %s""",
                (country_id, year, indicator_id)
            )
            row = cur.fetchone()
            return row['value'] if row else None

    def upsert(self, statistics: Statistics) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO statistics (country_id, year, indicator_id, value)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (country_id, year, indicator_id)
                   DO UPDATE SET value = EXCLUDED.value""",
                (statistics.country_id, statistics.year, statistics.indicator_id, statistics.value)
            )
            self.conn.commit()

    def delete(self, country_id: int, year: int, indicator_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM statistics WHERE country_id = %s AND year = %s AND indicator_id = %s",
                (country_id, year, indicator_id)
            )
            deleted = cur.rowcount > 0
            self.conn.commit()
            return deleted

    def delete_for_country_and_year(self, country_id: int, year: int) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM statistics WHERE country_id = %s AND year = %s",
                (country_id, year)
            )
            deleted = cur.rowcount
            self.conn.commit()
            return deleted

    def delete_by_indicator(self, indicator_id: int) -> int:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM statistics WHERE indicator_id = %s", (indicator_id,))
            deleted = cur.rowcount
            self.conn.commit()
            return deleted

    def delete_by_country(self, country_id: int) -> int:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM statistics WHERE country_id = %s", (country_id,))
            deleted = cur.rowcount
            self.conn.commit()
            return deleted

    def filter(self, country_id=None, start_year=None, end_year=None, indicator_id=None):
        query = "SELECT country_id, year, indicator_id, value FROM statistics WHERE 1=1"
        params = []
        if country_id:
            query += " AND country_id = %s"
            params.append(country_id)
        if start_year:
            query += " AND year >= %s"
            params.append(start_year)
        if end_year:
            query += " AND year <= %s"
            params.append(end_year)
        if indicator_id:
            query += " AND indicator_id = %s"
            params.append(indicator_id)
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [Statistics(country_id=r['country_id'], year=r['year'],
                               indicator_id=r['indicator_id'], value=r['value']) for r in rows]

    def get_years(self) -> List[int]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT year FROM statistics ORDER BY year")
            rows = cur.fetchall()
            return [row['year'] for row in rows]