"""
히스토리 에디터 - 번역 로그 관리 및 편집

기능:
- 실시간 번역 로그 표시
- 단어/화자 이름 편집 → DB 업데이트
- 오버레이 즉시 반영 (Signal 연결)
- 용어집 자동 학습
"""

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QHeaderView, QAbstractItemView,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox, QCheckBox,
    QSplitter, QTextEdit, QMenu, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QAction, QKeySequence, QShortcut

from core.interfaces import TranslationResult


@dataclass
class HistoryItem:
    """히스토리 항목"""
    id: int
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    timestamp: datetime
    game_id: Optional[int] = None
    confidence: float = 0.0
    is_edited: bool = False


class EditDialog(QDialog):
    """번역 편집 다이얼로그"""

    def __init__(
        self,
        original: str,
        translated: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._original = original
        self._translated = translated

        self.setWindowTitle("번역 편집")
        self.setMinimumSize(400, 300)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 구성"""
        layout = QVBoxLayout(self)

        # 원문 (읽기 전용)
        layout.addWidget(QLabel("원문:"))
        self._original_edit = QTextEdit()
        self._original_edit.setText(self._original)
        self._original_edit.setReadOnly(True)
        self._original_edit.setMaximumHeight(80)
        self._original_edit.setStyleSheet("background-color: #f0f0f0;")
        layout.addWidget(self._original_edit)

        # 번역문 (편집 가능)
        layout.addWidget(QLabel("번역:"))
        self._translated_edit = QTextEdit()
        self._translated_edit.setText(self._translated)
        self._translated_edit.setMinimumHeight(100)
        layout.addWidget(self._translated_edit)

        # 용어집 추가 옵션
        glossary_frame = QFrame()
        glossary_frame.setFrameShape(QFrame.Shape.StyledPanel)
        glossary_layout = QVBoxLayout(glossary_frame)

        self._add_to_glossary = QCheckBox("수정 내용을 용어집에 추가")
        glossary_layout.addWidget(self._add_to_glossary)

        # 용어 선택 (원문에서 특정 단어 선택)
        term_layout = QHBoxLayout()
        term_layout.addWidget(QLabel("용어:"))
        self._term_original = QLineEdit()
        self._term_original.setPlaceholderText("원문 용어")
        term_layout.addWidget(self._term_original)
        term_layout.addWidget(QLabel("→"))
        self._term_translated = QLineEdit()
        self._term_translated.setPlaceholderText("번역 용어")
        term_layout.addWidget(self._term_translated)
        glossary_layout.addLayout(term_layout)

        # 카테고리
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("카테고리:"))
        self._category_combo = QComboBox()
        self._category_combo.addItems([
            "일반", "캐릭터", "아이템", "스킬", "지명", "UI", "기타"
        ])
        self._category_combo.setEditable(True)
        cat_layout.addWidget(self._category_combo)
        cat_layout.addStretch()
        glossary_layout.addLayout(cat_layout)

        layout.addWidget(glossary_frame)

        # 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_translated_text(self) -> str:
        """수정된 번역문 반환"""
        return self._translated_edit.toPlainText()

    def should_add_to_glossary(self) -> bool:
        """용어집 추가 여부"""
        return self._add_to_glossary.isChecked()

    def get_glossary_term(self) -> Optional[tuple[str, str, str]]:
        """용어집 항목 반환 (원문, 번역, 카테고리)"""
        if not self._add_to_glossary.isChecked():
            return None

        orig = self._term_original.text().strip()
        trans = self._term_translated.text().strip()
        cat = self._category_combo.currentText()

        if orig and trans:
            return (orig, trans, cat)
        return None


class HistoryEditor(QWidget):
    """
    히스토리 에디터 위젯

    실시간으로 번역 로그를 표시하고 편집할 수 있습니다.
    수정 시 DB가 업데이트되고 오버레이에 즉시 반영됩니다.

    Signals:
        translation_edited: 번역 수정 시 (id, original, new_translated)
        glossary_added: 용어집 추가 시 (original, translated, category)
        entry_selected: 항목 선택 시 (original, translated)
        overlay_update_requested: 오버레이 업데이트 요청 (original, translated)
    """

    # 시그널 정의
    translation_edited = pyqtSignal(int, str, str)  # (id, original, new_translated)
    glossary_added = pyqtSignal(str, str, str)  # (original, translated, category)
    entry_selected = pyqtSignal(str, str)  # (original, translated)
    overlay_update_requested = pyqtSignal(str, str)  # (original, translated)

    # 테이블 컬럼
    COL_TIME = 0
    COL_ORIGINAL = 1
    COL_TRANSLATED = 2
    COL_EDITED = 3

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._items: List[HistoryItem] = []
        self._current_game_id: Optional[int] = None
        self._auto_scroll = True
        self._max_items = 500

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 상단 툴바
        toolbar = QHBoxLayout()

        # 검색
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("검색...")
        self._search_edit.textChanged.connect(self._on_search)
        toolbar.addWidget(self._search_edit)

        # 필터
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["전체", "수정됨", "미수정"])
        self._filter_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self._filter_combo)

        # 자동 스크롤
        self._auto_scroll_check = QCheckBox("자동 스크롤")
        self._auto_scroll_check.setChecked(True)
        self._auto_scroll_check.toggled.connect(self._on_auto_scroll_changed)
        toolbar.addWidget(self._auto_scroll_check)

        # 클리어 버튼
        self._clear_btn = QPushButton("클리어")
        self._clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(self._clear_btn)

        layout.addLayout(toolbar)

        # 테이블
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["시간", "원문", "번역", "수정"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)

        # 컬럼 크기 조정
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(self.COL_TIME, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_ORIGINAL, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_TRANSLATED, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_EDITED, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(self.COL_TIME, 80)
        self._table.setColumnWidth(self.COL_EDITED, 50)

        # 이벤트 연결
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self._table)

        # 하단 미리보기
        preview_layout = QHBoxLayout()

        self._preview_original = QLabel()
        self._preview_original.setWordWrap(True)
        self._preview_original.setStyleSheet("background-color: #f5f5f5; padding: 8px; border-radius: 4px;")
        preview_layout.addWidget(self._preview_original, 1)

        self._preview_translated = QLabel()
        self._preview_translated.setWordWrap(True)
        self._preview_translated.setStyleSheet("background-color: #e8f5e9; padding: 8px; border-radius: 4px;")
        preview_layout.addWidget(self._preview_translated, 1)

        layout.addLayout(preview_layout)

        # 하단 버튼
        button_layout = QHBoxLayout()

        self._edit_btn = QPushButton("편집 (Enter)")
        self._edit_btn.clicked.connect(self._edit_selected)
        button_layout.addWidget(self._edit_btn)

        self._copy_btn = QPushButton("복사")
        self._copy_btn.clicked.connect(self._copy_selected)
        button_layout.addWidget(self._copy_btn)

        self._show_overlay_btn = QPushButton("오버레이에 표시")
        self._show_overlay_btn.clicked.connect(self._show_in_overlay)
        button_layout.addWidget(self._show_overlay_btn)

        button_layout.addStretch()

        self._export_btn = QPushButton("내보내기")
        self._export_btn.clicked.connect(self._export_history)
        button_layout.addWidget(self._export_btn)

        layout.addLayout(button_layout)

    def _setup_shortcuts(self) -> None:
        """단축키 설정"""
        # Enter: 편집
        edit_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        edit_shortcut.activated.connect(self._edit_selected)

        # Delete: 삭제
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        delete_shortcut.activated.connect(self._delete_selected)

        # Ctrl+C: 복사
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        copy_shortcut.activated.connect(self._copy_selected)

    # === 데이터 관리 ===

    def add_entry(self, result: TranslationResult) -> None:
        """
        새 번역 결과 추가

        TranslationService의 on_translation_complete에 연결하세요.
        """
        item = HistoryItem(
            id=len(self._items) + 1,
            original_text=result.original_text,
            translated_text=result.translated_text,
            source_language=result.source_language or "auto",
            target_language=result.target_language,
            timestamp=datetime.now(),
            confidence=result.confidence
        )

        self._items.append(item)
        self._add_table_row(item)

        # 최대 항목 수 제한
        if len(self._items) > self._max_items:
            self._items.pop(0)
            self._table.removeRow(0)

        # 자동 스크롤
        if self._auto_scroll:
            self._table.scrollToBottom()

    def add_entry_from_data(
        self,
        id: int,
        original: str,
        translated: str,
        source_lang: str = "auto",
        target_lang: str = "ko",
        timestamp: Optional[datetime] = None,
        game_id: Optional[int] = None,
        confidence: float = 0.0
    ) -> None:
        """데이터로 직접 항목 추가"""
        item = HistoryItem(
            id=id,
            original_text=original,
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            timestamp=timestamp or datetime.now(),
            game_id=game_id,
            confidence=confidence
        )

        self._items.append(item)
        self._add_table_row(item)

        if self._auto_scroll:
            self._table.scrollToBottom()

    def _add_table_row(self, item: HistoryItem) -> None:
        """테이블에 행 추가"""
        row = self._table.rowCount()
        self._table.insertRow(row)

        # 시간
        time_item = QTableWidgetItem(item.timestamp.strftime("%H:%M:%S"))
        time_item.setData(Qt.ItemDataRole.UserRole, item.id)
        self._table.setItem(row, self.COL_TIME, time_item)

        # 원문 (줄임)
        orig_text = item.original_text[:50] + "..." if len(item.original_text) > 50 else item.original_text
        self._table.setItem(row, self.COL_ORIGINAL, QTableWidgetItem(orig_text))

        # 번역문 (줄임)
        trans_text = item.translated_text[:50] + "..." if len(item.translated_text) > 50 else item.translated_text
        self._table.setItem(row, self.COL_TRANSLATED, QTableWidgetItem(trans_text))

        # 수정 여부
        edited_item = QTableWidgetItem("✓" if item.is_edited else "")
        edited_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, self.COL_EDITED, edited_item)

    def set_game_id(self, game_id: Optional[int]) -> None:
        """현재 게임 ID 설정"""
        self._current_game_id = game_id

    def load_from_db(self, entries: List[HistoryItem]) -> None:
        """DB에서 로드"""
        self._items.clear()
        self._table.setRowCount(0)

        for item in entries:
            self._items.append(item)
            self._add_table_row(item)

    def clear(self) -> None:
        """모든 항목 삭제"""
        self._items.clear()
        self._table.setRowCount(0)

    # === 이벤트 핸들러 ===

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        """셀 더블클릭 - 편집"""
        self._edit_row(row)

    def _on_selection_changed(self) -> None:
        """선택 변경 - 미리보기 업데이트"""
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._preview_original.setText("")
            self._preview_translated.setText("")
            return

        row = rows[0].row()
        if 0 <= row < len(self._items):
            item = self._items[row]
            self._preview_original.setText(item.original_text)
            self._preview_translated.setText(item.translated_text)
            self.entry_selected.emit(item.original_text, item.translated_text)

    def _on_search(self, text: str) -> None:
        """검색"""
        text = text.lower()
        for row in range(self._table.rowCount()):
            if row >= len(self._items):
                continue

            item = self._items[row]
            match = (
                text in item.original_text.lower() or
                text in item.translated_text.lower()
            )
            self._table.setRowHidden(row, not match)

    def _apply_filter(self, index: int) -> None:
        """필터 적용"""
        for row in range(self._table.rowCount()):
            if row >= len(self._items):
                continue

            item = self._items[row]
            if index == 0:  # 전체
                self._table.setRowHidden(row, False)
            elif index == 1:  # 수정됨
                self._table.setRowHidden(row, not item.is_edited)
            elif index == 2:  # 미수정
                self._table.setRowHidden(row, item.is_edited)

    def _on_auto_scroll_changed(self, checked: bool) -> None:
        """자동 스크롤 설정 변경"""
        self._auto_scroll = checked

    def _on_clear(self) -> None:
        """클리어"""
        reply = QMessageBox.question(
            self, "확인",
            "모든 히스토리를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.clear()

    # === 편집 ===

    def _get_selected_row(self) -> Optional[int]:
        """선택된 행 반환"""
        rows = self._table.selectionModel().selectedRows()
        if rows:
            return rows[0].row()
        return None

    def _get_selected_item(self) -> Optional[HistoryItem]:
        """선택된 항목 반환"""
        row = self._get_selected_row()
        if row is not None and 0 <= row < len(self._items):
            return self._items[row]
        return None

    def _edit_selected(self) -> None:
        """선택된 항목 편집"""
        row = self._get_selected_row()
        if row is not None:
            self._edit_row(row)

    def _edit_row(self, row: int) -> None:
        """행 편집"""
        if row < 0 or row >= len(self._items):
            return

        item = self._items[row]

        dialog = EditDialog(item.original_text, item.translated_text, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_translated = dialog.get_translated_text()

            if new_translated != item.translated_text:
                # 항목 업데이트
                item.translated_text = new_translated
                item.is_edited = True

                # 테이블 업데이트
                trans_text = new_translated[:50] + "..." if len(new_translated) > 50 else new_translated
                self._table.item(row, self.COL_TRANSLATED).setText(trans_text)
                self._table.item(row, self.COL_EDITED).setText("✓")

                # 미리보기 업데이트
                self._preview_translated.setText(new_translated)

                # 시그널 발생 (DB 업데이트 및 오버레이 반영)
                self.translation_edited.emit(item.id, item.original_text, new_translated)
                self.overlay_update_requested.emit(item.original_text, new_translated)

            # 용어집 추가
            glossary_term = dialog.get_glossary_term()
            if glossary_term:
                orig, trans, cat = glossary_term
                self.glossary_added.emit(orig, trans, cat)

    def _delete_selected(self) -> None:
        """선택된 항목 삭제"""
        row = self._get_selected_row()
        if row is not None and 0 <= row < len(self._items):
            del self._items[row]
            self._table.removeRow(row)

    def _copy_selected(self) -> None:
        """선택된 항목 복사"""
        item = self._get_selected_item()
        if item:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(f"{item.original_text}\n\n{item.translated_text}")

    def _show_in_overlay(self) -> None:
        """선택된 항목을 오버레이에 표시"""
        item = self._get_selected_item()
        if item:
            self.overlay_update_requested.emit(item.original_text, item.translated_text)

    def _show_context_menu(self, pos) -> None:
        """컨텍스트 메뉴"""
        item = self._get_selected_item()
        if not item:
            return

        menu = QMenu(self)

        edit_action = QAction("편집", self)
        edit_action.triggered.connect(self._edit_selected)
        menu.addAction(edit_action)

        copy_action = QAction("복사", self)
        copy_action.triggered.connect(self._copy_selected)
        menu.addAction(copy_action)

        menu.addSeparator()

        overlay_action = QAction("오버레이에 표시", self)
        overlay_action.triggered.connect(self._show_in_overlay)
        menu.addAction(overlay_action)

        menu.addSeparator()

        delete_action = QAction("삭제", self)
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _export_history(self) -> None:
        """히스토리 내보내기"""
        from PyQt6.QtWidgets import QFileDialog
        import json

        path, _ = QFileDialog.getSaveFileName(
            self, "히스토리 내보내기",
            "history.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if path:
            data = []
            for item in self._items:
                data.append({
                    "id": item.id,
                    "original": item.original_text,
                    "translated": item.translated_text,
                    "source_language": item.source_language,
                    "target_language": item.target_language,
                    "timestamp": item.timestamp.isoformat(),
                    "is_edited": item.is_edited
                })

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


class HistoryEditorWindow(QWidget):
    """히스토리 에디터 독립 윈도우"""

    # 프록시 시그널
    translation_edited = pyqtSignal(int, str, str)
    glossary_added = pyqtSignal(str, str, str)
    overlay_update_requested = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("번역 히스토리")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._editor = HistoryEditor()
        layout.addWidget(self._editor)

        # 시그널 연결
        self._editor.translation_edited.connect(self.translation_edited.emit)
        self._editor.glossary_added.connect(self.glossary_added.emit)
        self._editor.overlay_update_requested.connect(self.overlay_update_requested.emit)

    @property
    def editor(self) -> HistoryEditor:
        return self._editor

    def add_entry(self, result: TranslationResult) -> None:
        """항목 추가 (편의 메서드)"""
        self._editor.add_entry(result)
