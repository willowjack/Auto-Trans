"""
SQLite 데이터베이스 관리

테이블 스키마:
- Games: 게임별 설정 저장
- History: 번역 히스토리 로그
- Glossary: 사용자 정의 용어집
"""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from utils.platform import get_data_dir


class Database:
    """SQLite 데이터베이스 관리 클래스"""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Path] = None):
        """
        Args:
            db_path: 데이터베이스 파일 경로 (None이면 기본 경로 사용)
        """
        if db_path is None:
            db_path = get_data_dir() / "auto_trans.db"
        self._db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def path(self) -> Path:
        return self._db_path

    def connect(self) -> None:
        """데이터베이스 연결"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self._db_path,
            check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        """데이터베이스 연결 종료"""
        if self._connection:
            self._connection.close()
            self._connection = None

    @contextmanager
    def cursor(self):
        """커서 컨텍스트 매니저"""
        if not self._connection:
            self.connect()
        cursor = self._connection.cursor()
        try:
            yield cursor
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            cursor.close()

    def _initialize_schema(self) -> None:
        """스키마 초기화"""
        with self.cursor() as cur:
            # Games 테이블 - 게임별 설정
            cur.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    process_name TEXT,
                    source_language TEXT DEFAULT 'auto',
                    target_language TEXT DEFAULT 'ko',
                    capture_region_x INTEGER,
                    capture_region_y INTEGER,
                    capture_region_w INTEGER,
                    capture_region_h INTEGER,
                    ocr_interval REAL DEFAULT 0.5,
                    stabilization_time REAL DEFAULT 1.5,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # History 테이블 - 번역 기록
            cur.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    original_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_language TEXT,
                    target_language TEXT,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE SET NULL
                )
            """)

            # Glossary 테이블 - 용어집
            cur.execute("""
                CREATE TABLE IF NOT EXISTS glossary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    original_term TEXT NOT NULL,
                    translated_term TEXT NOT NULL,
                    category TEXT,
                    notes TEXT,
                    is_global BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                    UNIQUE(game_id, original_term)
                )
            """)

            # 인덱스 생성
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_game_id
                ON history(game_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_created_at
                ON history(created_at)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_glossary_game_id
                ON glossary(game_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_glossary_original
                ON glossary(original_term)
            """)

            # 스키마 버전 테이블
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)

            # 버전 확인 및 설정
            cur.execute("SELECT version FROM schema_version")
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,)
                )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
