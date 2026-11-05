import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON_IN_ROOT = ROOT / "Gengar.ico"
PORTABLE_DIR = ROOT / "AudioTrackExtractor"
BUILD_DIR = ROOT / "build"
OUTPUT_EXE = PORTABLE_DIR / "AudioTrackExtractor.exe"


def banner(text: str, color: str = "purple"):

    colors = {
        "purple": "\033[95m",
        "cyan":   "\033[96m",
        "green":  "\033[92m",
        "yellow": "\033[93m",
        "red":    "\033[91m",
        "bold":   "\033[1m",
        "reset":  "\033[0m",
    }
    c = colors.get(color, "")
    bar = "=" * 70
    print(f"\n{c}{colors['bold']}{bar}{colors['reset']}")
    print(f"{c}{colors['bold']}  {text}{colors['reset']}")
    print(f"{c}{colors['bold']}{bar}{colors['reset']}\n")


def step(text: str):
    print(f"\n>>> {text}")


def error_exit(msg: str):
    banner("❌ ОШИБКА СБОРКИ", "red")
    print(f"    {msg}\n")
    sys.exit(1)


# Проверки перед сборкой

def check_prerequisites():
    banner("1/5  ПРОВЕРКА ПЕРЕД СБОРКОЙ", "cyan")

    # Gengar.ico в корне? (PyInstaller читает его отсюда чтобы вшить в .exe)
    if not ICON_IN_ROOT.is_file():
        error_exit(
            f"Не найден файл иконки: {ICON_IN_ROOT}\n"
            f"    Скопируй его из Portable/Gengar.ico в корень проекта."
        )
    step(f"✅ Gengar.ico найден: {ICON_IN_ROOT}")

    # Папка Portable существует?
    if not PORTABLE_DIR.is_dir():
        error_exit(f"Папка Portable не найдена: {PORTABLE_DIR}")
    step(f"✅ Папка Portable найдена: {PORTABLE_DIR}")

    # PyInstaller доступен?
    try:
        import PyInstaller  # noqa
        step(f"✅ PyInstaller найден: v{PyInstaller.__version__}")
    except ImportError:
        error_exit(
            "PyInstaller не установлен.\n"
            "    Запусти:  python -m pip install --user PyInstaller PySide6"
        )



# Запуск PyInstaller с правильными флагами

def run_pyinstaller():
    banner("2/5  ЗАПУСК PYINSTALLER", "cyan")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "AudioTrackExtractor",
        "--icon", str(ICON_IN_ROOT),
        "--add-data", f"{ICON_IN_ROOT};.",
        "--distpath", str(PORTABLE_DIR),
        "--workpath", str(BUILD_DIR),
        str(ROOT / "main.py"),
    ]

    step("Команда сборки:")
    print("    " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    print()

    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        error_exit(
            f"PyInstaller завершился с ошибкой (код {result.returncode}).\n"
            f"    Читай логи выше, там написано в чём проблема."
        )



# Проверка что .exe создан

def verify_output():
    banner("3/5  ПРОВЕРКА РЕЗУЛЬТАТА", "cyan")

    if not OUTPUT_EXE.is_file():
        error_exit(f"После сборки не найден .exe: {OUTPUT_EXE}")

    size_mb = OUTPUT_EXE.stat().st_size / (1024 * 1024)
    step(f"✅ .exe собран успешно!")
    print(f"    Путь:   {OUTPUT_EXE}")
    print(f"    Размер: {size_mb:.1f} МБ")



# Уборка мусора

def cleanup_spec():
    banner("4/5  УБОРКА", "cyan")

    spec = ROOT / "AudioTrackExtractor.spec"
    if spec.is_file():
        try:
            # Оставляем spec-файл — не удаляем, вдруг пользователь его правит руками.
            # Просто говорим что он есть.
            step(f"ℹ️  Файл конфигурации сборки: {spec.name} (оставлен)")
        except Exception:
            pass

    if BUILD_DIR.is_dir():
        step(f"ℹ️  Временные файлы сборки: {BUILD_DIR.name}/ (можно удалить если не нужны)")



# Готово

def done():
    banner("5/5  СБОРКА ЗАВЕРШЕНА УСПЕШНО 🎉", "green")

    print("    📦 Готовый файл:")
    print(f"        {OUTPUT_EXE}")
    print()
    print("    🔧 Рядом уже лежат (portable-режим):")
    print(f"        - {PORTABLE_DIR / 'Gengar.ico'} (иконка для окна приложения)")
    print(f"        - {PORTABLE_DIR / 'ffmpeg.exe'}")
    print(f"        - {PORTABLE_DIR / 'ffprobe.exe'}")
    print()
    print("    🚀 Запусти AudioTrackExtractor.exe и проверяй!")
    print("    💡 Если иконка в проводнике не обновилась — смени папку/переименуй .exe")
    print()


# --------------------------------------------------------------------------
def main():
    print()
    print("  ╔══════════════════════════════════════════════════════════════════╗")
    print("  ║       Audio Track Extractor  —  BUILD SCRIPT  (portable)        ║")
    print("  ║              Просто нажми Run в PyCharm / python build.py       ║")
    print("  ╚══════════════════════════════════════════════════════════════════╝")

    try:
        check_prerequisites()
        run_pyinstaller()
        verify_output()
        cleanup_spec()
        done()
    except KeyboardInterrupt:
        banner("⏹️  СБОРКА ОТМЕНЕНА ПОЛЬЗОВАТЕЛЕМ", "yellow")
        sys.exit(130)


if __name__ == "__main__":
    main()
