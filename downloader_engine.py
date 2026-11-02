import os
import re
import sys
import time
import subprocess
import threading
import importlib.util
from urllib.parse import urlparse
from PyQt6.QtCore import QObject, pyqtSignal

def get_bin_path(binary_name):
    """
    Localiza o executável procurando primeiro na pasta bin/ local,
    e depois no PATH do sistema.
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    local_path = os.path.join(base_dir, "bin", f"{binary_name}.exe")
    if os.path.exists(local_path):
        return local_path

    from shutil import which
    system_path = which(binary_name)
    if system_path:
        return system_path
    return local_path

FFMPEG_PATH = get_bin_path("ffmpeg")
FFPROBE_PATH = get_bin_path("ffprobe")
YTDLP_PATH = get_bin_path("yt-dlp")

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
AUDIO_FORMATS = ["mp3", "flac", "wav", "m4a", "opus"]
MAX_RETRIES = 2
RETRY_DELAY_SEC = 4

# Nomes genéricos de arquivo em URLs (index.m3u8, playlist.m3u8...) que não servem como título
GENERIC_URL_NAMES = {"watch", "video", "videos", "playlist", "stream", "live", "index", "master", "manifest", "chunklist", "media", "embed"}

HAS_MUTAGEN = importlib.util.find_spec("mutagen") is not None


def get_ytdlp_version():
    try:
        from yt_dlp.version import __version__
        return __version__
    except Exception:
        return ""


def format_bytes(bytes_num):
    if not bytes_num or bytes_num <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"

def parse_time_to_seconds(time_str):
    try:
        parts = time_str.strip().split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 0.0

def sanitize_filename(filename):
    # Remove caracteres inválidos para arquivos no Windows
    invalid_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(invalid_chars, '_', filename)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip('. ')
    return cleaned if cleaned else "arquivo"

def is_direct_stream_url(url):
    """Links que o FFmpeg baixa direto (não passam por extratores de sites)."""
    path = urlparse(url.lower()).path
    return path.endswith((".m3u8", ".mpd", ".mp4", ".ts", ".mkv", ".m4a", ".mp3", ".webm", ".flac", ".wav"))

class DownloadTask:
    PERSIST_FIELDS = ("url", "raw_filename", "output_dir", "engine", "fmt", "headers", "quality",
                      "use_auto_title", "browser_cookies", "resolved_title",
                      "download_subtitles", "sub_lang", "sub_embed", "expand_playlist")

    def __init__(self, task_id, url, filename="", output_dir="", engine="auto", fmt="mp4", headers="", 
                 quality="best", use_auto_title=True, browser_cookies="none",
                 download_subtitles=False, sub_lang="pt", sub_embed=False, expand_playlist=True):
        self.task_id = task_id
        self.url = url.strip()
        self.raw_filename = filename.strip()
        self.output_dir = output_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")
        self.engine = engine  # 'auto', 'ffmpeg', 'ytdlp'
        self.fmt = fmt.lower()  # 'mp4', 'mkv', 'ts', 'mp3', 'flac', 'wav', 'm4a', 'opus'
        self.headers = headers  # raw string
        self.quality = str(quality).lower()  # 'best', '1080', '720', '480', '320', '256', '192', etc.
        self.use_auto_title = use_auto_title
        self.browser_cookies = browser_cookies  # 'none', 'chrome', 'edge', 'firefox', 'brave' ou caminho do arquivo
        self.download_subtitles = download_subtitles
        self.sub_lang = sub_lang
        self.sub_embed = sub_embed
        self.expand_playlist = expand_playlist
        
        self.resolved_title = ""
        self.resolving = False  # True enquanto o título/playlist ainda está sendo identificado
        self.thumbnail_url = ""
        self.thumbnail_bytes = None

        self.status = "queued"  # queued, downloading, completed, error, cancelled
        self.progress = 0.0
        self.speed = ""
        self.size_info = ""
        self.eta = ""
        self.error_message = ""
        self.final_filepath = ""
        self.is_cancelled = False
        self.process = None

    def to_dict(self):
        return {k: getattr(self, k, None) for k in self.PERSIST_FIELDS}

    def get_output_filename(self, final=False):
        """
        Nome do arquivo de saída. Com final=True nunca devolve o texto provisório
        "Buscando título..." (usado só para exibição enquanto o título é buscado).
        """
        ext = f".{self.fmt}"
        if self.resolved_title:
            name = self.resolved_title
            if not name.lower().endswith(ext):
                name += ext
            return sanitize_filename(name)

        if self.raw_filename:
            name = self.raw_filename
            if not name.lower().endswith(ext):
                name += ext
            return sanitize_filename(name)

        is_audio = self.fmt in AUDIO_FORMATS
        if self.use_auto_title and not final:
            return f"Buscando título da música...{ext}" if is_audio else f"Buscando título do vídeo...{ext}"

        parsed = urlparse(self.url)
        path = parsed.path.rstrip('/')
        base = os.path.basename(path)
        stem = os.path.splitext(base)[0] if '.' in base else base
        if stem and stem.lower() not in GENERIC_URL_NAMES:
            return sanitize_filename(f"{stem}{ext}")
        return sanitize_filename(f"{'musica' if is_audio else 'video'}_{self.task_id}{ext}")

class DownloaderSignals(QObject):
    status_changed = pyqtSignal(int, str)       # task_id, status
    progress_changed = pyqtSignal(int, float, str, str, str) # task_id, percent, speed, size_info, eta
    title_updated = pyqtSignal(int, str)        # task_id, new_title
    thumbnail_loaded = pyqtSignal(int, bytes)   # task_id, thumb_bytes
    log_received = pyqtSignal(int, str)         # task_id, log_line
    task_finished = pyqtSignal(int, bool, str)  # task_id, success, message
    tasks_replaced = pyqtSignal(int, int)       # task_id da playlist, quantidade de itens criados
    all_finished = pyqtSignal()

class DownloadWorker(threading.Thread):
    def __init__(self, task: DownloadTask, signals: DownloaderSignals, manager=None):
        super().__init__()
        self.task = task
        self.signals = signals
        self.manager = manager
        self.daemon = True

    def log(self, msg):
        self.signals.log_received.emit(self.task.task_id, msg)

    def run(self):
        try:
            os.makedirs(self.task.output_dir, exist_ok=True)
            self.task.status = "downloading"
            self.signals.status_changed.emit(self.task.task_id, "downloading")
            self.log(f"Iniciando download da tarefa #{self.task.task_id}")
            self.log(f"URL: {self.task.url}")

            use_engine = self.task.engine
            if use_engine == "auto":
                if self.task.browser_cookies and self.task.browser_cookies != "none":
                    use_engine = "ytdlp"
                elif ".m3u8" in self.task.url.lower():
                    use_engine = "ffmpeg"
                elif any(domain in self.task.url.lower() for domain in ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "facebook.com", "instagram.com", "twitch.tv", "soundcloud.com", "bandcamp.com"]):
                    use_engine = "ytdlp"
                else:
                    use_engine = "ytdlp" if (self.task.use_auto_title or self.task.fmt in AUDIO_FORMATS) else "ffmpeg"

            success = False
            for attempt in range(MAX_RETRIES + 1):
                if attempt:
                    self.log(f"Tentativa {attempt + 1} de {MAX_RETRIES + 1} em {RETRY_DELAY_SEC}s...")
                    self.signals.progress_changed.emit(self.task.task_id, 0.0, "", f"Nova tentativa ({attempt + 1}/{MAX_RETRIES + 1})", "")
                    time.sleep(RETRY_DELAY_SEC)
                    if self.task.is_cancelled:
                        break
                    self.task.error_message = ""

                if use_engine == "ffmpeg":
                    success = self.download_with_ffmpeg()
                else:
                    success = self.download_with_ytdlp()

                if success or self.task.is_cancelled:
                    break
                self.log(f"Falhou: {self.task.error_message or 'erro desconhecido'}")
                # 403/404 etc. não se resolvem tentando de novo (link errado, expirado ou sem permissão)
                if re.search(r"(Server returned|HTTP Error) 4\d\d", self.task.error_message):
                    break

            if self.task.is_cancelled:
                self.task.status = "cancelled"
                self.signals.status_changed.emit(self.task.task_id, "cancelled")
                self.signals.task_finished.emit(self.task.task_id, False, "Cancelado pelo usuário")
                self.log("Download cancelado.")
            elif success:
                self.task.status = "completed"
                self.task.progress = 100.0
                self.signals.progress_changed.emit(self.task.task_id, 100.0, "", self.task.size_info or "Concluído", "")
                self.signals.status_changed.emit(self.task.task_id, "completed")
                self.signals.task_finished.emit(self.task.task_id, True, "Download concluído com sucesso!")
                self.log("Download concluído com sucesso!")
            else:
                self.task.status = "error"
                self.signals.status_changed.emit(self.task.task_id, "error")
                self.signals.task_finished.emit(self.task.task_id, False, self.task.error_message or "Falha no download")
        except Exception as e:
            self.task.status = "error"
            self.task.error_message = str(e)
            self.signals.status_changed.emit(self.task.task_id, "error")
            self.signals.task_finished.emit(self.task.task_id, False, str(e))
            self.log(f"Erro inesperado: {str(e)}")

    def parse_headers_dict(self):
        return parse_headers_dict(self.task.headers)

    def parse_headers_ffmpeg_str(self):
        headers_dict = self.parse_headers_dict()
        result = "".join(f"{k}: {v}\r\n" for k, v in headers_dict.items())
        return result

    def download_with_ffmpeg(self):
        output_name = self.task.get_output_filename(final=True)
        if self.manager:
            output_path = self.manager.reserve_output_path(self.task, os.path.join(self.task.output_dir, output_name))
        else:
            output_path = os.path.join(self.task.output_dir, output_name)
        self.task.final_filepath = output_path

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            self.log(f"Arquivo já existe, pulando: {os.path.basename(output_path)}")
            self.task.size_info = "Já existia na pasta"
            return True

        cmd = [FFMPEG_PATH, "-y", "-hide_banner", "-user_agent", DEFAULT_USER_AGENT]

        headers_str = self.parse_headers_ffmpeg_str()
        if headers_str:
            cmd.extend(["-headers", headers_str])

        if urlparse(self.task.url).scheme in ("http", "https"):
            # Reconecta sozinho se a conexão cair no meio do stream
            cmd.extend([
                "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_on_network_error", "1",
                "-reconnect_delay_max", "10", "-rw_timeout", "30000000",
            ])

        cmd.extend(["-i", self.task.url])

        # Formatos de áudio
        if self.task.fmt == "flac":
            cmd.extend(["-vn", "-c:a", "flac"])
        elif self.task.fmt == "wav":
            cmd.extend(["-vn", "-c:a", "pcm_s16le"])
        elif self.task.fmt == "m4a":
            bitrate = f"{self.task.quality}k" if self.task.quality in ['128', '192', '256', '320'] else "256k"
            cmd.extend(["-vn", "-c:a", "aac", "-b:a", bitrate])
        elif self.task.fmt == "opus":
            cmd.extend(["-vn", "-c:a", "libopus", "-b:a", "160k"])
        elif self.task.fmt == "mp3":
            bitrate = f"{self.task.quality}k" if self.task.quality in ['128', '192', '256', '320'] else "320k"
            cmd.extend(["-vn", "-c:a", "libmp3lame", "-b:a", bitrate])
        else:
            # Formatos de vídeo
            cmd.extend(["-c", "copy"])
            if self.task.fmt == "mp4":
                cmd.extend(["-bsf:a", "aac_adtstoasc", "-movflags", "+faststart"])

        cmd.extend(["-progress", "pipe:1", output_path])

        # Não registra os headers no log: podem conter Cookie / Authorization
        self.log(f"Executando FFmpeg → {os.path.basename(output_path)}")

        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW

        self.task.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            startupinfo=startupinfo,
            creationflags=creationflags
        )

        total_duration_sec = 0.0
        last_stderr_lines = []

        def read_stderr():
            nonlocal total_duration_sec
            dur_regex = re.compile(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d+)")
            try:
                for line in iter(self.task.process.stderr.readline, ''):
                    if not line:
                        break
                    line_clean = line.strip()
                    if line_clean:
                        self.log(line_clean)
                        last_stderr_lines.append(line_clean)
                        del last_stderr_lines[:-5]
                        if total_duration_sec == 0.0:
                            m = dur_regex.search(line_clean)
                            if m:
                                h, m_min, s = m.groups()
                                total_duration_sec = int(h) * 3600 + int(m_min) * 60 + float(s)
            except Exception:
                pass

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        progress_data = {}
        last_update_time = 0
        try:
            for line in iter(self.task.process.stdout.readline, ''):
                if self.task.is_cancelled:
                    try:
                        self.task.process.kill()
                    except Exception:
                        pass
                    break

                line = line.strip()
                if not line:
                    continue

                if "=" in line:
                    key, val = line.split("=", 1)
                    progress_data[key.strip()] = val.strip()

                if line == "progress=continue" or line == "progress=end":
                    now = time.time()
                    if now - last_update_time >= 0.3 or line == "progress=end":
                        last_update_time = now
                        out_time = progress_data.get("out_time", "00:00:00")
                        out_sec = parse_time_to_seconds(out_time)
                        total_size = int(progress_data.get("total_size", 0) or 0)
                        speed = progress_data.get("speed", "N/A")

                        percent = 0.0
                        eta_str = ""
                        if total_duration_sec > 0:
                            percent = min(99.9, (out_sec / total_duration_sec) * 100)
                            speed_val = 1.0
                            m_sp = re.search(r"([\d\.]+)x", speed)
                            if m_sp:
                                speed_val = max(0.1, float(m_sp.group(1)))
                            remaining_sec = (total_duration_sec - out_sec) / speed_val
                            if remaining_sec > 0:
                                rem_m, rem_s = divmod(int(remaining_sec), 60)
                                rem_h, rem_m = divmod(rem_m, 60)
                                eta_str = f"ETA: {rem_h:02d}:{rem_m:02d}:{rem_s:02d}"

                        size_str = format_bytes(total_size)
                        speed_str = f"Vel: {speed}"
                        info_str = f"{size_str} | Tempo: {out_time.split('.')[0]}"
                        self.task.size_info = size_str
                        self.signals.progress_changed.emit(self.task.task_id, percent, speed_str, info_str, eta_str)

            self.task.process.wait()
            stderr_thread.join(timeout=2.0)

            if self.task.process.returncode == 0 and not self.task.is_cancelled:
                return True
            if not self.task.is_cancelled:
                hint = next((l for l in reversed(last_stderr_lines) if "Server returned" in l or "rror" in l),
                            last_stderr_lines[-1] if last_stderr_lines else "")
                self.task.error_message = f"FFmpeg: {hint}" if hint else f"FFmpeg erro {self.task.process.returncode}"
            self._remove_partial(output_path)
            return False
        except Exception as e:
            if not self.task.is_cancelled:
                self.task.error_message = str(e)
            self._remove_partial(output_path)
            return False

    def _remove_partial(self, path):
        # Arquivo incompleto não pode ficar na pasta, senão a próxima tentativa "pula" achando que já existe
        try:
            if path and os.path.exists(path):
                os.remove(path)
                self.log(f"Arquivo incompleto removido: {os.path.basename(path)}")
        except Exception:
            pass

    def download_with_ytdlp(self):
        import yt_dlp

        # Se houver nome manual, usa o nome do usuário.
        # Caso contrário, usa %(title)s.%(ext)s para salvar com o título original!
        if self.task.raw_filename or not self.task.use_auto_title:
            output_name = self.task.get_output_filename(final=True)
            stem, _ = os.path.splitext(output_name)
            output_template = os.path.join(self.task.output_dir, f"{stem}.%(ext)s")
        else:
            output_template = os.path.join(self.task.output_dir, "%(title)s.%(ext)s")

        headers_dict = self.parse_headers_dict()

        class YtDlpLogger:
            def __init__(self, task_id, signals):
                self.task_id = task_id
                self.signals = signals

            def debug(self, msg):
                if not msg.startswith("[debug]"):
                    self.signals.log_received.emit(self.task_id, msg)

            def info(self, msg):
                self.signals.log_received.emit(self.task_id, msg)

            def warning(self, msg):
                self.signals.log_received.emit(self.task_id, f"[Aviso] {msg}")

            def error(self, msg):
                self.signals.log_received.emit(self.task_id, f"[Erro] {msg}")

        last_update_time = [0]

        def ytdlp_hook(d):
            if self.task.is_cancelled:
                raise Exception("Download cancelado pelo usuário")

            # Atualiza o título assim que disponível
            info_dict = d.get('info_dict') or {}
            title = info_dict.get('title')
            if title and not self.task.resolved_title and self.task.use_auto_title and not self.task.raw_filename:
                self.task.resolved_title = f"{title}.{self.task.fmt}"
                self.signals.title_updated.emit(self.task.task_id, self.task.get_output_filename())

            status = d.get('status')
            if status == 'downloading':
                now = time.time()
                if now - last_update_time[0] >= 0.3:
                    last_update_time[0] = now
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes') or 0
                    speed = d.get('speed') or 0
                    eta = d.get('eta') or 0

                    percent = 0.0
                    if total > 0:
                        percent = min(99.9, (downloaded / total) * 100)

                    speed_str = f"{format_bytes(speed)}/s" if speed else ""
                    size_str = f"{format_bytes(downloaded)} / {format_bytes(total)}" if total else format_bytes(downloaded)
                    self.task.size_info = format_bytes(total or downloaded)

                    eta_str = ""
                    if eta:
                        eta_m, eta_s = divmod(int(eta), 60)
                        eta_h, eta_m = divmod(eta_m, 60)
                        eta_str = f"ETA: {eta_h:02d}:{eta_m:02d}:{eta_s:02d}"

                    self.signals.progress_changed.emit(self.task.task_id, percent, speed_str, size_str, eta_str)
            elif status == 'finished':
                self.log("Download concluído, processando saída...")
                self.signals.progress_changed.emit(self.task.task_id, 99.0, "", "Processando...", "")

        ydl_opts = {
            'ffmpeg_location': FFMPEG_PATH,
            'outtmpl': output_template,
            'logger': YtDlpLogger(self.task.task_id, self.signals),
            'progress_hooks': [ytdlp_hook],
            'nocheckcertificate': True,
            'windowsfilenames': True,
            'restrictfilenames': False,
            'quiet': True,
            'no_warnings': True,
            # Playlists já são separadas em itens na fila; aqui baixa só o link informado
            'noplaylist': True,
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
        }

        apply_cookie_opts(ydl_opts, self.task.browser_cookies, self.log)

        if headers_dict:
            ydl_opts['http_headers'] = headers_dict

        postprocessors = []
        # Formatos de áudio (MP3, FLAC, WAV, M4A, OPUS)
        if self.task.fmt in AUDIO_FORMATS:
            ydl_opts['format'] = 'bestaudio/best'
            postprocessor = {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.task.fmt,
            }
            if self.task.fmt in ("mp3", "m4a") and self.task.quality in ['128', '192', '256', '320']:
                postprocessor['preferredquality'] = self.task.quality
            elif self.task.fmt == "mp3":
                postprocessor['preferredquality'] = '320'
            postprocessors.append(postprocessor)
        else:
            # Formatos de vídeo
            q = self.task.quality
            if q in ["1080", "720", "480", "360"]:
                fmt_str = f"bestvideo[height<={q}]+bestaudio/best[height<={q}]/best"
            else:
                if self.task.fmt == "mp4":
                    fmt_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else:
                    fmt_str = "bestvideo+bestaudio/best"

            ydl_opts['format'] = fmt_str
            if self.task.fmt in ["mp4", "mkv"]:
                ydl_opts['merge_output_format'] = self.task.fmt

        # Metadados (título, artista, álbum, data) e capítulos
        if self.task.fmt != "ts":
            postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True,
                                   'add_chapters': self.task.fmt not in AUDIO_FORMATS})

        # Capa embutida no arquivo
        if self._can_embed_thumbnail():
            ydl_opts['writethumbnail'] = True
            postprocessors.insert(0, {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg', 'when': 'before_dl'})
            postprocessors.append({'key': 'EmbedThumbnail', 'already_have_thumbnail': False})

        # Legendas (.srt ou embutidas)
        if self.task.download_subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitlesformat'] = 'srt/best'
            if self.task.sub_lang == 'pt':
                ydl_opts['subtitleslangs'] = ['pt', 'pt-BR', 'pt-PT']
            elif self.task.sub_lang == 'en':
                ydl_opts['subtitleslangs'] = ['en', 'en-US', 'en-GB']
            else:
                ydl_opts['subtitleslangs'] = ['all']

            if self.task.sub_embed and self.task.fmt in ('mp4', 'mkv'):
                postprocessors.append({'key': 'FFmpegEmbedSubtitle'})
            else:
                postprocessors.append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})

        ydl_opts['postprocessors'] = postprocessors

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.task.url, download=True)
                if info:
                    if not self.task.thumbnail_bytes:
                        thumb_url = info.get('thumbnail')
                        if not thumb_url and info.get('thumbnails'):
                            thumb_url = info['thumbnails'][-1].get('url') or info['thumbnails'][0].get('url')
                        if thumb_url:
                            self.task.thumbnail_url = thumb_url
                            try:
                                import urllib.request
                                req = urllib.request.Request(thumb_url, headers={'User-Agent': DEFAULT_USER_AGENT})
                                with urllib.request.urlopen(req, timeout=4) as resp:
                                    b = resp.read()
                                    if b:
                                        self.task.thumbnail_bytes = b
                                        self.signals.thumbnail_loaded.emit(self.task.task_id, b)
                            except Exception:
                                pass

                    target_path = ydl.prepare_filename(info)
                    if self.task.fmt in AUDIO_FORMATS:
                        target_path = os.path.splitext(target_path)[0] + f".{self.task.fmt}"
                    elif self.task.fmt in ["mp4", "mkv"]:
                        target_path = os.path.splitext(target_path)[0] + f".{self.task.fmt}"
                    self.task.final_filepath = target_path
                    real_filename = os.path.basename(target_path)
                    self.task.resolved_title = real_filename
                    self.signals.title_updated.emit(self.task.task_id, real_filename)
            return True
        except Exception as e:
            if "Download cancelado" in str(e):
                return False
            self.task.error_message = str(e)
            return False

    def _can_embed_thumbnail(self):
        # mp3/mp4/m4a/mkv funcionam só com FFmpeg; flac/opus precisam do pacote mutagen; wav/ts não aceitam capa
        if self.task.fmt in ("mp3", "mp4", "m4a", "mkv"):
            return True
        if self.task.fmt in ("flac", "opus"):
            return HAS_MUTAGEN
        return False


def parse_headers_dict(raw_headers):
    headers_dict = {}
    has_ua = False
    if raw_headers:
        for line in raw_headers.strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                k = key.strip()
                v = val.strip()
                headers_dict[k] = v
                if k.lower() == "user-agent":
                    has_ua = True
    if not has_ua:
        headers_dict["User-Agent"] = DEFAULT_USER_AGENT
    return headers_dict


def apply_cookie_opts(ydl_opts, browser_cookies, log=None):
    # Injeta cookies do navegador ou arquivo cookies.txt se configurado
    if browser_cookies and browser_cookies != "none":
        if os.path.isfile(browser_cookies):
            ydl_opts['cookiefile'] = browser_cookies
            if log:
                log(f"Usando arquivo de cookies: {os.path.basename(browser_cookies)}")
        else:
            ydl_opts['cookiesfrombrowser'] = (browser_cookies,)
            if log:
                log(f"Usando sessão ativa do navegador: {browser_cookies}")


class DownloadManager:
    def __init__(self, signals: DownloaderSignals):
        self.signals = signals
        self.tasks = []
        self.active_workers = {}
        self.max_concurrent = 2
        self.is_running = False
        self._lock = threading.Lock()
        self._next_id = 1
        self._reserved_paths = {}  # caminho normalizado -> task_id

    def _new_task(self, url, filename="", output_dir="", engine="auto", fmt="mp4", headers="", 
                  quality="best", use_auto_title=True, browser_cookies="none",
                  download_subtitles=False, sub_lang="pt", sub_embed=False, expand_playlist=True):
        task = DownloadTask(
            self._next_id, url, filename, output_dir, engine, fmt, headers, quality, use_auto_title, browser_cookies,
            download_subtitles, sub_lang, sub_embed, expand_playlist
        )
        self._next_id += 1
        return task

    def add_task(self, url, filename="", output_dir="", engine="auto", fmt="mp4", headers="", 
                 quality="best", use_auto_title=True, browser_cookies="none",
                 download_subtitles=False, sub_lang="pt", sub_embed=False, expand_playlist=True):
        with self._lock:
            task = self._new_task(
                url, filename, output_dir, engine, fmt, headers, quality, use_auto_title, browser_cookies,
                download_subtitles, sub_lang, sub_embed, expand_playlist
            )
            self.tasks.append(task)

        # Busca título e detecta playlists em segundo plano (não para streams diretos)
        if engine != "ffmpeg" and not is_direct_stream_url(task.url):
            task.resolving = True
            self._prefetch_info_async(task)
        return task

    def restore_task(self, data):
        """Recria uma tarefa salva da sessão anterior."""
        with self._lock:
            task = self._new_task(
                data.get("url", ""), data.get("raw_filename", ""), data.get("output_dir", ""),
                data.get("engine", "auto"), data.get("fmt", "mp4"), data.get("headers", ""),
                data.get("quality", "best"), data.get("use_auto_title", True), data.get("browser_cookies", "none"),
                data.get("download_subtitles", False), data.get("sub_lang", "pt"), data.get("sub_embed", False),
                data.get("expand_playlist", True)
            )
            task.resolved_title = data.get("resolved_title", "")
            self.tasks.append(task)
            return task

    def _prefetch_info_async(self, task: DownloadTask):
        def worker():
            try:
                import yt_dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': 'in_playlist',
                    'noplaylist': not task.expand_playlist,
                    'skip_download': True,
                    'nocheckcertificate': True,
                    'http_headers': parse_headers_dict(task.headers),
                }
                apply_cookie_opts(ydl_opts, task.browser_cookies)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(task.url, download=False)
                if not info:
                    return

                entries = [e for e in (info.get('entries') or []) if e]
                if info.get('_type') == 'playlist' and entries and task.expand_playlist:
                    self._expand_playlist(task, info, entries)
                    return

                title = info.get('title')
                if title and task.use_auto_title and not task.raw_filename and not task.resolved_title:
                    task.resolved_title = f"{title}.{task.fmt}"
                    self.signals.title_updated.emit(task.task_id, task.get_output_filename())

                # Busca e carrega miniatura (Thumbnail)
                thumb_url = info.get('thumbnail')
                if not thumb_url and info.get('thumbnails'):
                    thumb_url = info['thumbnails'][-1].get('url') or info['thumbnails'][0].get('url')
                if thumb_url:
                    task.thumbnail_url = thumb_url
                    try:
                        import urllib.request
                        req = urllib.request.Request(thumb_url, headers={'User-Agent': DEFAULT_USER_AGENT})
                        with urllib.request.urlopen(req, timeout=4) as resp:
                            thumb_bytes = resp.read()
                            if thumb_bytes:
                                task.thumbnail_bytes = thumb_bytes
                                self.signals.thumbnail_loaded.emit(task.task_id, thumb_bytes)
                    except Exception:
                        pass
            except Exception as e:
                self.signals.log_received.emit(task.task_id, f"Não foi possível identificar o título/miniatura antes do download: {e}")
            finally:
                task.resolving = False
                self._check_queue()

        threading.Thread(target=worker, daemon=True).start()

    def _fetch_thumb_async(self, task: DownloadTask):
        def worker():
            try:
                import urllib.request
                req = urllib.request.Request(task.thumbnail_url, headers={'User-Agent': DEFAULT_USER_AGENT})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    thumb_bytes = resp.read()
                    if thumb_bytes:
                        task.thumbnail_bytes = thumb_bytes
                        self.signals.thumbnail_loaded.emit(task.task_id, thumb_bytes)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _expand_playlist(self, task: DownloadTask, info, entries):
        """Troca a tarefa da playlist por uma tarefa para cada item, na mesma posição da fila."""
        playlist_title = info.get('title') or "Playlist"
        new_tasks = []
        with self._lock:
            if task not in self.tasks or task.status != "queued":
                return
            for i, entry in enumerate(entries, 1):
                url = entry.get('url') or entry.get('webpage_url')
                if not url:
                    continue
                if not url.startswith("http") and entry.get('ie_key') == 'Youtube':
                    url = f"https://www.youtube.com/watch?v={url}"
                name = f"{task.raw_filename} - {i:02d}" if task.raw_filename else ""
                child = self._new_task(
                    url, name, task.output_dir, task.engine, task.fmt, task.headers,
                    task.quality, task.use_auto_title, task.browser_cookies,
                    task.download_subtitles, task.sub_lang, task.sub_embed, task.expand_playlist
                )
                if not name and task.use_auto_title and entry.get('title'):
                    child.resolved_title = f"{entry['title']}.{task.fmt}"
                
                thumb = entry.get('thumbnail')
                if not thumb and entry.get('thumbnails'):
                    thumb = entry['thumbnails'][-1].get('url') or entry['thumbnails'][0].get('url')
                if thumb:
                    child.thumbnail_url = thumb
                    
                new_tasks.append(child)
            if not new_tasks:
                return
            idx = self.tasks.index(task)
            self.tasks[idx:idx + 1] = new_tasks
        self.signals.log_received.emit(task.task_id, f"Playlist \"{playlist_title}\": {len(new_tasks)} itens adicionados à fila.")
        self.signals.tasks_replaced.emit(task.task_id, len(new_tasks))
        
        # Dispara busca de miniaturas para os novos itens da playlist
        for c in new_tasks:
            if c.thumbnail_url and not c.thumbnail_bytes:
                self._fetch_thumb_async(c)

    def reserve_output_path(self, task, path):
        """
        Garante que duas tarefas desta sessão não gravem no mesmo arquivo.
        Se outro item da fila já usa o nome, acrescenta " (2)", " (3)"...
        Um arquivo que já existia na pasta antes não é renomeado (é pulado pelo worker).
        """
        with self._lock:
            stem, ext = os.path.splitext(path)
            candidate = path
            n = 2
            while True:
                key = os.path.normcase(os.path.abspath(candidate))
                owner = self._reserved_paths.get(key)
                if owner is None or owner == task.task_id:
                    self._reserved_paths[key] = task.task_id
                    return candidate
                candidate = f"{stem} ({n}){ext}"
                n += 1

    def start_queue(self):
        self.is_running = True
        self._check_queue()

    def pause_queue(self):
        self.is_running = False

    def cancel_task(self, task_id):
        with self._lock:
            for task in self.tasks:
                if task.task_id == task_id:
                    task.is_cancelled = True
                    if task.status == "queued":
                        task.status = "cancelled"
                        self.signals.status_changed.emit(task.task_id, "cancelled")
                    if task.process:
                        try:
                            task.process.kill()
                        except Exception:
                            pass
                    break
        self._check_queue()

    def cancel_all(self):
        self.is_running = False
        with self._lock:
            for task in self.tasks:
                if task.status in ["queued", "downloading"]:
                    task.is_cancelled = True
                    if task.process:
                        try:
                            task.process.kill()
                        except Exception:
                            pass
                    task.status = "cancelled"
                    self.signals.status_changed.emit(task.task_id, "cancelled")

    def clear_completed(self):
        with self._lock:
            self.tasks = [t for t in self.tasks if t.status not in ["completed", "cancelled"]]

    def clear_all(self):
        self.cancel_all()
        with self._lock:
            self.tasks.clear()

    def on_worker_finished(self, task_id, success, message):
        with self._lock:
            if task_id in self.active_workers:
                del self.active_workers[task_id]
        self._check_queue()

    def _check_queue(self):
        if not self.is_running:
            return

        with self._lock:
            finished_ids = [tid for tid, w in self.active_workers.items() if not w.is_alive()]
            for fid in finished_ids:
                del self.active_workers[fid]

            pending = [t for t in self.tasks if t.status == "queued" and not t.is_cancelled]
            ready = [t for t in pending if not t.resolving]

            available_slots = self.max_concurrent - len(self.active_workers)
            for task in ready[:max(0, available_slots)]:
                worker = DownloadWorker(task, self.signals, self)
                self.active_workers[task.task_id] = worker
                task.status = "downloading"
                worker.start()

            # Itens ainda sendo identificados contam como pendentes: a fila não termina antes deles
            if not self.active_workers and not pending:
                self.is_running = False
                self.signals.all_finished.emit()
