"""SQLite Persistence for Campus Obstacle Reports.

Implements parameterised, persistent storage for obstacle lifecycles:
SUBMITTED -> UNDER_REVIEW -> VERIFIED -> RESOLVED / REJECTED.
Ensures report modifications persist across application restarts.
"""

import sqlite3
import os
import datetime
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Set
from campus_navigator.models.core_models import (
    ObstacleReport,
    ObstacleType,
    ObstacleSeverity,
    ObstacleStatus,
    VerificationStatus,
)


class ObstacleDB:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to campus_navigator/db/obstacles.db
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, "obstacles.db")
        else:
            self.db_path = db_path
        
        self.init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create tables if they don't exist and upgrade schema if columns are missing."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS obstacle_reports (
                    id TEXT PRIMARY KEY,
                    location_or_edge_id TEXT NOT NULL,
                    obstacle_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reported_by_role TEXT NOT NULL,
                    verification_notes TEXT DEFAULT '',
                    expiration_time TEXT DEFAULT NULL,
                    location_id TEXT DEFAULT NULL,
                    pathway_id TEXT DEFAULT NULL,
                    building_id TEXT DEFAULT NULL,
                    floor_id INTEGER DEFAULT NULL,
                    verification_status TEXT DEFAULT 'PROVISIONAL'
                );
            """)
            conn.commit()

            # Ensure newly added columns exist if table was previously created
            existing_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(obstacle_reports)").fetchall()}
            new_columns = [
                ("location_id", "TEXT DEFAULT NULL"),
                ("pathway_id", "TEXT DEFAULT NULL"),
                ("building_id", "TEXT DEFAULT NULL"),
                ("floor_id", "INTEGER DEFAULT NULL"),
                ("verification_status", "TEXT DEFAULT 'PROVISIONAL'"),
                ("resolved_at", "TEXT DEFAULT NULL")
            ]
            for col_name, col_def in new_columns:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE obstacle_reports ADD COLUMN {col_name} {col_def};")
            conn.commit()

            cursor.execute("SELECT COUNT(*) as cnt FROM obstacle_reports")
            row = cursor.fetchone()
            if row and row["cnt"] == 0:
                self._seed_initial_obstacles(cursor)
                conn.commit()

    def _seed_initial_obstacles(self, cursor: sqlite3.Cursor) -> None:
        seed_data = [
            (
                "OBS-2026-001",
                "E_FET_STAIR_G_1",
                "CONSTRUCTION",
                "Demonstration: Routine maintenance on Ground-to-First stairwell handrail.",
                "MEDIUM",
                "2026-10-10 09:30:00",
                "UNDER_REVIEW",
                "Campus Facility Team",
                "Under safety inspection.",
                None,
                None,
                "E_FET_STAIR_G_1",
                "FET_MAIN",
                0,
                "PROVISIONAL"
            ),
            (
                "OBS-2026-002",
                "E_OUTDOOR_ADMIN_PATH",
                "TEMPORARY_OBSTRUCTION",
                "Demonstration: Landscaping machinery temporarily placed on outdoor brick pathway.",
                "LOW",
                "2026-10-11 14:15:00",
                "SUBMITTED",
                "Student / Visitor",
                "Awaiting groundskeeper clearance.",
                None,
                None,
                "E_OUTDOOR_ADMIN_PATH",
                None,
                None,
                "PROVISIONAL"
            )
        ]
        cursor.executemany("""
            INSERT INTO obstacle_reports (
                id, location_or_edge_id, obstacle_type, description,
                severity, timestamp, status, reported_by_role,
                verification_notes, expiration_time,
                location_id, pathway_id, building_id, floor_id, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)

    def add_report(self, report: ObstacleReport) -> bool:
        """Insert or replace obstacle report using parameterized query."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO obstacle_reports (
                    id, location_or_edge_id, obstacle_type, description,
                    severity, timestamp, status, reported_by_role,
                    verification_notes, expiration_time,
                    location_id, pathway_id, building_id, floor_id, verification_status, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.id,
                report.location_or_edge_id,
                report.obstacle_type.value if isinstance(report.obstacle_type, ObstacleType) else report.obstacle_type,
                report.description,
                report.severity.value if isinstance(report.severity, ObstacleSeverity) else report.severity,
                report.timestamp,
                report.status.value if isinstance(report.status, ObstacleStatus) else report.status,
                report.reported_by_role,
                report.verification_notes,
                report.expiration_time,
                report.location_id,
                report.pathway_id,
                report.building_id,
                report.floor_id,
                report.verification_status.value if isinstance(report.verification_status, VerificationStatus) else report.verification_status,
                report.resolved_at
            ))
            conn.commit()
            return True

    def update_report_status(
        self,
        report_id: str,
        new_status: ObstacleStatus,
        verification_notes: str = "",
        verification_status: Optional[VerificationStatus] = None,
        resolved_at: Optional[str] = None
    ) -> bool:
        """Update lifecycle status, resolution timestamp, and verification state."""
        # Auto-stamp resolved_at if status transitioning to RESOLVED and not provided
        if (new_status == ObstacleStatus.RESOLVED or str(new_status) == "RESOLVED") and resolved_at is None:
            resolved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with self._connection() as conn:
            cursor = conn.cursor()
            if verification_status:
                cursor.execute("""
                    UPDATE obstacle_reports
                    SET status = ?, verification_notes = ?, verification_status = ?, resolved_at = COALESCE(?, resolved_at)
                    WHERE id = ?
                """, (
                    new_status.value if isinstance(new_status, ObstacleStatus) else new_status,
                    verification_notes,
                    verification_status.value if isinstance(verification_status, VerificationStatus) else verification_status,
                    resolved_at,
                    report_id
                ))
            else:
                cursor.execute("""
                    UPDATE obstacle_reports
                    SET status = ?, verification_notes = ?, resolved_at = COALESCE(?, resolved_at)
                    WHERE id = ?
                """, (
                    new_status.value if isinstance(new_status, ObstacleStatus) else new_status,
                    verification_notes,
                    resolved_at,
                    report_id
                ))
            conn.commit()
            return cursor.rowcount > 0

    def get_report(self, report_id: str) -> Optional[ObstacleReport]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM obstacle_reports WHERE id = ?", (report_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_model(row)
        return None

    def get_all_reports(self) -> List[ObstacleReport]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM obstacle_reports ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [self._row_to_model(r) for r in rows]

    def get_active_blocking_obstacles(self, current_time_iso: Optional[str] = None) -> List[ObstacleReport]:
        """Fetch all reports that actively block or impede navigation, considering expiration policy."""
        if current_time_iso is None:
            current_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        all_reports = self.get_all_reports()
        return [r for r in all_reports if r.is_blocking_for_routing(current_time_iso=current_time_iso)]

    def get_blocked_target_ids(self, current_time_iso: Optional[str] = None) -> Set[str]:
        """Return set of location_or_edge_id that are currently blocked."""
        active = self.get_active_blocking_obstacles(current_time_iso)
        blocked_ids = set()
        for r in active:
            blocked_ids.add(r.location_or_edge_id)
            if r.pathway_id:
                blocked_ids.add(r.pathway_id)
            if r.location_id:
                blocked_ids.add(r.location_id)
        return blocked_ids

    def save_report(self, report: ObstacleReport) -> bool:
        """Alias for add_report to support common repository idioms."""
        return self.add_report(report)

    def get_report_by_id(self, report_id: str) -> Optional[ObstacleReport]:
        """Alias for get_report."""
        return self.get_report(report_id)

    def get_active_reports(self, current_time_iso: Optional[str] = None) -> List[ObstacleReport]:
        """Alias for get_active_blocking_obstacles."""
        return self.get_active_blocking_obstacles(current_time_iso)

    def delete_report(self, report_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM obstacle_reports WHERE id = ?", (report_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_model(self, row: sqlite3.Row) -> ObstacleReport:
        keys = row.keys()
        return ObstacleReport(
            id=row["id"],
            location_or_edge_id=row["location_or_edge_id"],
            obstacle_type=ObstacleType(row["obstacle_type"]) if row["obstacle_type"] in ObstacleType._value2member_map_ else ObstacleType.OTHER,
            description=row["description"],
            severity=ObstacleSeverity(row["severity"]) if row["severity"] in ObstacleSeverity._value2member_map_ else ObstacleSeverity.MEDIUM,
            timestamp=row["timestamp"],
            status=ObstacleStatus(row["status"]) if row["status"] in ObstacleStatus._value2member_map_ else ObstacleStatus.SUBMITTED,
            reported_by_role=row["reported_by_role"],
            verification_notes=row["verification_notes"] or "",
            expiration_time=row["expiration_time"],
            location_id=row["location_id"] if "location_id" in keys else None,
            pathway_id=row["pathway_id"] if "pathway_id" in keys else None,
            building_id=row["building_id"] if "building_id" in keys else None,
            floor_id=row["floor_id"] if "floor_id" in keys else None,
            verification_status=VerificationStatus(row["verification_status"]) if "verification_status" in keys and row["verification_status"] in VerificationStatus._value2member_map_ else VerificationStatus.PROVISIONAL,
            resolved_at=row["resolved_at"] if "resolved_at" in keys else None
        )
