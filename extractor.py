"""
Модуль логики извлечения аудиодорожек из видеофайлов.
Использует FFmpeg/ffprobe через subprocess с fallback-перекодировкой в WAV.
"""

import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from PySide6.QtCore import QObject, QThread, Signal, QMutex, QMutexLocker


def get_app_dir() -> Path:
    """
    Возвращает директорию приложения.
    Если упаковано через PyInstaller — папка с .exe, иначе папка со скриптом.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.resolve()
    return Path(__file__).parent.resolve()


def normalize_path(path: str | Path) -> str:
    """
    Приводит путь к единому формату для сравнения:
    абсолютный путь, нижний регистр, нормализованные слэши.
    Используется для корректной проверки дубликатов вне зависимости от регистра.
    """
    try:
        return str(Path(path).resolve()).lower()
    except Exception:
        # Fallback: если resolve не сработал (например, сетевой путь),
        # просто нормализуем строку
        try:
            s = str(path).replace("\\", "/").lower()
            while "//" in s:
                s = s.replace("//", "/")
            return s
        except Exception:
            return str(path).lower()


def resolve_app_icon_path() -> Optional[Path]:
    """
    Найти иконку приложения (используется окном + панелью задач).
    Приоритет (по убыванию):
      1) Portable/Gengar.ico   — кастомная иконка рядом с .exe (основной)
      2) Gengar.ico            — в корне проекта (если запускаем dev)
      5) None                  — fallback на программную отрисовку
    """
    app_dir = get_app_dir()

    candidates = [
        app_dir / "Gengar.ico",
    ]

    portable_dir = app_dir / "AudioTrackExtractor"
    try:
        if portable_dir.is_dir():
            candidates = [
                portable_dir / "Gengar.ico",
                portable_dir / "favicon.ico",
            ] + candidates
    except Exception:
        pass

    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return p
        except Exception:
            continue
    return None



class ConfigManager:
    """
    Управление настройками приложения: тема, путь сохранения аудио.
    Настройки хранятся в файле config.json рядом с приложением (portable).
    """

    DEFAULT_CONFIG = {
        "theme": "dark",          # "dark" / "light"
        "output_mode": "source",  # "source" = рядом с видео, "custom" = своя папка
        "custom_output_path": "", # Путь при output_mode == "custom"
    }

    def __init__(self):
        self.app_dir = get_app_dir()
        self.config_path = self.app_dir / "config.json"
        self._mutex = QMutex()
        self._config = self._load()

    def _load(self) -> dict:
        """Загрузить конфиг из файла или создать дефолтный."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                # Объединяем с дефолтным, чтобы не было пропущенных ключей
                merged = self.DEFAULT_CONFIG.copy()
                merged.update({k: v for k, v in user_cfg.items()
                               if k in self.DEFAULT_CONFIG})
                return merged
        except Exception:
            pass
        return self.DEFAULT_CONFIG.copy()

    def save(self):
        """Сохранить текущий конфиг в файл."""
        with QMutexLocker(self._mutex):
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

    def get(self, key: str):
        """Получить значение настройки по ключу."""
        with QMutexLocker(self._mutex):
            return self._config.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key: str, value):
        """Установить значение настройки и сразу сохранить в файл."""
        with QMutexLocker(self._mutex):
            self._config[key] = value
        self.save()



def check_ffmpeg_available() -> Tuple[bool, str]:
    """
    Проверяет наличие ffmpeg и ffprobe в системном PATH
    """
    missing = []
    for tool in ["ffmpeg", "ffprobe"]:
        try:
            res = subprocess.run(
                [tool, "-version"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode != 0:
                missing.append(tool)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            missing.append(tool)

    if missing:
        msg = (
            f"Не найдены необходимые инструменты: {', '.join(missing)}\n\n"
            "Приложение требует установленный FFmpeg (вместе с ffprobe),\n"
            "добавленный в системную переменную PATH.\n\n"
            "Как установить:\n"
            "  1. Скачайте FFmpeg с https://www.gyan.dev/ffmpeg/builds/\n"
            "  2. Распакуйте архив, например в C:\\ffmpeg\n"
            "  3. Добавьте путь C:\\ffmpeg\\bin в переменную среды PATH\n"
            "  4. Перезапустите приложение"
        )
        return False, msg
    return True, "OK"



SUPPORTED_EXT = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


class AudioExtractor(QObject):
    """
    Основной класс извлечения аудио. Работает в отдельном потоке.
    Использует пул из 2-х потоков для параллельной обработки файлов.
    """

    # Сигналы для связи с GUI
    log = Signal(str)                        # Лог-сообщение с уровнем
    progress = Signal(int)                   # Общий прогресс 0-100
    file_started = Signal(str)               # Начало обработки файла (путь)
    file_finished = Signal(str, bool, str)   # Файл обработан (путь, успех, инфо)
    all_finished = Signal(dict)              # Все обработаны {путь: (успех, инфо)}
    critical_error = Signal(str)             # Критическая ошибка (останавливает всё)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self._is_running = False
        self._should_stop = False
        self._mutex = QMutex()
        self._log_file_path = get_app_dir() / "extractor.log"
        self._results: Dict[str, Tuple[bool, str]] = {}
        self._max_workers = 2


    def stop(self):
        with QMutexLocker(self._mutex):
            self._should_stop = True

    def is_running(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._is_running

    def _should_stop_check(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._should_stop

    def _write_log_file(self, message: str):
        """Перезаписывает лог-файл рядом с приложением."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            line = f"[{timestamp}] {message}\n"
            with open(self._log_file_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def _reset_log_file(self):
        """Очистить лог-файл перед запуском."""
        try:
            with open(self._log_file_path, "w", encoding="utf-8") as f:
                f.write(
                    f"===== Audio Track Extractor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n"
                )
        except Exception:
            pass

    def log_file_path(self) -> Path:
        return self._log_file_path

    def _emit_log(self, msg: str):
        """Отправить лог в GUI и записать в файл."""
        self.log.emit(msg)
        self._write_log_file(msg)


    def start_extraction(self, file_paths: List[str]):
        """
        Запуск обработки списка файлов.
        Выполняется в вызывающем потоке (обычно это отдельный QThread).
        """
        with QMutexLocker(self._mutex):
            self._is_running = True
            self._should_stop = False
            self._results = {}

        self._reset_log_file()
        self._emit_log("=" * 60)
        self._emit_log(f"Запуск обработки. Файлов в очереди: {len(file_paths)}")
        self._emit_log(f"Параллельных потоков: {self._max_workers}")
        self._emit_log(f"Лог-файл: {self._log_file_path}")
        self._emit_log("=" * 60)

        # Проверяем выходной режим
        out_mode = self.config.get("output_mode")
        out_path_custom = self.config.get("custom_output_path") if out_mode == "custom" else None
        if out_mode == "custom":
            if not out_path_custom:
                self._emit_log("[ОШИБКА] Выбран пользовательский путь, но он не задан. "
                               "Используем расположение рядом с видео.")
                out_path_custom = None
            elif not Path(out_path_custom).exists():
                try:
                    Path(out_path_custom).mkdir(parents=True, exist_ok=True)
                    self._emit_log(f"Создана папка для вывода: {out_path_custom}")
                except Exception as e:
                    self._emit_log(f"[ОШИБКА] Невозможно создать папку {out_path_custom}: {e}")
                    out_path_custom = None

        total_files = len(file_paths)
        if total_files == 0:
            self._finish(dict())
            return

        self.progress.emit(0)
        processed_count = 0

        # Параллельная обработка через ThreadPoolExecutor
        try:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                future_map = {}
                for fp in file_paths:
                    if self._should_stop_check():
                        break
                    # Определяем корневую папку для результата
                    if out_path_custom:
                        output_root = Path(out_path_custom)
                    else:
                        output_root = Path(fp).parent
                    future = executor.submit(
                        self._process_single_file, fp, output_root
                    )
                    future_map[future] = fp

                for future in as_completed(future_map):
                    if self._should_stop_check():
                        self._emit_log("[ИНФО] Получен запрос на остановку.")
                        break
                    fp = future_map[future]
                    try:
                        success, info = future.result()
                    except Exception as e:
                        success, info = False, f"Необработанная ошибка: {e}"
                        self._emit_log(f"[КРИТИЧНО] {fp} — {info}")

                    self._results[fp] = (success, info)
                    processed_count += 1
                    percent = int(processed_count * 100 / total_files)
                    self.progress.emit(percent)
                    self.file_finished.emit(fp, success, info)
                    status = "ОК" if success else "ОШИБКА"
                    self._emit_log(f"[{status}] {Path(fp).name} — {info}")
        except Exception as e:
            msg = f"Критическая ошибка в диспетчере потоков: {e}"
            self._emit_log(f"[КРИТИЧНО] {msg}")
            self.critical_error.emit(msg)

        self._finish(self._results)

    def _finish(self, results: Dict[str, Tuple[bool, str]]):
        ok_count = sum(1 for ok, _ in results.values() if ok)
        fail_count = sum(1 for ok, _ in results.values() if not ok)
        self._emit_log("=" * 60)
        self._emit_log(
            f"Обработка завершена. Успешно: {ok_count}, "
            f"с ошибками: {fail_count}, всего: {len(results)}"
        )
        self._emit_log("=" * 60)
        self.progress.emit(100)
        with QMutexLocker(self._mutex):
            self._is_running = False
        self.all_finished.emit(results)



    def _process_single_file(self, video_path: str, output_root: Path) -> Tuple[bool, str]:
        """
        Обработать один видеофайл: определить дорожки, создать папку,
        извлечь все аудиодорожки с fallback-перекодировкой в WAV.
        """
        video_p = Path(video_path)
        file_label = video_p.name

        # Проверка существования файла
        if not video_p.exists() or not video_p.is_file():
            return False, "Файл не найден"

        # Получаем список аудио-индексов
        self._emit_log(f"→ Анализ файла: {file_label}")
        indices = self._get_audio_stream_indices(video_p)
        if indices is None:
            return False, "Ошибка чтения метаданных (ffprobe)"
        if len(indices) == 0:
            return False, "Аудиодорожек в файле не найдено"

        self._emit_log(f"  ↳ Найдено аудиодорожек: {len(indices)}")

        # Создаём папку <имя_видео>_audio
        try:
            folder_name = video_p.stem + "_audio"
            target_dir = output_root / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)
            self._emit_log(f"  ↳ Папка для результатов: {target_dir}")
        except Exception as e:
            return False, f"Не удалось создать папку: {e}"

        self.file_started.emit(video_path)

        # Извлекаем каждую дорожку
        errors = []
        extracted = 0
        for i, stream_idx in enumerate(indices, start=1):
            if self._should_stop_check():
                errors.append("Обработка прервана пользователем")
                break

            out_m4a = target_dir / f"track{i}.m4a"
            out_wav = target_dir / f"track{i}.wav"

            # Сначала пробуем скопировать поток как есть в m4a
            ok, msg = self._extract_copy(video_p, stream_idx, out_m4a)
            if ok:
                extracted += 1
                self._emit_log(f"  ↳ track{i}.m4a — скопирован (без перекодировки)")
                continue

            # Если copy не сработал — fallback в WAV (без потерь)
            self._emit_log(f"  ↳ track{i}.m4a — copy не удался: {msg}. Пробуем WAV...")
            ok2, msg2 = self._extract_to_wav(video_p, stream_idx, out_wav)
            if ok2:
                extracted += 1
                self._emit_log(f"  ↳ track{i}.wav — сохранён (без потерь, PCM)")
            else:
                err = f"track{i}: {msg2}"
                errors.append(err)
                self._emit_log(f"  ↳ [ОШИБКА] {err}")

        if len(indices) > 0 and extracted == len(indices):
            return True, f"Извлечено {extracted}/{len(indices)} дорожек"
        elif extracted > 0:
            return (False, f"Частично: {extracted}/{len(indices)} дорожек. Проблемы : {'; '.join(errors[:3])}")
        else:
            return False, f"Не извлечено ни одной дорожки: {'; '.join(errors[:3])}"


    def _get_audio_stream_indices(self, video_p: Path) -> Optional[List[int]]:
        """Получить индексы всех аудиопотоков через ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index",
                "-of", "csv=p=0",
                str(video_p),
            ]
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode != 0:
                self._emit_log(f"  [ffprobe] stderr: {res.stderr.strip()}")
                return None
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            return [int(l) for l in lines if l.isdigit()]
        except Exception as e:
            self._emit_log(f"  [ffprobe] Исключение: {e}")
            return None


    def _extract_copy(self, video_p: Path, stream_idx: int, out_path: Path) -> Tuple[bool, str]:
        """
        Извлечь аудиопоток без перекодировки (-c copy) в .m4a.
        """
        try:
            # Если файл существует — перезаписываем
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(video_p),
                "-map", f"0:{stream_idx}",
                "-c", "copy",
                "-f", "mp4",  # Принудительно mp4-контейнер для m4a
                str(out_path),
            ]
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return True, "OK"
            err = res.stderr.strip()
            if "moov atom not found" in err.lower():
                return False, "Файл битый или повреждён"
            if "invalid" in err.lower() and "codec" in err.lower():
                return False, "Кодек несовместим с m4a"
            short_err = err.splitlines()[-1] if err.splitlines() else "ffmpeg error"
            return False, short_err[:200]
        except subprocess.TimeoutExpired:
            return False, "Превышено время ожидания (10 мин)"
        except Exception as e:
            return False, f"Исключение: {e}"


    def _extract_to_wav(self, video_p: Path, stream_idx: int, out_path: Path) -> Tuple[bool, str]:
        """
        Fallback: извлечь аудио и перекодировать в несжатый WAV (PCM 16-bit).
        Без потери качества, совместимо с любыми кодеками.
        """
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(video_p),
                "-map", f"0:{stream_idx}",
                "-vn",
                "-acodec", "pcm_s16le",
                str(out_path),
            ]
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return True, "OK"
            err = res.stderr.strip()
            short_err = err.splitlines()[-1] if err.splitlines() else "ffmpeg error"
            return False, short_err[:200]
        except subprocess.TimeoutExpired:
            return False, "Превышено время ожидания (10 мин)"
        except Exception as e:
            return False, f"Исключение: {e}"



class ExtractionThread(QThread):
    """
    Обёртка над AudioExtractor, запускающая его в отдельном QThread,
    чтобы главный цикл интерфейса не зависал.
    """

    def __init__(self, extractor: AudioExtractor, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.extractor = extractor
        self.file_paths = file_paths

    def run(self):
        self.extractor.start_extraction(self.file_paths)
