"""
Repository 패턴 - 데이터 접근 레이어

각 테이블에 대한 CRUD 작업을 캡슐화합니다.
"""

from typing import Optional
from datetime import datetime

from data.database import Database
from data.models import Game, HistoryEntry, GlossaryTerm


class GameRepository:
    """게임 설정 Repository"""

    def __init__(self, db: Database):
        self._db = db

    def create(self, game: Game) -> Game:
        """게임 생성"""
        with self._db.cursor() as cur:
            cur.execute("""
                INSERT INTO games (
                    name, process_name, source_language, target_language,
                    capture_region_x, capture_region_y,
                    capture_region_w, capture_region_h,
                    ocr_interval, stabilization_time, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game.name, game.process_name,
                game.source_language, game.target_language,
                game.capture_region_x, game.capture_region_y,
                game.capture_region_w, game.capture_region_h,
                game.ocr_interval, game.stabilization_time,
                game.is_active
            ))
            game.id = cur.lastrowid
        return game

    def get_by_id(self, game_id: int) -> Optional[Game]:
        """ID로 게임 조회"""
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM games WHERE id = ?", (game_id,))
            row = cur.fetchone()
            if row:
                return self._row_to_game(row)
        return None

    def get_by_name(self, name: str) -> Optional[Game]:
        """이름으로 게임 조회"""
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM games WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                return self._row_to_game(row)
        return None

    def get_all(self, active_only: bool = False) -> list[Game]:
        """모든 게임 조회"""
        with self._db.cursor() as cur:
            if active_only:
                cur.execute("SELECT * FROM games WHERE is_active = 1 ORDER BY name")
            else:
                cur.execute("SELECT * FROM games ORDER BY name")
            return [self._row_to_game(row) for row in cur.fetchall()]

    def update(self, game: Game) -> None:
        """게임 업데이트"""
        with self._db.cursor() as cur:
            cur.execute("""
                UPDATE games SET
                    name = ?, process_name = ?,
                    source_language = ?, target_language = ?,
                    capture_region_x = ?, capture_region_y = ?,
                    capture_region_w = ?, capture_region_h = ?,
                    ocr_interval = ?, stabilization_time = ?,
                    is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                game.name, game.process_name,
                game.source_language, game.target_language,
                game.capture_region_x, game.capture_region_y,
                game.capture_region_w, game.capture_region_h,
                game.ocr_interval, game.stabilization_time,
                game.is_active, game.id
            ))

    def delete(self, game_id: int) -> None:
        """게임 삭제"""
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM games WHERE id = ?", (game_id,))

    def _row_to_game(self, row) -> Game:
        """Row를 Game 객체로 변환"""
        return Game(
            id=row["id"],
            name=row["name"],
            process_name=row["process_name"],
            source_language=row["source_language"],
            target_language=row["target_language"],
            capture_region_x=row["capture_region_x"],
            capture_region_y=row["capture_region_y"],
            capture_region_w=row["capture_region_w"],
            capture_region_h=row["capture_region_h"],
            ocr_interval=row["ocr_interval"],
            stabilization_time=row["stabilization_time"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


class HistoryRepository:
    """번역 히스토리 Repository"""

    def __init__(self, db: Database):
        self._db = db

    def create(self, entry: HistoryEntry) -> HistoryEntry:
        """히스토리 항목 생성"""
        with self._db.cursor() as cur:
            cur.execute("""
                INSERT INTO history (
                    game_id, original_text, translated_text,
                    source_language, target_language, confidence
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.game_id, entry.original_text, entry.translated_text,
                entry.source_language, entry.target_language, entry.confidence
            ))
            entry.id = cur.lastrowid
        return entry

    def get_recent(self, limit: int = 100, game_id: Optional[int] = None) -> list[HistoryEntry]:
        """최근 히스토리 조회"""
        with self._db.cursor() as cur:
            if game_id is not None:
                cur.execute("""
                    SELECT * FROM history
                    WHERE game_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (game_id, limit))
            else:
                cur.execute("""
                    SELECT * FROM history
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def search(self, query: str, limit: int = 50) -> list[HistoryEntry]:
        """히스토리 검색"""
        with self._db.cursor() as cur:
            cur.execute("""
                SELECT * FROM history
                WHERE original_text LIKE ? OR translated_text LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def delete_old(self, days: int = 30) -> int:
        """오래된 히스토리 삭제"""
        with self._db.cursor() as cur:
            cur.execute("""
                DELETE FROM history
                WHERE created_at < datetime('now', ?)
            """, (f"-{days} days",))
            return cur.rowcount

    def clear_all(self, game_id: Optional[int] = None) -> int:
        """히스토리 전체 삭제"""
        with self._db.cursor() as cur:
            if game_id is not None:
                cur.execute("DELETE FROM history WHERE game_id = ?", (game_id,))
            else:
                cur.execute("DELETE FROM history")
            return cur.rowcount

    def _row_to_entry(self, row) -> HistoryEntry:
        """Row를 HistoryEntry 객체로 변환"""
        return HistoryEntry(
            id=row["id"],
            game_id=row["game_id"],
            original_text=row["original_text"],
            translated_text=row["translated_text"],
            source_language=row["source_language"],
            target_language=row["target_language"],
            confidence=row["confidence"],
            created_at=row["created_at"]
        )


class GlossaryRepository:
    """용어집 Repository"""

    def __init__(self, db: Database):
        self._db = db

    def create(self, term: GlossaryTerm) -> GlossaryTerm:
        """용어 생성"""
        with self._db.cursor() as cur:
            cur.execute("""
                INSERT INTO glossary (
                    game_id, original_term, translated_term,
                    category, notes, is_global
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                term.game_id, term.original_term, term.translated_term,
                term.category, term.notes, term.is_global
            ))
            term.id = cur.lastrowid
        return term

    def get_by_id(self, term_id: int) -> Optional[GlossaryTerm]:
        """ID로 용어 조회"""
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM glossary WHERE id = ?", (term_id,))
            row = cur.fetchone()
            if row:
                return self._row_to_term(row)
        return None

    def get_for_game(self, game_id: int, include_global: bool = True) -> list[GlossaryTerm]:
        """게임별 용어집 조회"""
        with self._db.cursor() as cur:
            if include_global:
                cur.execute("""
                    SELECT * FROM glossary
                    WHERE game_id = ? OR is_global = 1
                    ORDER BY original_term
                """, (game_id,))
            else:
                cur.execute("""
                    SELECT * FROM glossary
                    WHERE game_id = ?
                    ORDER BY original_term
                """, (game_id,))
            return [self._row_to_term(row) for row in cur.fetchall()]

    def get_global(self) -> list[GlossaryTerm]:
        """전역 용어집 조회"""
        with self._db.cursor() as cur:
            cur.execute("""
                SELECT * FROM glossary
                WHERE is_global = 1
                ORDER BY original_term
            """)
            return [self._row_to_term(row) for row in cur.fetchall()]

    def get_as_dict(self, game_id: Optional[int] = None) -> dict[str, str]:
        """용어집을 딕셔너리로 반환 (번역 매니저용)"""
        with self._db.cursor() as cur:
            if game_id is not None:
                cur.execute("""
                    SELECT original_term, translated_term FROM glossary
                    WHERE game_id = ? OR is_global = 1
                """, (game_id,))
            else:
                cur.execute("""
                    SELECT original_term, translated_term FROM glossary
                    WHERE is_global = 1
                """)
            return {row["original_term"]: row["translated_term"] for row in cur.fetchall()}

    def update(self, term: GlossaryTerm) -> None:
        """용어 업데이트"""
        with self._db.cursor() as cur:
            cur.execute("""
                UPDATE glossary SET
                    original_term = ?, translated_term = ?,
                    category = ?, notes = ?, is_global = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                term.original_term, term.translated_term,
                term.category, term.notes, term.is_global,
                term.id
            ))

    def delete(self, term_id: int) -> None:
        """용어 삭제"""
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM glossary WHERE id = ?", (term_id,))

    def _row_to_term(self, row) -> GlossaryTerm:
        """Row를 GlossaryTerm 객체로 변환"""
        return GlossaryTerm(
            id=row["id"],
            game_id=row["game_id"],
            original_term=row["original_term"],
            translated_term=row["translated_term"],
            category=row["category"],
            notes=row["notes"],
            is_global=bool(row["is_global"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
