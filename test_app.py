import os
import io
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


class TestHelperFunctions(unittest.TestCase):
    """Тесты вспомогательных функций extractor.py."""

    def setUp(self):
        from extractor import normalize_path, SUPPORTED_EXT
        self.normalize_path = normalize_path
        self.SUPPORTED_EXT = SUPPORTED_EXT

    def test_normalize_path_basic(self):
        """Простое приведение пути: нижний регистр + слэши."""
        p = "C:\\Users\\Test\\file.mp4"
        res = self.normalize_path(p)
        self.assertEqual(res, res.lower())

    def test_normalize_path_case_insensitive(self):
        """Два пути отличающихся регистром -> одинаковый нормализованный."""
        a = "C:\\Test\\VIDEO.MP4"
        b = "C:\\test\\video.mp4"
        self.assertEqual(self.normalize_path(a), self.normalize_path(b))

    def test_normalize_path_empty_safe(self):
        """Пустой/None ввод не должен крашить (fallback)."""
        try:
            self.normalize_path("")
        except Exception:
            self.fail("normalize_path('') вызвал исключение")

    def test_normalize_path_forward_backslash(self):
        """Оба типа слэшей должны давать одинаковый результат."""
        a = "C:/a/b/file.mp4"
        b = "C:\\a\\b\\file.mp4"
        self.assertEqual(self.normalize_path(a), self.normalize_path(b))

    def test_supported_ext_common(self):
        """Популярные форматы должны быть в списке."""
        for ext in [".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"]:
            self.assertIn(ext, self.SUPPORTED_EXT, f"Отсутствует {ext}")

    def test_supported_ext_lowercase_only(self):
        """Форматы в нижнем регистре, сравнение должно работать правильно."""
        self.assertIn(".MP4".lower(), self.SUPPORTED_EXT)
        self.assertNotIn(".txt", self.SUPPORTED_EXT)




class TestConfigManager(unittest.TestCase):
    """Тесты менеджера настроек."""

    def setUp(self):
        # Временный каталог (удаляется автоматически)
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _with_app_dir(self, app_dir: Path):
        """Патчим get_app_dir, чтобы ConfigManager работал во временной папке."""
        return patch("extractor.get_app_dir", return_value=app_dir)

    def test_defaults_created(self):
        """При первом запуске создаются дефолтные настройки."""
        with self._with_app_dir(self.tmpdir):
            from extractor import ConfigManager
            cm = ConfigManager()
            self.assertEqual(cm.get("theme"), "dark")
            self.assertEqual(cm.get("output_mode"), "source")
            self.assertEqual(cm.get("custom_output_path"), "")

    def test_config_json_created(self):
        """После вызова save() появляется config.json."""
        with self._with_app_dir(self.tmpdir):
            from extractor import ConfigManager
            cm = ConfigManager()
            cm.set("theme", "light")
            self.assertTrue((self.tmpdir / "config.json").exists())

    def test_set_get_persistence(self):
        """Сохраняем -> создаём новый экземпляр -> значения читаются."""
        with self._with_app_dir(self.tmpdir):
            from extractor import ConfigManager
            cm1 = ConfigManager()
            cm1.set("theme", "light")
            cm1.set("custom_output_path", "D:/audio_out")

            # Создаём новый ConfigManager — должен прочитать из файла
            cm2 = ConfigManager()
            self.assertEqual(cm2.get("theme"), "light")
            self.assertEqual(cm2.get("custom_output_path"), "D:/audio_out")

    def test_unknown_key_returns_default(self):
        """Несуществующий ключ -> возвращаем None или дефолт, не падаем."""
        with self._with_app_dir(self.tmpdir):
            from extractor import ConfigManager
            cm = ConfigManager()
            res = cm.get("totally_unknown_key_12345")
            self.assertIsNone(res)

    def test_corrupted_config_returns_defaults(self):
        """Битый config.json не крашит приложение."""
        (self.tmpdir / "config.json").write_text("{ не json вообще ][", encoding="utf-8")
        with self._with_app_dir(self.tmpdir):
            from extractor import ConfigManager
            cm = ConfigManager()
            self.assertEqual(cm.get("theme"), "dark")
            self.assertEqual(cm.get("output_mode"), "source")




class TestAppColors(unittest.TestCase):
    """Тесты цветов и QSS-генерации."""

    def test_colors_classes_exist(self):
        """Dark/Light палитры должны быть определены."""
        from ui_colors import AppColors
        self.assertTrue(hasattr(AppColors, "Dark"))
        self.assertTrue(hasattr(AppColors, "Light"))

    def test_colors_have_required_fields(self):
        """Каждая палитра имеет обязательные цвета."""
        from ui_colors import AppColors
        for pal in (AppColors.Dark, AppColors.Light):
            for attr in ("BG_MAIN", "BG_WIDGET", "BG_SURFACE", "TEXT_PRIMARY",
                         "TEXT_SECONDARY", "BORDER"):
                self.assertTrue(hasattr(pal, attr), f"У палитры нет {attr}")
                v = getattr(pal, attr)
                self.assertTrue(v.startswith("#"), f"{attr} не hex: {v}")

    def test_get_stylesheet_returns_string(self):
        """Функция get_stylesheet для обеих тем возвращает непустой str."""
        from ui_colors import get_stylesheet
        for theme in ("dark", "light"):
            qss = get_stylesheet(theme)
            self.assertIsInstance(qss, str)
            self.assertGreater(len(qss), 500)
            # QSS содержит ключевые селекторы
            self.assertIn("QMainWindow", qss)
            self.assertIn("QPushButton", qss)
            self.assertIn("QListWidget", qss)

    def test_accent_colors_sane(self):
        """Акцентные цвета приложения (сиреневый) не пустые."""
        from ui_colors import AppColors
        for attr in ("ACCENT_PRIMARY", "ACCENT_HOVER", "ACCENT_PRESSED",
                     "ACCENT_LIGHT"):
            v = getattr(AppColors, attr, None)
            self.assertTrue(v and v.startswith("#"), f"Accent {attr} битый")




class TestGUIComponentsSanity(unittest.TestCase):
    """Sanity тесты GUI-компонентов без создания главного цикла Qt."""

    @classmethod
    def setUpClass(cls):
        """Создаём QApplication ОДИН раз на весь класс тестов."""
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError as e:
            raise unittest.SkipTest(f"PySide6 не установлен: {e}")

        cls._app = QApplication.instance() or QApplication(sys.argv)


    def test_file_item_widget_creation(self):
        """Создание FileItemWidget не падает."""
        from ui import FileItemWidget
        # Создадим временный файл (чтобы p.stat() работал)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 1024)
            tmp = f.name
        try:
            w = FileItemWidget(tmp, on_delete=lambda p: None)
            self.assertIsNotNone(w)
            self.assertEqual(w.file_path, tmp)
            # _state инициализирован как PENDING
            self.assertEqual(w.state, w.STATE_PENDING)
            # set_state не падает
            w.set_state(w.STATE_SUCCESS, "OK")
            self.assertEqual(w.state, w.STATE_SUCCESS)
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass

    def test_file_item_widget_missing_file(self):
        """Создание с несуществующим путём — должно выжить."""
        from ui import FileItemWidget
        fake = "Z:\\does_not_exist\\fake_video_12345.mp4"
        try:
            w = FileItemWidget(fake, on_delete=lambda p: None)
            # Не должно упасть на stat()
        except Exception as e:
            self.fail(f"FileItemWidget упал на несуществующем файле: {e}")


    def test_drag_drop_frame_has_signal(self):
        """DragDropFrame имеет сигнал filesDropped."""
        from ui import DragDropFrame
        from PySide6.QtCore import Signal
        self.assertTrue(hasattr(DragDropFrame, "filesDropped"))


    def test_main_window_normalize_indicator_helpers(self):
        """Хелперы индикатора: установить цвет + моргание тайкл-методы не падают."""
        # Используем настоящий ConfigManager во временной папке
        from extractor import ConfigManager
        tmp = tempfile.TemporaryDirectory()
        try:
            with patch("extractor.get_app_dir", return_value=Path(tmp.name)):
                from ui import MainWindow
                cm = ConfigManager()
                w = MainWindow(cm)
                w._set_indicator_color("#FFFFFF")
                w._blink_tick()
                w._blink_tick()
                w._reset_indicator()
                w._stop_indicator_blink()
                w.close()
        finally:
            tmp.cleanup()

    def test_main_window_title_colors_not_crash(self):
        """_apply_title_colors для обеих тем не падает."""
        from extractor import ConfigManager
        tmp = tempfile.TemporaryDirectory()
        try:
            with patch("extractor.get_app_dir", return_value=Path(tmp.name)):
                from ui import MainWindow
                cm = ConfigManager()
                w = MainWindow(cm)
                for theme in ("dark", "light"):
                    w._current_theme = theme
                    w._apply_title_colors()  # Не должно упасть
                w.close()
        finally:
            tmp.cleanup()




class TestAudioExtractorMocks(unittest.TestCase):
    pass


class TestAudioExtractorLogic(unittest.TestCase):

    def _make_tmp_folder(self):
        tmp = tempfile.TemporaryDirectory()
        return tmp, Path(tmp.name)

    def test_extractor_creation(self):
        """Создание AudioExtractor без запуска — работает."""
        from extractor import ConfigManager, AudioExtractor
        tmp = tempfile.TemporaryDirectory()
        try:
            with patch("extractor.get_app_dir", return_value=Path(tmp.name)):
                cm = ConfigManager()
                ex = AudioExtractor(cm)
                self.assertFalse(ex.is_running())
                self.assertIsNotNone(ex.log_file_path())
                self.assertFalse(ex._should_stop_check())
        finally:
            tmp.cleanup()

    def test_ffprobe_parser_recovery(self):
        """_get_audio_stream_indices возвращает None/список без краша."""
        from extractor import ConfigManager, AudioExtractor
        tmp = tempfile.TemporaryDirectory()
        try:
            with patch("extractor.get_app_dir", return_value=Path(tmp.name)):
                cm = ConfigManager()
                ex = AudioExtractor(cm)

                # Проверяем случай битого ffprobe
                bad_res = MagicMock()
                bad_res.returncode = 1
                bad_res.stdout = ""
                bad_res.stderr = "some error"
                with patch("subprocess.run", return_value=bad_res):
                    idx = ex._get_audio_stream_indices(Path("fake.mp4"))
                    self.assertIsNone(idx)

                # Нормальный ffprobe: найдено 2 аудио-дорожки
                good_res = MagicMock()
                good_res.returncode = 0
                good_res.stdout = "1\n2\n"
                good_res.stderr = ""
                with patch("subprocess.run", return_value=good_res):
                    idx = ex._get_audio_stream_indices(Path("fake.mp4"))
                    self.assertEqual(idx, [1, 2])
        finally:
            tmp.cleanup()

    def test_extract_copy_ok_case(self):
        """_extract_copy с успехом ffmpeg возвращает (True, 'OK')."""
        from extractor import ConfigManager, AudioExtractor
        tmp = tempfile.TemporaryDirectory()
        try:
            with patch("extractor.get_app_dir", return_value=Path(tmp.name)):
                cm = ConfigManager()
                ex = AudioExtractor(cm)

                out_file = Path(tmp.name) / "track1.m4a"
                out_file.write_bytes(b"fake audio content 123")

                ok = MagicMock()
                ok.returncode = 0
                ok.stderr = ""
                with patch("subprocess.run", return_value=ok):
                    success, info = ex._extract_copy(
                        Path("in.mp4"), 1, out_file
                    )
                    self.assertTrue(success)
                    self.assertEqual(info, "OK")
        finally:
            tmp.cleanup()

    def test_extract_copy_returns_error_string(self):
        """_extract_copy при падении ffmpeg возвращает False+сообщение."""
        from extractor import ConfigManager, AudioExtractor
        tmp = tempfile.TemporaryDirectory()
        try:
            with patch("extractor.get_app_dir", return_value=Path(tmp.name)):
                cm = ConfigManager()
                ex = AudioExtractor(cm)

                bad = MagicMock()
                bad.returncode = 1
                bad.stderr = "moov atom not found\n"
                with patch("subprocess.run", return_value=bad):
                    success, info = ex._extract_copy(
                        Path("broken.mp4"), 0, Path("out.m4a")
                    )
                    self.assertFalse(success)
                    self.assertIn("битый", info.lower())
        finally:
            tmp.cleanup()

    def test_check_ffmpeg_available_mock_ok(self):
        """check_ffmpeg_available -> True когда оба инструмента на месте."""
        good = MagicMock()
        good.returncode = 0
        with patch("subprocess.run", return_value=good):
            from extractor import check_ffmpeg_available
            ok, msg = check_ffmpeg_available()
            self.assertTrue(ok)
            self.assertEqual(msg, "OK")

    def test_check_ffmpeg_available_mock_missing(self):
        """check_ffmpeg_available -> False когда ffmpeg отсутствует."""
        with patch("subprocess.run", side_effect=FileNotFoundError("не найден")):
            from extractor import check_ffmpeg_available
            ok, msg = check_ffmpeg_available()
            self.assertFalse(ok)
            # Сообщение пользователю достаточно длинное
            self.assertGreater(len(msg), 100)


class TestExtractionEndToEndMocked(unittest.TestCase):
    """Запуск extractor.start_extraction с моканными subprocess."""

    def test_run_two_videos_all_success(self):
        """Два 'видео' -> успешно обрабатываются."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication

        # Гарантируем существование QCoreApplication для Signal
        app = QCoreApplication.instance() or QApplication(sys.argv)

        tmp = tempfile.TemporaryDirectory()
        tmpdir = Path(tmp.name)

        # Два фейковых видео-файла
        vid1 = tmpdir / "a.mp4"
        vid2 = tmpdir / "b.mkv"
        for v in (vid1, vid2):
            v.write_bytes(b"0" * 1024)

        with patch("extractor.get_app_dir", return_value=tmpdir):
            from extractor import ConfigManager, AudioExtractor

            cm = ConfigManager()
            ex = AudioExtractor(cm)

            # Сигналы
            results = {"done": None, "finished_count": 0}
            def _on_finished(r):
                results["done"] = r
            ex.all_finished.connect(_on_finished)

            # Мокаем:
            # 1) ffprobe -> каждый файл имеет 2 аудио дорожки
            # 2) ffmpeg (copy) -> успешно
            ffprobe_res = MagicMock()
            ffprobe_res.returncode = 0
            ffprobe_res.stdout = "1\n2\n"
            ffprobe_res.stderr = ""

            ffmpeg_ok = MagicMock()
            ffmpeg_ok.returncode = 0
            ffmpeg_ok.stderr = ""

            # Внутри _process_single_file сначала ffprobe, затем несколько раз
            # ffmpeg. Самый простой мок: всегда возвращаем успех,
            # + пишем в выходной файл, чтобы проверка размера прошла.
            def _runner(cmd, **kwargs):
                if cmd[0] == "ffprobe":
                    return ffprobe_res
                # ffmpeg: создаём выходной файл
                out = Path(cmd[-1])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"ok")
                return ffmpeg_ok

            with patch("subprocess.run", side_effect=_runner):
                ex.start_extraction([str(vid1), str(vid2)])

        # Проверка: оба файла обработаны успешно
        self.assertIsNotNone(results["done"])
        for fp, (ok, info) in results["done"].items():
            self.assertTrue(ok, f"{fp} не обработан: {info}")
        # 4 всего дорожки (2 файла * 2 трека) каждая извлечена
        self.assertEqual(len(results["done"]), 2)
        tmp.cleanup()



if __name__ == "__main__":
    unittest.main(verbosity=2)
