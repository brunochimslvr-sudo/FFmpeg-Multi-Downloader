import os
import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QMessageBox, QTabWidget, QGroupBox, QSplitter,
    QFrame, QMenu, QToolButton, QAbstractItemView, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QCursor, QDesktopServices

from downloader_engine import (
    DownloadManager, DownloaderSignals, DownloadTask,
    FFMPEG_PATH, YTDLP_PATH, sanitize_filename
)

# Estilo Moderno Dark (Dark Theme QSS)
MODERN_STYLE = """
QMainWindow {
    background-color: #12131C;
}

QWidget {
    color: #E2E8F0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QGroupBox {
    background-color: #1A1C28;
    border: 1px solid #2D3148;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 600;
    font-size: 13px;
    color: #93C5FD;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
}

QTabWidget::pane {
    border: 1px solid #2D3148;
    background-color: #1A1C28;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: #151722;
    color: #94A3B8;
    padding: 9px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #1A1C28;
    color: #38BDF8;
    border: 1px solid #2D3148;
    border-bottom: none;
}

QTabBar::tab:hover:!selected {
    background: #202334;
    color: #CBD5E1;
}

QLineEdit, QTextEdit, QSpinBox, QComboBox {
    background-color: #0F111A;
    border: 1px solid #2D3148;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
    selection-background-color: #2563EB;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #38BDF8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1A1C28;
    border: 1px solid #2D3148;
    selection-background-color: #2563EB;
    color: #F8FAFC;
}

QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #1E2333;
    color: #64748B;
}

QPushButton#btnSuccess {
    background-color: #059669;
}
QPushButton#btnSuccess:hover {
    background-color: #047857;
}

QPushButton#btnDanger {
    background-color: #DC2626;
}
QPushButton#btnDanger:hover {
    background-color: #B91C1C;
}

QPushButton#btnSecondary {
    background-color: #26293B;
    border: 1px solid #3B4261;
    color: #E2E8F0;
}
QPushButton#btnSecondary:hover {
    background-color: #32374E;
}

QTableWidget {
    background-color: #1A1C28;
    border: 1px solid #2D3148;
    border-radius: 8px;
    gridline-color: #222638;
    selection-background-color: #253352;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #141622;
    color: #94A3B8;
    padding: 8px 6px;
    border: none;
    border-bottom: 1px solid #2D3148;
    font-weight: 600;
}

QProgressBar {
    border: 1px solid #2D3148;
    border-radius: 5px;
    text-align: center;
    background-color: #0F111A;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #06B6D4);
    border-radius: 4px;
}

QRadioButton {
    color: #E2E8F0;
    font-weight: 600;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid #475569;
    background-color: #0F111A;
}
QRadioButton::indicator:checked {
    border-color: #38BDF8;
    background-color: #2563EB;
}
QRadioButton::indicator:hover {
    border-color: #38BDF8;
}

QScrollBar:vertical {
    border: none;
    background: #12131C;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2D3148;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg Multi-Video Downloader")
        self.resize(1060, 740)
        self.setMinimumSize(850, 580)
        self.setStyleSheet(MODERN_STYLE)

        self.signals = DownloaderSignals()
        self.manager = DownloadManager(self.signals)

        # Mapeamento de id da tarefa para linha da tabela
        self.task_row_map = {}

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # 1. Header Superior
        header_layout = QHBoxLayout()
        
        title_box = QVBoxLayout()
        title_label = QLabel("🎬 FFmpeg Multi-Video Downloader")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #F8FAFC;")
        
        subtitle_label = QLabel("Baixe múltiplos vídeos, streams m3u8 e playlists em lote simultaneamente")
        subtitle_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Status dos Binários Locais
        bin_box = QHBoxLayout()
        bin_box.setSpacing(10)

        ffmpeg_exists = os.path.exists(FFMPEG_PATH)
        badge_ffmpeg = QLabel(f"● FFmpeg: {'Pronto (Local)' if ffmpeg_exists else 'Não encontrado'}")
        badge_ffmpeg.setStyleSheet(
            f"background-color: {'#064E3B' if ffmpeg_exists else '#7F1D1D'}; "
            f"color: {'#6EE7B7' if ffmpeg_exists else '#FCA5A5'}; "
            "padding: 5px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;"
        )
        badge_ffmpeg.setToolTip(f"Caminho: {FFMPEG_PATH}")

        ytdlp_exists = os.path.exists(YTDLP_PATH)
        badge_ytdlp = QLabel(f"● yt-dlp: {'Pronto (Local)' if ytdlp_exists else 'Não encontrado'}")
        badge_ytdlp.setStyleSheet(
            f"background-color: {'#064E3B' if ytdlp_exists else '#7F1D1D'}; "
            f"color: {'#6EE7B7' if ytdlp_exists else '#FCA5A5'}; "
            "padding: 5px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;"
        )
        badge_ytdlp.setToolTip(f"Caminho: {YTDLP_PATH}")

        bin_box.addWidget(badge_ffmpeg)
        bin_box.addWidget(badge_ytdlp)
        header_layout.addLayout(bin_box)

        main_layout.addLayout(header_layout)

        # 2. Painel de Inserção de Links e Configurações (Abas)
        self.tabs = QTabWidget()
        self.tabs.setMaximumHeight(230)

        # Aba 1: Inserção em Lote
        tab_batch = QWidget()
        layout_batch = QVBoxLayout(tab_batch)
        layout_batch.setContentsMargins(12, 10, 12, 10)
        layout_batch.setSpacing(8)

        self.txt_links = QTextEdit()
        self.txt_links.setPlaceholderText(
            "Cole seus links aqui, um por linha:\n"
            "https://servidor.com/video1.m3u8\n"
            "https://servidor.com/video2.m3u8 | Aula 02 - Anatomia\n"
            "https://servidor.com/video3.mp4\n"
            "https://youtube.com/watch?v=..."
        )
        self.txt_links.textChanged.connect(self.update_links_counter)
        layout_batch.addWidget(self.txt_links)

        # Linha inferior da aba lote
        batch_controls = QHBoxLayout()
        
        lbl_prefix = QLabel("Prefixo:")
        lbl_prefix.setStyleSheet("color: #94A3B8;")
        self.edt_prefix = QLineEdit()
        self.edt_prefix.setPlaceholderText("Ex: Aula_")
        self.edt_prefix.setMaximumWidth(130)

        # Seletor Vídeo ou Música
        type_container = QFrame()
        type_container.setStyleSheet("""
            QFrame {
                background-color: #0F111A;
                border: 1px solid #2D3148;
                border-radius: 6px;
            }
        """)
        type_layout = QHBoxLayout(type_container)
        type_layout.setContentsMargins(8, 2, 8, 2)
        type_layout.setSpacing(12)

        lbl_mode = QLabel("Baixar como:")
        lbl_mode.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 12px; border: none;")

        self.rb_video = QRadioButton("🎬 Vídeo (MP4)")
        self.rb_audio = QRadioButton("🎵 Música (MP3)")
        self.rb_video.setStyleSheet("border: none; color: #E2E8F0; font-weight: 600;")
        self.rb_audio.setStyleSheet("border: none; color: #E2E8F0; font-weight: 600;")
        self.rb_video.setChecked(True)

        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.rb_video)
        self.type_group.addButton(self.rb_audio)

        type_layout.addWidget(lbl_mode)
        type_layout.addWidget(self.rb_video)
        type_layout.addWidget(self.rb_audio)

        self.lbl_counter = QLabel("0 links detectados")
        self.lbl_counter.setStyleSheet("color: #38BDF8; font-weight: 600;")

        btn_import_txt = QPushButton("📂 Importar .txt")
        btn_import_txt.setObjectName("btnSecondary")
        btn_import_txt.clicked.connect(self.import_from_txt)

        btn_clear_text = QPushButton("Limpar")
        btn_clear_text.setObjectName("btnSecondary")
        btn_clear_text.clicked.connect(self.txt_links.clear)

        btn_add_batch = QPushButton("➕ Adicionar à Fila")
        btn_add_batch.clicked.connect(self.add_batch_links)

        batch_controls.addWidget(lbl_prefix)
        batch_controls.addWidget(self.edt_prefix)
        batch_controls.addSpacing(6)
        batch_controls.addWidget(type_container)
        batch_controls.addSpacing(6)
        batch_controls.addWidget(self.lbl_counter)
        batch_controls.addStretch()
        batch_controls.addWidget(btn_import_txt)
        batch_controls.addWidget(btn_clear_text)
        batch_controls.addWidget(btn_add_batch)

        layout_batch.addLayout(batch_controls)
        self.tabs.addTab(tab_batch, "📋 Múltiplos Links (Em Lote)")

        # Aba 2: Opções de Download & Headers HTTP
        tab_options = QWidget()
        layout_options = QVBoxLayout(tab_options)
        layout_options.setContentsMargins(12, 10, 12, 10)
        layout_options.setSpacing(8)

        # Pasta de Destino
        dest_layout = QHBoxLayout()
        lbl_dest = QLabel("Salvar em:")
        lbl_dest.setMinimumWidth(80)
        default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")
        self.edt_dest = QLineEdit(default_dir)
        btn_browse = QPushButton("Procurar...")
        btn_browse.setObjectName("btnSecondary")
        btn_browse.clicked.connect(self.browse_folder)

        btn_open_folder = QPushButton("📂 Abrir Pasta")
        btn_open_folder.setObjectName("btnSecondary")
        btn_open_folder.clicked.connect(self.open_downloads_folder)

        dest_layout.addWidget(lbl_dest)
        dest_layout.addWidget(self.edt_dest)
        dest_layout.addWidget(btn_browse)
        dest_layout.addWidget(btn_open_folder)
        layout_options.addLayout(dest_layout)

        # Configurações de Motor, Formato e Simultâneos
        cfg_layout = QHBoxLayout()

        lbl_engine = QLabel("Motor:")
        self.cmb_engine = QComboBox()
        self.cmb_engine.addItem("Automático (Recomendado)", "auto")
        self.cmb_engine.addItem("FFmpeg Direto (Cópia ultrarrápida / m3u8)", "ffmpeg")
        self.cmb_engine.addItem("yt-dlp (Muxing / YouTube / Sites)", "ytdlp")

        lbl_fmt = QLabel("Formato:")
        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItem("MP4 (.mp4)", "mp4")
        self.cmb_fmt.addItem("MKV (.mkv)", "mkv")
        self.cmb_fmt.addItem("TS (.ts)", "ts")
        self.cmb_fmt.addItem("MP3 (.mp3 - Apenas Áudio)", "mp3")

        lbl_concurrent = QLabel("Downloads Simultâneos:")
        self.spn_concurrent = QSpinBox()
        self.spn_concurrent.setRange(1, 6)
        self.spn_concurrent.setValue(2)
        self.spn_concurrent.valueChanged.connect(self.update_max_concurrent)

        cfg_layout.addWidget(lbl_engine)
        cfg_layout.addWidget(self.cmb_engine)
        cfg_layout.addSpacing(15)
        cfg_layout.addWidget(lbl_fmt)
        cfg_layout.addWidget(self.cmb_fmt)
        cfg_layout.addSpacing(15)
        cfg_layout.addWidget(lbl_concurrent)
        cfg_layout.addWidget(self.spn_concurrent)
        cfg_layout.addStretch()

        layout_options.addLayout(cfg_layout)

        # Headers HTTP personalizados
        headers_layout = QHBoxLayout()
        lbl_headers = QLabel("Headers HTTP\n(Opcional):")
        lbl_headers.setMinimumWidth(80)
        self.txt_headers = QTextEdit()
        self.txt_headers.setPlaceholderText(
            "Cole cabeçalhos se o site exigir (exemplo de aulas/cursos protegidos):\n"
            "Referer: https://plataforma.com/\n"
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )
        self.txt_headers.setMaximumHeight(65)
        headers_layout.addWidget(lbl_headers)
        headers_layout.addWidget(self.txt_headers)

        layout_options.addLayout(headers_layout)

        self.tabs.addTab(tab_options, "⚙️ Opções & Headers HTTP")
        main_layout.addWidget(self.tabs)

        # 3. Tabela da Fila de Downloads
        table_header_layout = QHBoxLayout()
        lbl_queue_title = QLabel("Fila de Downloads")
        lbl_queue_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_queue_title.setStyleSheet("color: #F8FAFC;")
        
        self.lbl_queue_stats = QLabel("Total: 0 itens")
        self.lbl_queue_stats.setStyleSheet("color: #94A3B8; font-size: 12px;")

        table_header_layout.addWidget(lbl_queue_title)
        table_header_layout.addWidget(self.lbl_queue_stats)
        table_header_layout.addStretch()
        main_layout.addLayout(table_header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "Status", "Nome do Arquivo", "Progresso", "Velocidade / Info", "Ações"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 190)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 210)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 130)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        main_layout.addWidget(self.table)

        # 4. Barra de Controles Globais
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_start = QPushButton("▶ Iniciar Fila")
        self.btn_start.setObjectName("btnSuccess")
        self.btn_start.setMinimumHeight(38)
        self.btn_start.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_start.clicked.connect(self.start_queue)

        self.btn_pause = QPushButton("⏸ Pausar / Parar Fila")
        self.btn_pause.setObjectName("btnSecondary")
        self.btn_pause.setMinimumHeight(38)
        self.btn_pause.clicked.connect(self.pause_queue)

        self.btn_clear_done = QPushButton("🧹 Limpar Concluídos")
        self.btn_clear_done.setObjectName("btnSecondary")
        self.btn_clear_done.clicked.connect(self.clear_completed)

        self.btn_clear_all = QPushButton("❌ Limpar Tudo")
        self.btn_clear_all.setObjectName("btnSecondary")
        self.btn_clear_all.clicked.connect(self.clear_all_tasks)

        self.btn_toggle_logs = QPushButton("📜 Ver Logs")
        self.btn_toggle_logs.setObjectName("btnSecondary")
        self.btn_toggle_logs.setCheckable(True)
        self.btn_toggle_logs.toggled.connect(self.toggle_log_drawer)

        bottom_bar.addWidget(self.btn_start)
        bottom_bar.addWidget(self.btn_pause)
        bottom_bar.addWidget(self.btn_clear_done)
        bottom_bar.addWidget(self.btn_clear_all)
        bottom_bar.addStretch()
        bottom_bar.addWidget(btn_open_folder)
        bottom_bar.addWidget(self.btn_toggle_logs)
        main_layout.addLayout(bottom_bar)

        # 5. Painel de Logs (Recolhível)
        self.log_widget = QWidget()
        layout_log = QVBoxLayout(self.log_widget)
        layout_log.setContentsMargins(0, 0, 0, 0)
        layout_log.setSpacing(4)

        log_top = QHBoxLayout()
        lbl_log = QLabel("Terminal de Saída e Diagnóstico:")
        lbl_log.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        btn_copy_log = QPushButton("Copiar Log")
        btn_copy_log.setObjectName("btnSecondary")
        btn_copy_log.setMaximumWidth(90)
        btn_copy_log.clicked.connect(self.copy_logs)
        btn_clear_log = QPushButton("Limpar Log")
        btn_clear_log.setObjectName("btnSecondary")
        btn_clear_log.setMaximumWidth(90)
        btn_clear_log.clicked.connect(self.clear_logs)

        log_top.addWidget(lbl_log)
        log_top.addStretch()
        log_top.addWidget(btn_copy_log)
        log_top.addWidget(btn_clear_log)
        layout_log.addLayout(log_top)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setFont(QFont("Consolas", 10))
        self.txt_logs.setStyleSheet("background-color: #0A0C14; color: #A5B4FC; border: 1px solid #1F2338;")
        self.txt_logs.setMaximumHeight(130)
        layout_log.addWidget(self.txt_logs)

        self.log_widget.setVisible(False)
        main_layout.addWidget(self.log_widget)

    def connect_signals(self):
        self.signals.status_changed.connect(self.on_status_changed)
        self.signals.progress_changed.connect(self.on_progress_changed)
        self.signals.log_received.connect(self.on_log_received)
        self.signals.task_finished.connect(self.on_task_finished)
        self.signals.all_finished.connect(self.on_all_finished)

        # Sincronização entre seletor de Vídeo/Música e Formato
        self.rb_video.toggled.connect(self.on_type_radio_toggled)
        self.cmb_fmt.currentIndexChanged.connect(self.on_cmb_fmt_changed)

    def on_type_radio_toggled(self, checked):
        if self.rb_audio.isChecked():
            idx = self.cmb_fmt.findData("mp3")
            if idx != -1:
                self.cmb_fmt.blockSignals(True)
                self.cmb_fmt.setCurrentIndex(idx)
                self.cmb_fmt.blockSignals(False)
        elif self.rb_video.isChecked():
            if self.cmb_fmt.currentData() == "mp3":
                idx = self.cmb_fmt.findData("mp4")
                if idx != -1:
                    self.cmb_fmt.blockSignals(True)
                    self.cmb_fmt.setCurrentIndex(idx)
                    self.cmb_fmt.blockSignals(False)

    def on_cmb_fmt_changed(self):
        fmt = self.cmb_fmt.currentData()
        self.rb_video.blockSignals(True)
        self.rb_audio.blockSignals(True)
        if fmt == "mp3":
            self.rb_audio.setChecked(True)
        else:
            self.rb_video.setChecked(True)
        self.rb_video.blockSignals(False)
        self.rb_audio.blockSignals(False)

    def update_links_counter(self):
        text = self.txt_links.toPlainText()
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('#')]
        count = len(lines)
        self.lbl_counter.setText(f"{count} link{'s' if count != 1 else ''} detectado{'s' if count != 1 else ''}")

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

    def add_batch_links(self):
        text = self.txt_links.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Aviso", "Por favor, cole ao menos um link na caixa de texto.")
            return

        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('#')]
        if not lines:
            QMessageBox.information(self, "Aviso", "Nenhum link válido encontrado.")
            return

        prefix = self.edt_prefix.text().strip()
        dest_dir = self.edt_dest.text().strip()
        engine = self.cmb_engine.currentData()

        # Determina formato baseado no seletor de Vídeo / Música
        if self.rb_audio.isChecked():
            fmt = "mp3"
        else:
            selected_fmt = self.cmb_fmt.currentData()
            fmt = selected_fmt if selected_fmt != "mp3" else "mp4"

        headers = self.txt_headers.toPlainText().strip()

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
                headers=headers
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

        # Coluna 0: #
        item_id = QTableWidgetItem(str(task.task_id))
        item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_id.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table.setItem(row, 0, item_id)

        # Coluna 1: Status
        status_widget = QLabel("⏳ Aguardando")
        status_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_widget.setStyleSheet(
            "background-color: #334155; color: #E2E8F0; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 11px;"
        )
        self.table.setCellWidget(row, 1, status_widget)

        # Coluna 2: Nome do Arquivo
        display_name = task.get_output_filename()
        icon_tag = "🎵 " if task.fmt == "mp3" else "🎬 "
        item_name = QTableWidgetItem(f"{icon_tag}{display_name}")
        tipo_desc = "Música (MP3)" if task.fmt == "mp3" else f"Vídeo ({task.fmt.upper()})"
        item_name.setToolTip(f"Arquivo: {display_name}\nTipo: {tipo_desc}\nURL: {task.url}")
        item_name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.table.setItem(row, 2, item_name)

        # Coluna 3: Progresso (QProgressBar)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setFixedHeight(18)
        self.table.setCellWidget(row, 3, progress_bar)

        # Coluna 4: Velocidade / Info
        info_label = QLabel("Na fila...")
        info_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.table.setCellWidget(row, 4, info_label)

        # Coluna 5: Ações
        actions_widget = QWidget()
        act_layout = QHBoxLayout(actions_widget)
        act_layout.setContentsMargins(2, 2, 2, 2)
        act_layout.setSpacing(4)

        btn_cancel = QPushButton("⏹")
        btn_cancel.setToolTip("Cancelar tarefa")
        btn_cancel.setFixedSize(28, 24)
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(lambda _, tid=task.task_id: self.cancel_task(tid))

        btn_open = QPushButton("📂")
        btn_open.setToolTip("Abrir arquivo / pasta")
        btn_open.setFixedSize(28, 24)
        btn_open.setObjectName("btnSecondary")
        btn_open.clicked.connect(lambda _, tid=task.task_id: self.open_task_file(tid))

        act_layout.addWidget(btn_cancel)
        act_layout.addWidget(btn_open)
        act_layout.addStretch()
        self.table.setCellWidget(row, 5, actions_widget)

    def start_queue(self):
        if not self.manager.tasks:
            QMessageBox.information(self, "Fila Vazia", "Adicione links antes de iniciar a fila.")
            return
        self.btn_start.setEnabled(False)
        self.btn_start.setText("▶ Baixando...")
        self.manager.start_queue()
        self.update_queue_stats()
        self.append_log("Fila iniciada.")

    def pause_queue(self):
        self.manager.pause_queue()
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶ Iniciar Fila")
        self.append_log("Fila pausada. Downloads em andamento continuarão até o fim.")

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
            self.btn_start.setEnabled(True)
            self.btn_start.setText("▶ Iniciar Fila")
            self.update_queue_stats()
            self.append_log("Todas as tarefas foram canceladas e removidas.")

    def rebuild_table(self):
        self.table.setRowCount(0)
        self.task_row_map.clear()
        for task in self.manager.tasks:
            self.add_task_to_table(task)
            # Restaura estados
            self.on_status_changed(task.task_id, task.status)
            if task.progress > 0:
                self.on_progress_changed(task.task_id, task.progress, task.speed, task.size_info, task.eta)

    def on_status_changed(self, task_id, status):
        row = self.task_row_map.get(task_id)
        if row is None or row >= self.table.rowCount():
            return

        status_lbl = self.table.cellWidget(row, 1)
        if not isinstance(status_lbl, QLabel):
            return

        styles = {
            "queued": ("⏳ Aguardando", "background-color: #334155; color: #E2E8F0;"),
            "downloading": ("⬇️ Baixando", "background-color: #1E3A8A; color: #93C5FD;"),
            "completed": ("✅ Concluído", "background-color: #064E3B; color: #6EE7B7;"),
            "error": ("❌ Erro", "background-color: #7F1D1D; color: #FCA5A5;"),
            "cancelled": ("⏹ Cancelado", "background-color: #4B5563; color: #D1D5DB;"),
        }

        text, style = styles.get(status, ("Desconhecido", ""))
        status_lbl.setText(text)
        status_lbl.setStyleSheet(style + " border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 11px;")
        self.update_queue_stats()

    def on_progress_changed(self, task_id, percent, speed, size_info, eta):
        row = self.task_row_map.get(task_id)
        if row is None or row >= self.table.rowCount():
            return

        prog_bar = self.table.cellWidget(row, 3)
        if isinstance(prog_bar, QProgressBar):
            prog_bar.setValue(int(percent))

        info_lbl = self.table.cellWidget(row, 4)
        if isinstance(info_lbl, QLabel):
            info_parts = [p for p in [speed, size_info, eta] if p]
            info_lbl.setText(" | ".join(info_parts))

    def on_task_finished(self, task_id, success, message):
        self.manager.on_worker_finished(task_id, success, message)
        self.update_queue_stats()

    def on_all_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶ Iniciar Fila")
        self.append_log("Todas as tarefas da fila foram concluídas!")
        self.update_queue_stats()

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
        self.btn_toggle_logs.setText("📜 Ocultar Logs" if checked else "📜 Ver Logs")

    def update_queue_stats(self):
        total = len(self.manager.tasks)
        queued = sum(1 for t in self.manager.tasks if t.status == "queued")
        downloading = sum(1 for t in self.manager.tasks if t.status == "downloading")
        completed = sum(1 for t in self.manager.tasks if t.status == "completed")
        errors = sum(1 for t in self.manager.tasks if t.status == "error")

        parts = [f"Total: {total}"]
        if downloading:
            parts.append(f"⬇️ {downloading} baixando")
        if queued:
            parts.append(f"⏳ {queued} pendentes")
        if completed:
            parts.append(f"✅ {completed} concluídos")
        if errors:
            parts.append(f"❌ {errors} com erro")

        self.lbl_queue_stats.setText(" | ".join(parts))

    def on_table_double_clicked(self, row, col):
        # Localiza a tarefa correspondente à linha
        for tid, r in self.task_row_map.items():
            if r == row:
                self.open_task_file(tid)
                break

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        task_id = None
        for tid, r in self.task_row_map.items():
            if r == row:
                task_id = tid
                break

        if task_id is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1A1C28;
                border: 1px solid #2D3148;
                color: #F8FAFC;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #2563EB;
            }
        """)

        act_open_file = menu.addAction("Abrir Arquivo")
        act_open_folder = menu.addAction("Abrir Pasta no Explorer")
        menu.addSeparator()
        act_copy_url = menu.addAction("Copiar Link do Vídeo")
        act_retry = menu.addAction("Reiniciar Download")
        act_cancel = menu.addAction("Cancelar / Remover")

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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
