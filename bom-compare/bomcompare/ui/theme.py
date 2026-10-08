"""Temi chiaro/scuro: palette colori e foglio di stile Qt (QSS)."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from ..core.models import ADDED, MODIFIED, REMOVED, UNCHANGED


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str            # sfondo finestra
    surface: str       # pannelli/card
    surface_alt: str   # righe alternate / input
    border: str
    text: str
    text_muted: str
    accent: str
    accent_text: str
    status_bg: dict
    status_fg: dict
    changed_bg: str    # cella modificata (evidenza forte)
    absent_bg: str     # riga assente in una distinta
    warn_bg: str
    warn_fg: str
    slot_colors: tuple

    def qcolor(self, key: str) -> QColor:
        return QColor(getattr(self, key))


LIGHT = Theme(
    name="light",
    bg="#F3F4F6", surface="#FFFFFF", surface_alt="#F9FAFB", border="#E5E7EB",
    text="#111827", text_muted="#6B7280", accent="#2563EB", accent_text="#FFFFFF",
    status_bg={ADDED: "#DCFCE7", REMOVED: "#FEE2E2", MODIFIED: "#DBEAFE", UNCHANGED: "#FFFFFF"},
    status_fg={ADDED: "#166534", REMOVED: "#991B1B", MODIFIED: "#1E40AF", UNCHANGED: "#6B7280"},
    changed_bg="#BFDBFE", absent_bg="#F3F4F6", warn_bg="#FDE68A", warn_fg="#92400E",
    slot_colors=("#6B7280", "#2563EB", "#7C3AED", "#0D9488", "#C2410C", "#BE185D"),
)

DARK = Theme(
    name="dark",
    bg="#0F1115", surface="#171A21", surface_alt="#1D212A", border="#2A2F3A",
    text="#E5E7EB", text_muted="#9CA3AF", accent="#3B82F6", accent_text="#FFFFFF",
    status_bg={ADDED: "#12351F", REMOVED: "#3B1418", MODIFIED: "#172A4D", UNCHANGED: "#171A21"},
    status_fg={ADDED: "#86EFAC", REMOVED: "#FCA5A5", MODIFIED: "#93C5FD", UNCHANGED: "#9CA3AF"},
    changed_bg="#1E3A8A", absent_bg="#12141A", warn_bg="#78350F", warn_fg="#FDE68A",
    slot_colors=("#9CA3AF", "#60A5FA", "#A78BFA", "#2DD4BF", "#FB923C", "#F472B6"),
)

THEMES = {"light": LIGHT, "dark": DARK}


def get_theme(name: str) -> Theme:
    return THEMES.get(name, LIGHT)


def _arrow_rules(arrows: dict[str, str]) -> str:
    if not arrows:
        return ""
    down, up = arrows.get("chevron-down"), arrows.get("chevron-up")
    return f"""
    QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
                            width: 22px; border: none; }}
    QComboBox::down-arrow {{ image: url({down}); width: 10px; height: 10px; }}
    QAbstractSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
                                   width: 18px; border: none; }}
    QAbstractSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
                                     width: 18px; border: none; }}
    QAbstractSpinBox::up-arrow {{ image: url({up}); width: 8px; height: 8px; }}
    QAbstractSpinBox::down-arrow {{ image: url({down}); width: 8px; height: 8px; }}
    """


def build_stylesheet(t: Theme, arrows: dict[str, str] | None = None) -> str:
    return _arrow_rules(arrows or {}) + f"""
    QWidget {{ color: {t.text}; font-size: 10pt; }}
    QMainWindow, QDialog {{ background: {t.bg}; }}
    QToolBar {{ background: {t.surface}; border: none; border-bottom: 1px solid {t.border};
                spacing: 4px; padding: 4px 6px; }}
    QToolBar QToolButton {{ padding: 5px 8px; border-radius: 6px; }}
    QToolBar QToolButton:hover {{ background: {t.surface_alt}; }}
    QToolBar QToolButton:checked {{ background: {t.status_bg[MODIFIED]}; }}
    QMenuBar {{ background: {t.surface}; }}
    QMenuBar::item:selected, QMenu::item:selected {{ background: {t.accent}; color: {t.accent_text}; }}
    QMenu {{ background: {t.surface}; border: 1px solid {t.border}; }}
    QStatusBar {{ background: {t.surface}; border-top: 1px solid {t.border}; color: {t.text_muted}; }}
    QFrame#Card, QFrame#SlotCard, QFrame#StatCard {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 10px; }}
    QFrame#SlotCard[dragOver="true"] {{ border: 2px dashed {t.accent}; background: {t.surface_alt}; }}
    QFrame#SlotCard[empty="true"] {{ border: 2px dashed {t.border}; }}
    QLabel#Muted {{ color: {t.text_muted}; }}
    QLabel#Title {{ font-size: 13pt; font-weight: 600; }}
    QLabel#BigNumber {{ font-size: 22pt; font-weight: 700; }}
    QLabel#Chip {{ border-radius: 9px; padding: 2px 8px; font-weight: 600; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
        background: {t.surface}; border: 1px solid {t.border}; border-radius: 6px;
        padding: 4px 6px; selection-background-color: {t.accent}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {t.accent}; }}
    QLineEdit#RoleEdit {{ border: 1px solid transparent; background: transparent;
                         font-weight: 600; font-size: 11pt; padding: 2px; }}
    QLineEdit#RoleEdit:hover {{ border: 1px solid {t.border}; }}
    QLineEdit#RoleEdit:focus {{ border: 1px solid {t.accent}; background: {t.surface}; }}
    QComboBox QAbstractItemView {{ background: {t.surface}; border: 1px solid {t.border};
        selection-background-color: {t.accent}; selection-color: {t.accent_text}; }}
    QPushButton {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 6px;
                   padding: 5px 12px; }}
    QPushButton:hover {{ background: {t.surface_alt}; border-color: {t.accent}; }}
    QPushButton:disabled {{ color: {t.text_muted}; }}
    QPushButton#Primary {{ background: {t.accent}; color: {t.accent_text}; border: none;
                           font-weight: 600; padding: 6px 16px; }}
    QPushButton#Primary:hover {{ background: {t.accent}; border: none; }}
    QPushButton#Primary:disabled {{ background: {t.border}; color: {t.text_muted}; }}
    QPushButton#Filter {{ border-radius: 14px; padding: 4px 12px; }}
    QPushButton#Filter:checked {{ background: {t.accent}; color: {t.accent_text}; border-color: {t.accent}; }}
    QToolButton#Flat {{ border: none; padding: 3px; border-radius: 5px; }}
    QToolButton#Flat:hover {{ background: {t.surface_alt}; }}
    QTabWidget::pane {{ border: 1px solid {t.border}; border-radius: 8px; background: {t.surface};
                        top: -1px; }}
    QTabBar::tab {{ background: transparent; padding: 7px 14px; margin-right: 2px;
                    border-top-left-radius: 6px; border-top-right-radius: 6px; color: {t.text_muted}; }}
    QTabBar::tab:selected {{ background: {t.surface}; color: {t.text}; font-weight: 600;
                             border: 1px solid {t.border}; border-bottom: 2px solid {t.accent}; }}
    QTableView {{ background: {t.surface}; alternate-background-color: {t.surface_alt};
                  gridline-color: {t.border}; border: none;
                  selection-background-color: {t.accent}; selection-color: {t.accent_text}; }}
    QHeaderView::section {{ background: {t.surface_alt}; color: {t.text}; padding: 4px 6px;
                            border: none; border-right: 1px solid {t.border};
                            border-bottom: 1px solid {t.border}; font-weight: 600; }}
    QTableCornerButton::section {{ background: {t.surface_alt}; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
    QScrollBar::handle {{ background: {t.border}; border-radius: 5px; min-height: 24px; min-width: 24px; }}
    QScrollBar::handle:hover {{ background: {t.text_muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QProgressBar {{ border: 1px solid {t.border}; border-radius: 5px; background: {t.surface_alt};
                    text-align: center; height: 14px; }}
    QProgressBar::chunk {{ background: {t.accent}; border-radius: 4px; }}
    QSplitter::handle {{ background: {t.border}; }}
    QSplitter::handle:horizontal {{ width: 3px; }}
    QGroupBox {{ border: 1px solid {t.border}; border-radius: 8px; margin-top: 14px;
                 padding: 10px; background: {t.surface}; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; font-weight: 600; }}
    QToolTip {{ background: {t.surface}; color: {t.text}; border: 1px solid {t.border};
                padding: 5px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; }}
    QListWidget {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 6px; }}
    """


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Applica palette + QSS all'intera applicazione."""
    app.setStyle("Fusion")
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: theme.bg,
        QPalette.ColorRole.WindowText: theme.text,
        QPalette.ColorRole.Base: theme.surface,
        QPalette.ColorRole.AlternateBase: theme.surface_alt,
        QPalette.ColorRole.Text: theme.text,
        QPalette.ColorRole.Button: theme.surface,
        QPalette.ColorRole.ButtonText: theme.text,
        QPalette.ColorRole.Highlight: theme.accent,
        QPalette.ColorRole.HighlightedText: theme.accent_text,
        QPalette.ColorRole.ToolTipBase: theme.surface,
        QPalette.ColorRole.ToolTipText: theme.text,
        QPalette.ColorRole.PlaceholderText: theme.text_muted,
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(theme.text_muted))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,
                 QColor(theme.text_muted))
    app.setPalette(pal)
    from ..core.config import user_data_dir
    from .icons import arrow_images, set_default_color
    set_default_color(theme.text)
    arrows = arrow_images(theme.text_muted, user_data_dir() / "ui_cache")
    app.setStyleSheet(build_stylesheet(theme, arrows))
