"""
Data 모듈 - 데이터베이스 및 모델

- database: SQLite 연결 및 스키마 관리
- models: 데이터 모델 클래스
- repositories: 데이터 접근 레이어 (CRUD)
"""

from data.database import Database
from data.models import Game, HistoryEntry, GlossaryTerm
from data.repositories import GameRepository, HistoryRepository, GlossaryRepository

__all__ = [
    "Database",
    "Game", "HistoryEntry", "GlossaryTerm",
    "GameRepository", "HistoryRepository", "GlossaryRepository"
]
