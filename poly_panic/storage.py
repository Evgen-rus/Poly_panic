from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from poly_panic.models import MarketRecord, Snapshot


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._init_db()

    def close(self) -> None:
        self.connection.close()

    def _init_db(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS markets (
                market_id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                slug TEXT,
                category TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                yes_price REAL,
                volume_num REAL NOT NULL,
                FOREIGN KEY (market_id) REFERENCES markets(market_id)
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_market_time
            ON snapshots (market_id, observed_at DESC);

            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                summary TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_market_trigger_time
            ON alerts_sent (market_id, trigger_type, sent_at DESC);
            """
        )
        self.connection.commit()

    def market_exists(self, market_id: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM markets WHERE market_id = ? LIMIT 1", (market_id,)
        ).fetchone()
        return row is not None

    def upsert_market(self, market: MarketRecord, observed_at: datetime) -> None:
        now_iso = observed_at.isoformat()
        self.connection.execute(
            """
            INSERT INTO markets (market_id, question, slug, category, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(market_id) DO UPDATE SET
                question = excluded.question,
                slug = excluded.slug,
                category = excluded.category,
                last_seen_at = excluded.last_seen_at
            """,
            (
                market.market_id,
                market.question,
                market.slug,
                market.category,
                now_iso,
                now_iso,
            ),
        )

    def insert_snapshot(self, market: MarketRecord, observed_at: datetime) -> None:
        self.connection.execute(
            """
            INSERT INTO snapshots (market_id, observed_at, yes_price, volume_num)
            VALUES (?, ?, ?, ?)
            """,
            (
                market.market_id,
                observed_at.isoformat(),
                market.yes_price,
                market.volume_num,
            ),
        )

    def commit(self) -> None:
        self.connection.commit()

    def get_snapshot_before(self, market_id: str, target_time: datetime) -> Snapshot | None:
        row = self.connection.execute(
            """
            SELECT market_id, observed_at, yes_price, volume_num
            FROM snapshots
            WHERE market_id = ? AND observed_at <= ?
            ORDER BY observed_at DESC
            LIMIT 1
            """,
            (market_id, target_time.isoformat()),
        ).fetchone()
        return self._row_to_snapshot(row)

    def get_latest_snapshot_before(
        self, market_id: str, observed_at: datetime
    ) -> Snapshot | None:
        row = self.connection.execute(
            """
            SELECT market_id, observed_at, yes_price, volume_num
            FROM snapshots
            WHERE market_id = ? AND observed_at < ?
            ORDER BY observed_at DESC
            LIMIT 1
            """,
            (market_id, observed_at.isoformat()),
        ).fetchone()
        return self._row_to_snapshot(row)

    def recently_sent_alert(
        self,
        market_id: str,
        trigger_type: str,
        now: datetime,
        cooldown_minutes: int,
    ) -> bool:
        cutoff = (now - timedelta(minutes=cooldown_minutes)).isoformat()
        row = self.connection.execute(
            """
            SELECT 1
            FROM alerts_sent
            WHERE market_id = ? AND trigger_type = ? AND sent_at >= ?
            LIMIT 1
            """,
            (market_id, trigger_type, cutoff),
        ).fetchone()
        return row is not None

    def record_alert(
        self, market_id: str, trigger_type: str, summary: str, sent_at: datetime
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO alerts_sent (market_id, trigger_type, sent_at, summary)
            VALUES (?, ?, ?, ?)
            """,
            (market_id, trigger_type, sent_at.isoformat(), summary),
        )

    def get_top_movers(
        self, now: datetime, lookback_minutes: int, limit: int
    ) -> list[tuple[str, float, float | None, float | None]]:
        cutoff = now - timedelta(minutes=lookback_minutes)
        rows = self.connection.execute(
            """
            SELECT
                m.question AS question,
                ABS(s_now.yes_price - s_then.yes_price) AS delta,
                s_now.yes_price AS current_price,
                s_then.yes_price AS old_price
            FROM markets m
            JOIN snapshots s_now
                ON s_now.market_id = m.market_id
            JOIN snapshots s_then
                ON s_then.market_id = m.market_id
            WHERE s_now.observed_at = (
                SELECT MAX(observed_at)
                FROM snapshots
                WHERE market_id = m.market_id AND observed_at <= ?
            )
              AND s_then.observed_at = (
                SELECT MAX(observed_at)
                FROM snapshots
                WHERE market_id = m.market_id AND observed_at <= ?
            )
              AND s_now.yes_price IS NOT NULL
              AND s_then.yes_price IS NOT NULL
            ORDER BY delta DESC
            LIMIT ?
            """,
            (now.isoformat(), cutoff.isoformat(), limit),
        ).fetchall()

        return [
            (
                row["question"],
                float(row["delta"]),
                self._optional_float(row["current_price"]),
                self._optional_float(row["old_price"]),
            )
            for row in rows
            if row["delta"] is not None
        ]

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row | None) -> Snapshot | None:
        if row is None:
            return None
        return Snapshot(
            market_id=row["market_id"],
            observed_at=datetime.fromisoformat(row["observed_at"]).astimezone(
                timezone.utc
            ),
            yes_price=Storage._optional_float(row["yes_price"]),
            volume_num=float(row["volume_num"]),
        )

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None:
            return None
        return float(value)
