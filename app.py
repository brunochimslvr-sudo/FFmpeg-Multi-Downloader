import os
import sys
import json
from urllib.parse import urlparse
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QMessageBox, QFrame, QMenu, QAbstractItemView, QButtonGroup,
    QStackedWidget, QSizePolicy, QCheckBox, QScrollArea, QSystemTrayIcon
)
from PyQt6.QtCore import Qt, QUrl, QSize, QByteArray, QProcess
from PyQt6.QtGui import QIcon, QFont, QCursor, QDesktopServices, QPixmap, QPainter, QPainterPath

from downloader_engine import (
    DownloadManager, DownloaderSignals, DownloadTask,
    FFMPEG_PATH, sanitize_filename, AUDIO_FORMATS, get_ytdlp_version
)

# Fila salva entre sessões (AppData, pois a pasta do programa pode não ter permissão de escrita)
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FFmpegDownloader")
QUEUE_FILE = os.path.join(APP_DATA_DIR, "fila.json")

# Paleta (mesma do mockup no Claude Design)
BG = "#0D0E11"
SURFACE = "#15171B"
SURFACE_2 = "#1F2127"
BORDER = "#22252C"
BORDER_INPUT = "#2A2D35"
TEXT = "#ECEDEF"
TEXT_SOFT = "#D5D8DE"
LABEL = "#A3A8B1"
MUTED = "#8E939D"
ACCENT = "#F5A524"
ACCENT_HOVER = "#FFB940"

# Status: (texto, fundo do selo, cor do texto, cor da barra)
STATUS_STYLES = {
    "queued": ("Na fila", SURFACE_2, "#B9BDC5", ACCENT),
    "downloading": ("Baixando", "#2B2213", "#F5B54A", ACCENT),
    "completed": ("Concluído", "#14261B", "#6EE7A0", "#4ADE80"),
    "error": ("Erro", "#2A1717", "#FCA5A5", "#F87171"),
    "cancelled": ("Cancelado", SURFACE_2, "#9CA3AF", "#4B5563"),
}

# Ícones de traço (estilo Lucide), coloridos em tempo de execução
ICONS = {
    "download": '<path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/>',
    "file": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "video": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9.5v5l4-2.5z"/>',
    "music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "play": '<path d="M7 4l13 8-13 8z" fill="currentColor"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "terminal": '<path d="M4 17l6-6-6-6"/><path d="M12 19h8"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "chevron": '<path d="M6 9l6 6 6-6"/>',
}


def make_icon(name, color=TEXT_SOFT, size=16, stroke=2.0):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size * 2}" height="{size * 2}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
        f'{ICONS[name].replace("currentColor", color)}</svg>'
    )
    pix = QPixmap()
    pix.loadFromData(QByteArray(svg.encode("utf-8")), "SVG")
    return QIcon(pix)


MODERN_STYLE = f"""
QMainWindow, QWidget#root {{
    background-color: {BG};
}}

QWidget {{
    color: {TEXT};
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    font-size: 13px;
}}

QLabel {{ background: transparent; }}

QFrame#header {{
    border-bottom: 1px solid {BORDER};
}}

QFrame#sidebar {{
    border-right: 1px solid {BORDER};
}}

QLabel#sectionLabel {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}}

QLabel#fieldLabel {{
    color: {LABEL};
    font-size: 12px;
}}

QLabel#counter {{
    color: {ACCENT};
    font-size: 12px;
    font-weight: 600;
}}

QLineEdit, QTextEdit, QSpinBox, QComboBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_INPUT};
    border-radius: 8px;
    padding: 0 10px;
    min-height: 34px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}

QTextEdit {{
    padding: 8px 10px;
    border-radius: 10px;
}}

QTextEdit#linksBox {{
    min-height: 120px;
    font-family: 'Cascadia Mono', Consolas, monospace;
    font-size: 12px;
}}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_INPUT};
    selection-background-color: {SURFACE_2};
    selection-color: {TEXT};
    color: {TEXT};
    outline: none;
    padding: 4px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 18px;
    border: none;
    background: transparent;
}}

QCheckBox {{
    color: {TEXT_SOFT};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {BORDER_INPUT};
    background-color: {SURFACE};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QPushButton {{
    background-color: transparent;
    color: {TEXT_SOFT};
    border: 1px solid {BORDER_INPUT};
    border-radius: 8px;
    padding: 0 14px;
    min-height: 34px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {SURFACE_2};
    color: {TEXT};
}}
QPushButton:pressed {{
    background-color: #262930;
}}
QPushButton:disabled {{
    color: #5B606A;
    border-color: {BORDER};
}}

QPushButton#btnAccent {{
    background-color: {ACCENT};
    color: {BG};
    border: none;
    border-radius: 10px;
    min-height: 44px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#btnAccent:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton#btnAccent:disabled {{ background-color: #3A3221; color: #7C6A45; }}

QPushButton#btnPrimary {{
    background-color: {TEXT};
    color: {BG};
    border: none;
    border-radius: 10px;
    min-height: 44px;
    padding: 0 22px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#btnPrimary:hover {{ background-color: #FFFFFF; }}
QPushButton#btnPrimary:disabled {{ background-color: #2A2D35; color: {MUTED}; }}

QPushButton#btnLarge {{
    min-height: 44px;
    border-radius: 10px;
    padding: 0 18px;
}}

QPushButton#btnGhost {{
    border: none;
    color: {MUTED};
}}
QPushButton#btnGhost:hover, QPushButton#btnGhost:checked {{
    color: {TEXT};
    background-color: {SURFACE_2};
}}

QPushButton#btnDashed {{
    border: 1px dashed {BORDER_INPUT};
    color: {LABEL};
    text-align: left;
    padding: 0 12px;
}}

QPushButton#btnIcon {{
    border: none;
    border-radius: 7px;
    padding: 0;
    min-height: 32px;
    min-width: 32px;
    max-width: 32px;
}}

QFrame#segmented {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_INPUT};
    border-radius: 10px;
}}
QFrame#segmented QPushButton {{
    border: none;
    border-radius: 7px;
    min-height: 30px;
    color: {MUTED};
}}
QFrame#segmented QPushButton:checked {{
    background-color: #262930;
    color: {TEXT};
    font-weight: 600;
}}

QTableWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    outline: none;
}}
QTableWidget::item {{
    border-bottom: 1px solid {BORDER};
    padding: 0;
}}
QTableWidget::item:selected {{
    background-color: #1C1E23;
}}

QProgressBar {{
    border: none;
    border-radius: 2px;
    background-color: #24272E;
    max-height: 4px;
    min-height: 4px;
}}
QProgressBar::chunk {{
    border-radius: 2px;
    background-color: {ACCENT};
}}

QLabel#emptyTitle {{ font-size: 15px; font-weight: 600; color: {TEXT_SOFT}; }}
QLabel#emptyText {{ color: {MUTED}; }}

QTextEdit#logBox {{
    background-color: #0A0B0E;
    border: 1px solid {BORDER};
    color: #B9BDC5;
    font-family: 'Cascadia Mono', Consolas, monospace;
    font-size: 11px;
}}

QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #2A2D35;
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{ background: #3A3E48; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QToolTip {{
    background-color: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER_INPUT};
    padding: 6px 8px;
}}

QMenu {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_INPUT};
    border-radius: 8px;
    color: {TEXT};
    padding: 4px;
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background-color: {SURFACE_2};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}
"""


def field_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("fieldLabel")
    return lbl


def labeled(text, widget):
    box = QVBoxLayout()
    box.setSpacing(6)
    box.addWidget(field_label(text))
    box.addWidget(widget)
    return box


def pill(text, bg, fg):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background-color: {bg}; color: {fg}; border-radius: 11px; padding: 0 10px; font-size: 12px;"
    )
    lbl.setFixedHeight(22)
    return lbl


class TaskRowWidget(QWidget):
    """Conteúdo visual de uma linha da fila: miniatura/ícone, nome, origem, progresso e info."""

    def __init__(self, task: DownloadTask):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 8, 10)
        layout.setSpacing(14)

        is_audio = task.fmt in AUDIO_FORMATS
        self.icon_box = QLabel()
        self.icon_box.setFixedSize(58, 40)
        self.icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_box.setStyleSheet(f"background-color: {SURFACE_2}; border-radius: 8px;")
        self.icon_box.setPixmap(make_icon("music" if is_audio else "video", LABEL, 18).pixmap(18, 18))
        layout.addWidget(self.icon_box)

        if getattr(task, "thumbnail_bytes", None):
            pix = QPixmap()
            if pix.loadFromData(task.thumbnail_bytes):
                self.set_thumbnail(pix)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.lbl_name = QLabel(task.get_output_filename())
        self.lbl_name.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.lbl_name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        host = urlparse(task.url).netloc or task.url[:40]
        self.lbl_host = QLabel(host)
        self.lbl_host.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        title_row.addWidget(self.lbl_name, 1)
        title_row.addWidget(self.lbl_host)
        text_col.addLayout(title_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        text_col.addWidget(self.progress)

        self.lbl_info = QLabel("Na fila...")
        self.lbl_info.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-family: 'Cascadia Mono', Consolas, monospace;")
        text_col.addWidget(self.lbl_info)

        layout.addLayout(text_col, 1)

    def set_thumbnail(self, pixmap: QPixmap):
        if not pixmap or pixmap.isNull():
            return
        target_w, target_h = 58, 40
        rounded = QPixmap(target_w, target_h)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(0, 0, target_w, target_h, 7, 7)
        painter.setClipPath(path)
        scaled = pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        x_offset = (scaled.width() - target_w) // 2
        y_offset = (scaled.height() - target_h) // 2
        painter.drawPixmap(-x_offset, -y_offset, scaled)
        painter.end()
        self.icon_box.setPixmap(rounded)

    def set_bar_color(self, color):
        self.progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Video Downloader")
        base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(make_icon("download", ACCENT, 32, 2.4))
        self.resize(1280, 800)
        self.setMinimumSize(1000, 640)
        self.setStyleSheet(MODERN_STYLE)

        self.signals = DownloaderSignals()
        self.manager = DownloadManager(self.signals)
        self.custom_cookie_file = ""
        self._last_clipboard_url = ""

        # Notificação nativa na bandeja do Windows (System Tray Toast)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setToolTip("Multi-Video Downloader")
        self.tray_icon.messageClicked.connect(self.open_downloads_folder)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

        # Mapeamento de id da tarefa para linha da tabela e widgets da linha
        self.task_row_map = {}
        self.task_widgets = {}

        self.init_ui()
        self.connect_signals()
        self.update_format_and_quality(is_music=False)
        self.update_links_counter()
        self.update_queue_stats()
        self.load_saved_queue()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("root")
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self.build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.build_sidebar())
        body.addWidget(self.build_queue_panel(), 1)
        root_layout.addLayout(body, 1)

    def build_header(self):
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(60)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(14)

        logo = QLabel()
        logo.setFixedSize(32, 32)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"background-color: {ACCENT}; border-radius: 8px;")
        logo.setPixmap(make_icon("download", BG, 18, 2.4).pixmap(18, 18))
        layout.addWidget(logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("Multi-Video Downloader")
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        subtitle = QLabel("m3u8, mp4, YouTube e playlists em lote")
        subtitle.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        layout.addStretch()

        # O motor usa o pacote Python yt_dlp (não o bin/yt-dlp.exe), então o selo mostra a versão dele
        ytdlp_version = get_ytdlp_version()
        badges = (
            ("FFmpeg", os.path.exists(FFMPEG_PATH), f"Caminho: {FFMPEG_PATH}"),
            (f"yt-dlp {ytdlp_version}".strip(), bool(ytdlp_version), "Pacote Python yt-dlp usado pelo motor"),
        )
        for name, ok, tip in badges:
            badge = QLabel(f"<span style='color:{'#4ADE80' if ok else '#F87171'}'>●</span>&nbsp; {name}"
                           f"{'' if ok else ' ausente'}")
            badge.setTextFormat(Qt.TextFormat.RichText)
            badge.setStyleSheet(
                f"border: 1px solid {BORDER}; border-radius: 13px; padding: 0 11px; "
                f"font-size: 11px; color: {'#B9BDC5' if ok else '#FCA5A5'};"
            )
            badge.setFixedHeight(26)
            badge.setToolTip(tip)
            layout.addWidget(badge)

        self.btn_update_ytdlp = QPushButton("Atualizar")
        self.btn_update_ytdlp.setObjectName("btnGhost")
        self.btn_update_ytdlp.setStyleSheet("min-height: 26px; padding: 0 10px; font-size: 11px; border-radius: 13px;")
        self.btn_update_ytdlp.setToolTip(
            "Atualiza o yt-dlp (e instala o mutagen, usado para pôr capa em FLAC e OPUS).\n"
            "Quando o YouTube ou outro site para de funcionar, quase sempre é isso que resolve."
        )
        self.btn_update_ytdlp.clicked.connect(self.update_ytdlp)
        if getattr(sys, 'frozen', False):
            self.btn_update_ytdlp.setEnabled(False)
            self.btn_update_ytdlp.setToolTip("Na versão instalada, o yt-dlp é atualizado junto com o instalador.")
        layout.addWidget(self.btn_update_ytdlp)

        return header

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(380)
        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)

        # Conteúdo rolável: em telas baixas (ou com Headers abertos) os campos não se sobrepõem
        content = QWidget()
        content.setObjectName("sidebarContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 20, 20)
        layout.setSpacing(14)

        # Links
        top = QHBoxLayout()
        lbl_section = QLabel("ADICIONAR LINKS")
        lbl_section.setObjectName("sectionLabel")
        self.lbl_counter = QLabel("0 links")
        self.lbl_counter.setObjectName("counter")
        top.addWidget(lbl_section)
        top.addStretch()
        top.addWidget(self.lbl_counter)
        layout.addLayout(top)

        self.txt_links = QTextEdit()
        self.txt_links.setObjectName("linksBox")
        self.txt_links.setAcceptRichText(False)
        self.txt_links.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt_links.setPlaceholderText("Um link por linha. Use  link | Nome  para nomear.")
        self.txt_links.textChanged.connect(self.update_links_counter)
        self.txt_links.setMinimumHeight(120)
        layout.addWidget(self.txt_links, 1)

        link_actions = QHBoxLayout()
        link_actions.setSpacing(8)
        btn_import_txt = QPushButton("Importar .txt")
        btn_import_txt.setIcon(make_icon("file"))
        btn_import_txt.clicked.connect(self.import_from_txt)
        btn_clear_text = QPushButton("Limpar")
        btn_clear_text.clicked.connect(self.txt_links.clear)
        link_actions.addWidget(btn_import_txt, 1)
        link_actions.addWidget(btn_clear_text)
        layout.addLayout(link_actions)

        # Seletor Vídeo / Música (controle segmentado)
        segmented = QFrame()
        segmented.setObjectName("segmented")
        seg_layout = QHBoxLayout(segmented)
        seg_layout.setContentsMargins(3, 3, 3, 3)
        seg_layout.setSpacing(0)
        self.rb_video = QPushButton("Vídeo")
        self.rb_audio = QPushButton("Música")
        for btn in (self.rb_video, self.rb_audio):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            seg_layout.addWidget(btn, 1)
        self.rb_video.setChecked(True)
        self.type_group = QButtonGroup(self)
        self.type_group.setExclusive(True)
        self.type_group.addButton(self.rb_video)
        self.type_group.addButton(self.rb_audio)
        layout.addLayout(labeled("Baixar como", segmented))

        # Grade de opções
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.cmb_fmt = QComboBox()
        self.cmb_quality = QComboBox()
        self.cmb_quality.setToolTip("Qualidade do vídeo ou áudio")

        self.edt_prefix = QLineEdit()
        self.edt_prefix.setPlaceholderText("Ex: Aula_")
        self.edt_prefix.setToolTip("Links sem nome viram Prefixo01, Prefixo02...")

        self.cmb_engine = QComboBox()
        self.cmb_engine.addItem("Automático", "auto")
        self.cmb_engine.addItem("FFmpeg direto", "ffmpeg")
        self.cmb_engine.addItem("yt-dlp", "ytdlp")
        self.cmb_engine.setItemData(0, "Escolhe o melhor motor para cada link", Qt.ItemDataRole.ToolTipRole)
        self.cmb_engine.setItemData(1, "Cópia ultrarrápida de stream (m3u8 / mp4)", Qt.ItemDataRole.ToolTipRole)
        self.cmb_engine.setItemData(2, "YouTube, SoundCloud, Bandcamp e sites em geral", Qt.ItemDataRole.ToolTipRole)

        self.spn_concurrent = QSpinBox()
        self.spn_concurrent.setRange(1, 6)
        self.spn_concurrent.setValue(2)
        self.spn_concurrent.valueChanged.connect(self.update_max_concurrent)

        grid.addLayout(labeled("Formato", self.cmb_fmt), 0, 0)
        grid.addLayout(labeled("Qualidade", self.cmb_quality), 0, 1)
        grid.addLayout(labeled("Prefixo", self.edt_prefix), 1, 0)
        grid.addLayout(labeled("Simultâneos", self.spn_concurrent), 1, 1)
        grid.addLayout(labeled("Motor", self.cmb_engine), 2, 0, 1, 2)
        layout.addLayout(grid)

        # Opção de Título Original
        self.chk_auto_title = QCheckBox("Salvar com nome original da música / vídeo")
        self.chk_auto_title.setChecked(True)
        self.chk_auto_title.setToolTip("Identifica e nomeia automaticamente com o nome da música ou vídeo no YouTube, YouTube Music, SoundCloud, Bandcamp, etc.")
        layout.addWidget(self.chk_auto_title)

        # Automação de Playlists e Clipboard
        self.chk_expand_playlist = QCheckBox("Desmembrar playlists em vídeos individuais")
        self.chk_expand_playlist.setChecked(True)
        self.chk_expand_playlist.setToolTip("Ao colar o link de uma playlist do YouTube, divide cada vídeo em uma tarefa individual na fila.")
        layout.addWidget(self.chk_expand_playlist)

        self.chk_clipboard = QCheckBox("📋 Monitorar Copiar/Colar (Ctrl+C)")
        self.chk_clipboard.setToolTip("Detecta quando você copia um link no navegador e já adiciona automaticamente na caixa de texto!")
        layout.addWidget(self.chk_clipboard)

        # Pasta de destino
        dest_row = QHBoxLayout()
        dest_row.setSpacing(8)
        user_dl = os.path.join(os.path.expanduser("~"), "Downloads")
        default_dir = user_dl if os.path.exists(user_dl) else os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")
        self.edt_dest = QLineEdit(default_dir)
        self.edt_dest.setStyleSheet("font-size: 12px;")
        btn_browse = QPushButton()
        btn_browse.setObjectName("btnIcon")
        btn_browse.setStyleSheet(f"border: 1px solid {BORDER_INPUT}; min-height: 34px; min-width: 36px; max-width: 36px;")
        btn_browse.setIcon(make_icon("folder"))
        btn_browse.setToolTip("Procurar pasta")
        btn_browse.clicked.connect(self.browse_folder)
        dest_row.addWidget(self.edt_dest, 1)
        dest_row.addWidget(btn_browse)
        dest_box = QVBoxLayout()
        dest_box.setSpacing(6)
        dest_box.addWidget(field_label("Salvar em"))
        dest_box.addLayout(dest_row)
        layout.addLayout(dest_box)

        # Cookies do Navegador / Autenticação
        self.cmb_cookies = QComboBox()
        self.cmb_cookies.addItem("Nenhum (Sem login)", "none")
        self.cmb_cookies.addItem("🌐 Google Chrome (Sessão ativa)", "chrome")
        self.cmb_cookies.addItem("🌐 Microsoft Edge (Sessão ativa)", "edge")
        self.cmb_cookies.addItem("🦊 Mozilla Firefox (Sessão ativa)", "firefox")
        self.cmb_cookies.addItem("🦁 Brave (Sessão ativa)", "brave")
        self.cmb_cookies.addItem("📁 Importar cookies.txt...", "file")
        self.cmb_cookies.setToolTip("Permite baixar de sites onde você já está logado no navegador sem digitar senha!")
        self.cmb_cookies.currentIndexChanged.connect(self.on_cookies_changed)
        layout.addLayout(labeled("Login / Cookies do Navegador", self.cmb_cookies))

        # Headers HTTP (recolhível)
        self.btn_toggle_headers = QPushButton("Headers HTTP (Referer, User-Agent)")
        self.btn_toggle_headers.setObjectName("btnDashed")
        self.btn_toggle_headers.setCheckable(True)
        self.btn_toggle_headers.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_toggle_headers.setIcon(make_icon("plus", MUTED, 14))
        self.btn_toggle_headers.toggled.connect(self.toggle_headers)
        layout.addWidget(self.btn_toggle_headers)

        self.txt_headers = QTextEdit()
        self.txt_headers.setAcceptRichText(False)
        self.txt_headers.setPlaceholderText(
            "Para cursos protegidos:\n"
            "Referer: https://plataforma.com/\n"
            "User-Agent: Mozilla/5.0 ..."
        )
        self.txt_headers.setFixedHeight(84)
        self.txt_headers.setStyleSheet("font-family: 'Cascadia Mono', Consolas, monospace; font-size: 11px;")
        self.txt_headers.setVisible(False)
        layout.addWidget(self.txt_headers)

        # Legendas (recolhível)
        self.btn_toggle_subtitles = QPushButton("Legendas (.srt / Embutidas)")
        self.btn_toggle_subtitles.setObjectName("btnDashed")
        self.btn_toggle_subtitles.setCheckable(True)
        self.btn_toggle_subtitles.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_toggle_subtitles.setIcon(make_icon("plus", MUTED, 14))
        self.btn_toggle_subtitles.toggled.connect(self.toggle_subtitles)
        layout.addWidget(self.btn_toggle_subtitles)

        self.box_subtitles = QWidget()
        box_sub_layout = QVBoxLayout(self.box_subtitles)
        box_sub_layout.setContentsMargins(0, 4, 0, 4)
        box_sub_layout.setSpacing(8)

        self.chk_subtitles = QCheckBox("Baixar legendas disponíveis")
        self.chk_subtitles.setToolTip("Baixa legendas oficiais e geradas automaticamente (auto-subs do YouTube)")
        box_sub_layout.addWidget(self.chk_subtitles)

        sub_grid = QGridLayout()
        sub_grid.setSpacing(8)
        self.cmb_sub_lang = QComboBox()
        self.cmb_sub_lang.addItem("🇧🇷 Português (pt)", "pt")
        self.cmb_sub_lang.addItem("🇺🇸 Inglês (en)", "en")
        self.cmb_sub_lang.addItem("🌐 Todos os idiomas", "all")
        
        self.cmb_sub_type = QComboBox()
        self.cmb_sub_type.addItem("📁 Arquivo .srt separado", "srt")
        self.cmb_sub_type.addItem("🎬 Embutir dentro do vídeo", "embed")
        
        sub_grid.addLayout(labeled("Idioma", self.cmb_sub_lang), 0, 0)
        sub_grid.addLayout(labeled("Entrega", self.cmb_sub_type), 0, 1)
        box_sub_layout.addLayout(sub_grid)

        self.box_subtitles.setVisible(False)
        layout.addWidget(self.box_subtitles)

        layout.addSpacing(4)
        self.btn_add_batch = QPushButton("Adicionar à fila")
        self.btn_add_batch.setObjectName("btnAccent")
        self.btn_add_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_batch.clicked.connect(self.add_batch_links)
        layout.addWidget(self.btn_add_batch)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea, QWidget#sidebarContent {{ background: {BG}; border: none; }}")
        scroll.setWidget(content)
        outer.addWidget(scroll)

        return sidebar

    def build_queue_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Cabeçalho da fila
        head = QHBoxLayout()
        head.setSpacing(8)
        lbl_queue_title = QLabel("Fila")
        lbl_queue_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        head.addWidget(lbl_queue_title)
        head.addSpacing(6)

        self.pill_total = pill("0 total", "#1B1D22", "#B9BDC5")
        self.pill_down = pill("", "#2B2213", "#F5B54A")
        self.pill_queued = pill("", SURFACE_2, "#B9BDC5")
        self.pill_done = pill("", "#14261B", "#6EE7A0")
        self.pill_err = pill("", "#2A1717", "#FCA5A5")
        for p in (self.pill_total, self.pill_down, self.pill_queued, self.pill_done, self.pill_err):
            head.addWidget(p)
        head.addStretch()

        self.btn_clear_done = QPushButton("Limpar concluídos")
        self.btn_clear_done.clicked.connect(self.clear_completed)
        self.btn_clear_all = QPushButton("Limpar tudo")
        self.btn_clear_all.clicked.connect(self.clear_all_tasks)
        btn_open_folder = QPushButton("Abrir pasta")
        btn_open_folder.setIcon(make_icon("folder"))
        btn_open_folder.clicked.connect(self.open_downloads_folder)
        head.addWidget(self.btn_clear_done)
        head.addWidget(self.btn_clear_all)
        head.addWidget(btn_open_folder)
        layout.addLayout(head)

        # Tabela (ou estado vazio)
        self.queue_stack = QStackedWidget()

        empty = QFrame()
        empty.setStyleSheet(f"QFrame {{ border: 1px dashed {BORDER_INPUT}; border-radius: 12px; }}")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)
        empty_icon = QLabel()
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon.setStyleSheet("border: none;")
        empty_icon.setPixmap(make_icon("download", "#3A3E48", 40, 1.6).pixmap(40, 40))
        empty_title = QLabel("A fila está vazia")
        empty_title.setObjectName("emptyTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title.setStyleSheet("border: none;")
        empty_text = QLabel("Cole os links à esquerda e clique em “Adicionar à fila”.")
        empty_text.setObjectName("emptyText")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet("border: none;")
        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_text)
        self.queue_stack.addWidget(empty)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 112)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 84)
        self.table.verticalHeader().setDefaultSectionSize(74)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.queue_stack.addWidget(self.table)

        layout.addWidget(self.queue_stack, 1)

        # Barra de controles globais
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_start = QPushButton("Iniciar fila")
        self.btn_start.setObjectName("btnPrimary")
        self.btn_start.setIcon(make_icon("play", BG, 14))
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_queue)

        self.btn_pause = QPushButton("Pausar")
        self.btn_pause.setObjectName("btnLarge")
        self.btn_pause.setIcon(make_icon("pause", TEXT_SOFT, 14))
        self.btn_pause.setToolTip("Para de iniciar novos downloads; os que estão em andamento terminam.")
        self.btn_pause.clicked.connect(self.pause_queue)

        self.btn_toggle_logs = QPushButton("Logs")
        self.btn_toggle_logs.setObjectName("btnGhost")
        self.btn_toggle_logs.setStyleSheet("min-height: 44px; border-radius: 10px; padding: 0 16px;")
        self.btn_toggle_logs.setIcon(make_icon("terminal", MUTED))
        self.btn_toggle_logs.setCheckable(True)
        self.btn_toggle_logs.toggled.connect(self.toggle_log_drawer)

        bottom_bar.addWidget(self.btn_start)
        bottom_bar.addWidget(self.btn_pause)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_toggle_logs)
        layout.addLayout(bottom_bar)

        # Painel de logs (recolhível)
        self.log_widget = QWidget()
        layout_log = QVBoxLayout(self.log_widget)
        layout_log.setContentsMargins(0, 0, 0, 0)
        layout_log.setSpacing(6)

        log_top = QHBoxLayout()
        lbl_log = QLabel("SAÍDA E DIAGNÓSTICO")
        lbl_log.setObjectName("sectionLabel")
        btn_copy_log = QPushButton("Copiar")
        btn_copy_log.setObjectName("btnGhost")
        btn_copy_log.clicked.connect(self.copy_logs)
        btn_clear_log = QPushButton("Limpar")
        btn_clear_log.setObjectName("btnGhost")
        btn_clear_log.clicked.connect(self.clear_logs)
        log_top.addWidget(lbl_log)
        log_top.addStretch()
        log_top.addWidget(btn_copy_log)
        log_top.addWidget(btn_clear_log)
        layout_log.addLayout(log_top)

        self.txt_logs = QTextEdit()
        self.txt_logs.setObjectName("logBox")
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setFixedHeight(150)
        layout_log.addWidget(self.txt_logs)

        self.log_widget.setVisible(False)
        layout.addWidget(self.log_widget)

        return panel

    def connect_signals(self):
        self.signals.status_changed.connect(self.on_status_changed)
        self.signals.progress_changed.connect(self.on_progress_changed)
        self.signals.title_updated.connect(self.on_title_updated)
        self.signals.thumbnail_loaded.connect(self.on_thumbnail_loaded)
        self.signals.tasks_replaced.connect(self.on_tasks_replaced)
        self.signals.log_received.connect(self.on_log_received)
        self.signals.task_finished.connect(self.on_task_finished)
        self.signals.all_finished.connect(self.on_all_finished)

        QApplication.clipboard().dataChanged.connect(self.on_clipboard_changed)

        # Sincronização entre seletor de Vídeo/Música, Formato e Qualidade
        self.rb_video.toggled.connect(self.on_type_radio_toggled)
        self.cmb_fmt.currentIndexChanged.connect(self.on_cmb_fmt_changed)

    def update_format_and_quality(self, is_music: bool):
        self.cmb_fmt.blockSignals(True)
        self.cmb_fmt.clear()
        if is_music:
            self.cmb_fmt.addItem("MP3 (.mp3)", "mp3")
            self.cmb_fmt.addItem("M4A (.m4a - AAC)", "m4a")
            self.cmb_fmt.addItem("OPUS (.opus - original do YouTube)", "opus")
            self.cmb_fmt.addItem("FLAC (.flac - Sem perdas)", "flac")
            self.cmb_fmt.addItem("WAV (.wav - Sem compressão)", "wav")
            lossless_note = ("Só tem qualidade maior se a fonte for sem perdas (ex.: Bandcamp).\n"
                             "Vindo do YouTube/SoundCloud, o arquivo fica maior mas soa igual.")
            self.cmb_fmt.setItemData(2, "Mesmo áudio que o YouTube entrega, sem reconversão: melhor qualidade por MB.", Qt.ItemDataRole.ToolTipRole)
            self.cmb_fmt.setItemData(3, lossless_note, Qt.ItemDataRole.ToolTipRole)
            self.cmb_fmt.setItemData(4, lossless_note, Qt.ItemDataRole.ToolTipRole)
        else:
            self.cmb_fmt.addItem("MP4 (.mp4)", "mp4")
            self.cmb_fmt.addItem("MKV (.mkv)", "mkv")
            self.cmb_fmt.addItem("TS (.ts)", "ts")
        self.cmb_fmt.blockSignals(False)
        self.update_quality_options()

    def update_quality_options(self):
        self.cmb_quality.blockSignals(True)
        self.cmb_quality.clear()
        
        current_fmt = self.cmb_fmt.currentData() or ("mp3" if self.rb_audio.isChecked() else "mp4")
        
        if current_fmt == "mp3":
            self.cmb_quality.addItem("320 kbps (Máxima)", "320")
            self.cmb_quality.addItem("256 kbps (Alta)", "256")
            self.cmb_quality.addItem("192 kbps (Padrão)", "192")
            self.cmb_quality.addItem("128 kbps (Econômica)", "128")
        elif current_fmt == "flac":
            self.cmb_quality.addItem("Lossless / Sem perdas (Original)", "flac")
        elif current_fmt == "wav":
            self.cmb_quality.addItem("PCM Sem compressão (Original)", "wav")
        elif current_fmt == "opus":
            self.cmb_quality.addItem("Original (sem reconversão)", "best")
        elif current_fmt == "m4a":
            self.cmb_quality.addItem("Melhor Qualidade AAC", "best")
            self.cmb_quality.addItem("256 kbps", "256")
            self.cmb_quality.addItem("128 kbps", "128")
        else:
            self.cmb_quality.addItem("Melhor Qualidade (Auto)", "best")
            self.cmb_quality.addItem("1080p (Full HD)", "1080")
            self.cmb_quality.addItem("720p (HD)", "720")
            self.cmb_quality.addItem("480p (SD)", "480")
            self.cmb_quality.addItem("360p (Econômico)", "360")
            
        self.cmb_quality.blockSignals(False)

    def on_type_radio_toggled(self, checked):
        if self.rb_audio.isChecked():
            self.update_format_and_quality(is_music=True)
        elif self.rb_video.isChecked():
            self.update_format_and_quality(is_music=False)

    def on_cmb_fmt_changed(self):
        fmt = self.cmb_fmt.currentData()
        if not fmt:
            return
        is_audio = fmt in AUDIO_FORMATS
        self.rb_video.blockSignals(True)
        self.rb_audio.blockSignals(True)
        if is_audio:
            self.rb_audio.setChecked(True)
        else:
            self.rb_video.setChecked(True)
        self.rb_video.blockSignals(False)
        self.rb_audio.blockSignals(False)
        self.update_quality_options()

    def on_title_updated(self, task_id, new_title):
        w = self.task_widgets.get(task_id)
        if w and "row" in w:
            w["row"].lbl_name.setText(new_title)
            w["row"].lbl_name.setToolTip(new_title)

    def on_thumbnail_loaded(self, task_id, thumb_bytes):
        w = self.task_widgets.get(task_id)
        if w and "row" in w:
            pix = QPixmap()
            if pix.loadFromData(thumb_bytes):
                w["row"].set_thumbnail(pix)

    def on_clipboard_changed(self):
        if not hasattr(self, "chk_clipboard") or not self.chk_clipboard.isChecked():
            return
        text = QApplication.clipboard().text().strip()
        if not text or text == getattr(self, "_last_clipboard_url", ""):
            return
        if text.startswith("http://") or text.startswith("https://"):
            media_domains = ("youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", 
                             "twitch.tv", "soundcloud.com", "bandcamp.com", "facebook.com", 
                             "instagram.com", "tiktok.com", "twitter.com", "x.com", 
                             ".m3u8", ".mpd", ".mp4")
            if any(d in text.lower() for d in media_domains) or text.lower().endswith((".m3u8", ".mp4", ".mp3")):
                self._last_clipboard_url = text
                current = self.txt_links.toPlainText()
                if text not in current:
                    if current.strip():
                        self.txt_links.setPlainText(current + "\n" + text)
                    else:
                        self.txt_links.setPlainText(text)
                    self.append_log(f"📋 Link detectado da área de transferência: {text}")

    def on_tasks_replaced(self, task_id, count):
        # Uma playlist virou vários itens na fila
        self.rebuild_table()
        self.update_queue_stats()

    def update_ytdlp(self):
        self.btn_update_ytdlp.setEnabled(False)
        self.btn_update_ytdlp.setText("Atualizando...")
        if not self.btn_toggle_logs.isChecked():
            self.btn_toggle_logs.setChecked(True)
        self.append_log("Atualizando yt-dlp e mutagen...")

        self.update_process = QProcess(self)
        self.update_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.update_process.readyReadStandardOutput.connect(
            lambda: self.append_log(bytes(self.update_process.readAllStandardOutput()).decode("utf-8", "replace").rstrip())
        )
        self.update_process.finished.connect(self.on_ytdlp_updated)
        self.update_process.start(sys.executable, ["-m", "pip", "install", "-U", "--disable-pip-version-check", "yt-dlp", "mutagen"])

    def on_ytdlp_updated(self, exit_code, _status):
        self.btn_update_ytdlp.setEnabled(True)
        self.btn_update_ytdlp.setText("Atualizar")
        if exit_code == 0:
            self.append_log("Atualização concluída. Feche e abra o programa para usar a nova versão.")
            QMessageBox.information(self, "yt-dlp atualizado",
                                    "Atualização concluída.\nFeche e abra o programa para usar a nova versão.")
        else:
            self.append_log(f"Falha ao atualizar (código {exit_code}). Veja os detalhes acima.")
            QMessageBox.warning(self, "Falha na atualização", "Não foi possível atualizar o yt-dlp. Veja os detalhes nos Logs.")

    def save_queue(self):
        pending = [t.to_dict() for t in self.manager.tasks if t.status in ("queued", "downloading", "error")]
        try:
            if pending:
                os.makedirs(APP_DATA_DIR, exist_ok=True)
                with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                    json.dump(pending, f, ensure_ascii=False, indent=1)
            elif os.path.exists(QUEUE_FILE):
                os.remove(QUEUE_FILE)
        except Exception:
            pass

    def load_saved_queue(self):
        if not os.path.exists(QUEUE_FILE):
            return
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            return
        for data in saved:
            if data.get("url"):
                self.add_task_to_table(self.manager.restore_task(data))
        if saved:
            self.append_log(f"{len(saved)} item(ns) restaurado(s) da sessão anterior. Clique em Iniciar fila para continuar.")
        self.update_queue_stats()

    def closeEvent(self, event):
        running = sum(1 for t in self.manager.tasks if t.status == "downloading")
        if running:
            confirm = QMessageBox.question(
                self, "Downloads em andamento",
                f"{running} download(s) em andamento serão interrompidos.\n"
                "Eles ficam salvos e recomeçam quando você abrir o programa de novo.\n\nFechar mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.save_queue()
        # Encerra processos do FFmpeg que continuariam rodando depois do programa fechar
        for task in self.manager.tasks:
            if task.status == "downloading":
                task.is_cancelled = True
                if task.process:
                    try:
                        task.process.kill()
                    except Exception:
                        pass
        event.accept()

    def toggle_headers(self, checked):
        self.txt_headers.setVisible(checked)
        self.btn_toggle_headers.setIcon(make_icon("chevron" if checked else "plus", MUTED, 14))

    def toggle_subtitles(self, checked):
        self.box_subtitles.setVisible(checked)
        self.btn_toggle_subtitles.setIcon(make_icon("chevron" if checked else "plus", MUTED, 14))

    def parse_link_lines(self):
        text = self.txt_links.toPlainText()
        return [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('#')]

    def update_links_counter(self):
        count = len(self.parse_link_lines())
        self.lbl_counter.setText(f"{count} link{'s' if count != 1 else ''}")
        self.btn_add_batch.setEnabled(count > 0)
        self.btn_add_batch.setText(f"Adicionar {count} à fila" if count else "Adicionar à fila")

    def update_max_concurrent(self, val):
        self.manager.max_concurrent = val

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Salvar", self.edt_dest.text())
        if folder:
            self.edt_dest.setText(folder)

    def open_downloads_folder(self):
        folder = self.edt_dest.text()
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def import_from_txt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo de Links", "", "Arquivos de Texto (*.txt);;Todos (*.*)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                current_text = self.txt_links.toPlainText()
                if current_text.strip():
                    self.txt_links.setPlainText(current_text + "\n" + content)
                else:
                    self.txt_links.setPlainText(content)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao carregar arquivo", str(e))

    def on_cookies_changed(self):
        choice = self.cmb_cookies.currentData()
        if choice == "file":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Selecionar arquivo cookies.txt exportado",
                "",
                "Cookies Netscape (*.txt);;Todos (*.*)"
            )
            if file_path:
                self.custom_cookie_file = file_path
                self.cmb_cookies.setItemText(5, f"📁 {os.path.basename(file_path)}")
                self.append_log(f"Arquivo de cookies carregado: {file_path}")
            else:
                self.custom_cookie_file = ""
                self.cmb_cookies.blockSignals(True)
                self.cmb_cookies.setCurrentIndex(0)
                self.cmb_cookies.blockSignals(False)
        else:
            self.custom_cookie_file = ""
            self.cmb_cookies.setItemText(5, "📁 Importar cookies.txt...")
            if choice and choice != "none":
                self.append_log(f"Sessão do navegador ativada: {choice.title()}")

    def add_batch_links(self):
        lines = self.parse_link_lines()
        if not lines:
            QMessageBox.information(self, "Aviso", "Por favor, cole ao menos um link na caixa de texto.")
            return

        prefix = self.edt_prefix.text().strip()
        dest_dir = self.edt_dest.text().strip()
        engine = self.cmb_engine.currentData()
        fmt = self.cmb_fmt.currentData() or ("mp3" if self.rb_audio.isChecked() else "mp4")
        quality = self.cmb_quality.currentData() or "best"
        use_auto_title = self.chk_auto_title.isChecked()
        headers = self.txt_headers.toPlainText().strip()
        
        cookie_choice = self.cmb_cookies.currentData()
        browser_cookies = self.custom_cookie_file if cookie_choice == "file" else cookie_choice

        download_subtitles = getattr(self, "chk_subtitles", None) and self.chk_subtitles.isChecked()
        sub_lang = self.cmb_sub_lang.currentData() if hasattr(self, "cmb_sub_lang") else "pt"
        sub_embed = (self.cmb_sub_type.currentData() == "embed") if hasattr(self, "cmb_sub_type") else False
        expand_playlist = getattr(self, "chk_expand_playlist", None) and self.chk_expand_playlist.isChecked()

        count_added = 0
        for i, line in enumerate(lines, 1):
            # Formatos suportados:
            # 1. URL | Nome
            # 2. URL (usa prefixo se tiver)
            url = line
            custom_name = ""
            if " | " in line:
                parts = line.split(" | ", 1)
                url = parts[0].strip()
                custom_name = parts[1].strip()
            elif "\t" in line:
                parts = line.split("\t", 1)
                url = parts[0].strip()
                custom_name = parts[1].strip()
            elif " ; " in line:
                parts = line.split(" ; ", 1)
                url = parts[0].strip()
                custom_name = parts[1].strip()

            if not custom_name and prefix:
                custom_name = f"{prefix}{i:02d}"

            task = self.manager.add_task(
                url=url,
                filename=custom_name,
                output_dir=dest_dir,
                engine=engine,
                fmt=fmt,
                headers=headers,
                quality=quality,
                use_auto_title=use_auto_title and not custom_name,
                browser_cookies=browser_cookies,
                download_subtitles=download_subtitles,
                sub_lang=sub_lang,
                sub_embed=sub_embed,
                expand_playlist=expand_playlist
            )
            self.add_task_to_table(task)
            count_added += 1

        self.txt_links.clear()
        self.update_queue_stats()
        self.append_log(f"{count_added} tarefa(s) adicionada(s) à fila.")

    def add_task_to_table(self, task: DownloadTask):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.task_row_map[task.task_id] = row

        # Coluna 0: nome, origem, progresso e info
        base_item = QTableWidgetItem()
        is_audio = task.fmt in AUDIO_FORMATS
        tipo_desc = f"Música ({task.fmt.upper()})" if is_audio else f"Vídeo ({task.fmt.upper()})"
        base_item.setToolTip(f"#{task.task_id} · {task.get_output_filename()}\nTipo: {tipo_desc}\nURL: {task.url}")
        self.table.setItem(row, 0, base_item)
        row_widget = TaskRowWidget(task)
        row_widget.setToolTip(base_item.toolTip())
        self.table.setCellWidget(row, 0, row_widget)
        self.table.setItem(row, 1, QTableWidgetItem())
        self.table.setItem(row, 2, QTableWidgetItem())

        # Coluna 1: selo de status
        status_holder = QWidget()
        status_holder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sh_layout = QHBoxLayout(status_holder)
        sh_layout.setContentsMargins(4, 0, 4, 0)
        status_lbl = QLabel()
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_lbl.setFixedSize(96, 24)
        sh_layout.addWidget(status_lbl)
        self.table.setCellWidget(row, 1, status_holder)

        # Coluna 2: ações
        actions_widget = QWidget()
        actions_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        act_layout = QHBoxLayout(actions_widget)
        act_layout.setContentsMargins(2, 0, 10, 0)
        act_layout.setSpacing(4)

        btn_open = QPushButton()
        btn_open.setObjectName("btnIcon")
        btn_open.setIcon(make_icon("folder", MUTED))
        btn_open.setToolTip("Abrir arquivo / pasta")
        btn_open.clicked.connect(lambda _, tid=task.task_id: self.open_task_file(tid))

        btn_cancel = QPushButton()
        btn_cancel.setObjectName("btnIcon")
        btn_cancel.setIcon(make_icon("x", MUTED))
        btn_cancel.setToolTip("Cancelar tarefa")
        btn_cancel.clicked.connect(lambda _, tid=task.task_id: self.cancel_task(tid))

        act_layout.addWidget(btn_open)
        act_layout.addWidget(btn_cancel)
        self.table.setCellWidget(row, 2, actions_widget)

        self.task_widgets[task.task_id] = {"row": row_widget, "status": status_lbl}
        self.apply_status_style(task.task_id, task.status)

    def start_queue(self):
        if not self.manager.tasks:
            QMessageBox.information(self, "Fila Vazia", "Adicione links antes de iniciar a fila.")
            return
        self.btn_start.setEnabled(False)
        self.btn_start.setText("Baixando...")
        self.manager.start_queue()
        self.update_queue_stats()
        self.append_log("Fila iniciada.")

    def pause_queue(self):
        self.manager.pause_queue()
        self.reset_start_button()
        self.append_log("Fila pausada. Downloads em andamento continuarão até o fim.")

    def reset_start_button(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Iniciar fila")

    def cancel_task(self, task_id):
        self.manager.cancel_task(task_id)
        self.append_log(f"Tarefa #{task_id} cancelada.")
        self.update_queue_stats()

    def open_task_file(self, task_id):
        for task in self.manager.tasks:
            if task.task_id == task_id:
                if task.final_filepath and os.path.exists(task.final_filepath):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(task.final_filepath))
                elif os.path.exists(task.output_dir):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(task.output_dir))
                break

    def clear_completed(self):
        self.manager.clear_completed()
        self.rebuild_table()
        self.update_queue_stats()
        self.append_log("Tarefas concluídas foram limpas da visualização.")

    def clear_all_tasks(self):
        if not self.manager.tasks:
            return
        confirm = QMessageBox.question(
            self, "Limpar Fila",
            "Deseja interromper e remover todas as tarefas da fila?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.manager.clear_all()
            self.rebuild_table()
            self.reset_start_button()
            self.update_queue_stats()
            self.append_log("Todas as tarefas foram canceladas e removidas.")

    def rebuild_table(self):
        self.table.setRowCount(0)
        self.task_row_map.clear()
        self.task_widgets.clear()
        for task in self.manager.tasks:
            self.add_task_to_table(task)
            # Restaura estados
            self.on_status_changed(task.task_id, task.status)
            if task.progress > 0:
                self.on_progress_changed(task.task_id, task.progress, task.speed, task.size_info, task.eta)

    def apply_status_style(self, task_id, status):
        widgets = self.task_widgets.get(task_id)
        if not widgets:
            return
        text, bg, fg, bar = STATUS_STYLES.get(status, ("Desconhecido", SURFACE_2, MUTED, MUTED))
        widgets["status"].setText(text)
        widgets["status"].setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 12px; font-size: 11px; font-weight: 600;"
        )
        row_widget = widgets["row"]
        row_widget.set_bar_color(bar)
        if status == "completed":
            row_widget.progress.setValue(100)
        if status == "error":
            task = next((t for t in self.manager.tasks if t.task_id == task_id), None)
            if task and task.error_message:
                row_widget.lbl_info.setText(task.error_message[:120])
                row_widget.lbl_info.setToolTip(task.error_message)
        elif status == "cancelled":
            row_widget.lbl_info.setText("Cancelado")

    def on_status_changed(self, task_id, status):
        self.apply_status_style(task_id, status)
        self.update_queue_stats()

    def on_progress_changed(self, task_id, percent, speed, size_info, eta):
        widgets = self.task_widgets.get(task_id)
        if not widgets:
            return
        row_widget = widgets["row"]
        row_widget.progress.setValue(int(percent))
        info_parts = [f"{percent:.0f}%"] if percent else []
        info_parts += [p for p in [speed, size_info, eta] if p]
        row_widget.lbl_info.setText("  ·  ".join(info_parts))

    def on_task_finished(self, task_id, success, message):
        self.manager.on_worker_finished(task_id, success, message)
        self.update_queue_stats()

    def on_all_finished(self):
        self.reset_start_button()
        errors = sum(1 for t in self.manager.tasks if t.status == "error")
        completed = sum(1 for t in self.manager.tasks if t.status == "completed")
        total = len(self.manager.tasks)
        self.append_log("Todas as tarefas da fila foram concluídas!" + (f" ({errors} com erro)" if errors else ""))
        self.update_queue_stats()
        # Pisca o ícone na barra de tarefas se a janela não estiver em foco
        QApplication.alert(self)

        # Notificação nativa do Windows (Toast via Bandeja)
        if hasattr(self, "tray_icon") and self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            title = "Downloads Concluídos! 🎉"
            if errors:
                body = f"{completed} concluído(s) e {errors} erro(s) de {total} itens.\nClique para abrir a pasta de downloads."
            else:
                body = f"Todos os {completed} arquivo(s) foram baixados com sucesso!\nClique para abrir a pasta de downloads."
            self.tray_icon.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 6000)

        # Chime sonoro suave do Windows
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def on_log_received(self, task_id, line):
        self.append_log(f"[# {task_id}] {line}")

    def append_log(self, text):
        self.txt_logs.append(text)

    def clear_logs(self):
        self.txt_logs.clear()

    def copy_logs(self):
        QApplication.clipboard().setText(self.txt_logs.toPlainText())
        QMessageBox.information(self, "Sucesso", "Logs copiados para a área de transferência!")

    def toggle_log_drawer(self, checked):
        self.log_widget.setVisible(checked)

    def update_queue_stats(self):
        tasks = self.manager.tasks
        total = len(tasks)
        counts = {s: sum(1 for t in tasks if t.status == s) for s in ("queued", "downloading", "completed", "error")}

        self.pill_total.setText(f"{total} total")
        for widget, key, label in (
            (self.pill_down, "downloading", "baixando"),
            (self.pill_queued, "queued", "na fila"),
            (self.pill_done, "completed", "concluído" if counts["completed"] == 1 else "concluídos"),
            (self.pill_err, "error", "erro" if counts["error"] == 1 else "erros"),
        ):
            widget.setText(f"{counts[key]} {label}")
            widget.setVisible(counts[key] > 0)

        self.queue_stack.setCurrentIndex(1 if total else 0)
        self.btn_clear_done.setEnabled(counts["completed"] > 0)
        self.btn_clear_all.setEnabled(total > 0)

    def task_id_at_row(self, row):
        for tid, r in self.task_row_map.items():
            if r == row:
                return tid
        return None

    def on_table_double_clicked(self, row, col):
        task_id = self.task_id_at_row(row)
        if task_id is not None:
            self.open_task_file(task_id)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        task_id = self.task_id_at_row(row)
        if task_id is None:
            return

        menu = QMenu(self)
        act_open_file = menu.addAction("Abrir arquivo")
        act_open_folder = menu.addAction("Abrir pasta no Explorer")
        menu.addSeparator()
        act_copy_url = menu.addAction("Copiar link do vídeo")
        act_retry = menu.addAction("Reiniciar download")
        act_cancel = menu.addAction("Cancelar / remover")

        action = menu.exec(QCursor.pos())
        if not action:
            return

        # Busca a tarefa
        target_task = next((t for t in self.manager.tasks if t.task_id == task_id), None)
        if not target_task:
            return

        if action == act_open_file:
            self.open_task_file(task_id)
        elif action == act_open_folder:
            if os.path.exists(target_task.output_dir):
                QDesktopServices.openUrl(QUrl.fromLocalFile(target_task.output_dir))
        elif action == act_copy_url:
            QApplication.clipboard().setText(target_task.url)
        elif action == act_retry:
            target_task.status = "queued"
            target_task.is_cancelled = False
            target_task.progress = 0.0
            self.on_status_changed(task_id, "queued")
            self.on_progress_changed(task_id, 0.0, "", "Reiniciado", "")
            self.manager.start_queue()
        elif action == act_cancel:
            self.cancel_task(task_id)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
