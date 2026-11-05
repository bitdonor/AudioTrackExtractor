<img width="60" height="60" alt="IMG_5913 копия" src="https://github.com/user-attachments/assets/fa2b9d18-8a44-4934-84d8-06c01f65d859" />
<b>AUDIO TRACK EXTRACTOR</b>

Десктопное приложение для **извлечения аудиодорожек из видеофайлов**. Достаёт **все** звуковые дорожки из файла сразу — каждая сохраняется отдельным файлом.

![Platform](https://img.shields.io/badge/platform-Windows-blue)    ![Python](https://img.shields.io/badge/python-3.10%2B-blue)   ![PySide6](https://img.shields.io/badge/UI-PySide6-green)   ![FFmpeg](https://img.shields.io/badge/powered%20by-FFmpeg-orange)

<img width="1024" height="572" alt="image" src="https://github.com/user-attachments/assets/2a6c74eb-917f-40d2-9b1f-e6940fa80430" />

## ✨ Возможности

- 🎧 **Извлекает все аудиодорожки** из видео 
- ⚡ **Без перекодировки** — по умолчанию поток копируется как есть (быстро, без потери качества)
- 🔁 **Fallback в WAV** — если кодек несовместим с m4a, дорожка сохраняется в WAV (PCM 16-bit, без потерь)
- 🖱 **Drag & Drop** — файлы можно просто перетащить в окно
- 🚀 **Параллельная обработка** — файлы обрабатываются в пуле потоков, интерфейс не подвисает
- 📂 **Гибкий выбор места сохранения** — рядом с видео или в свою папку
- 🌙 **Тёмная и светлая темы**
- 📄 **Лог операций** в файл `extractor.log`
- 📦 **Portable-сборка** в один `.exe`

### Поддерживаемые форматы видео

`.mp4` · `.mkv` · `.mov` · `.avi` · `.webm` · `.m4v`

---

## 📥 СКАЧАТЬ **[Releases](../../releases)**


---

## 📦 Требования

| Компонент | Версия | Обязательно |
|-----------|--------|-------------|
| **FFmpeg** (вместе с `ffprobe`) | любая актуальная | ✅ Да |
| Python (для запуска из исходников) | 3.10+ | только для разработки |
| PySide6 | ≥ 6.5.0 | только для разработки |

**FFmpeg должен быть доступен в системной переменной `PATH`.** Если он не найден, приложение покажет подсказку с инструкцией по установке.

Как установить FFmpeg:
1. Скачай сборку с https://www.gyan.dev/ffmpeg/builds/
2. Распакуй, например, в `C:\ffmpeg`
3. Добавь `C:\ffmpeg\bin` в переменную среды `PATH`
4. Перезапусти приложение

---

## 🚀 Запуск из исходников

```bash
# 1. Клонировать репозиторий
git clone <URL-репозитория>
cd "AT Extractor"

# 2. Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить
python main.py
```

---

## 🛠 Сборка в .exe

Для сборки используется скрипт `build.py`:

```bash
pip install pyinstaller
python build.py
```

Готовый файл появится в папке `AudioTrackExtractor/`:

```
AudioTrackExtractor/
├── AudioTrackExtractor.exe
├── Gengar.ico
├── ffmpeg.exe
└── ffprobe.exe
```

---

## 🎧 Как пользоваться

1. **Добавь видео** — перетащи файлы в окно или выбери через диалог.
2. **Выбери режим сохранения**:
   - *рядом с видео* — папка с аудио создастся рядом с исходником;
   - *своя папка* — укажи произвольный путь.
3. Нажми **«🎵 Извлечь звук»**.
4. Результат появится в папке `<имя_видео>_audio`:

```
my_movie_audio/
├── track1.m4a
├── track2.m4a
└── track3.m4a
```

При возникновении проблем с отдельной дорожкой она сохранится как `trackN.wav`.

---

## ⚙️ Настройки

Настройки хранятся в `config.json` рядом с приложением (portable-режим):

```json
{
    "theme": "dark",
    "output_mode": "source",
    "custom_output_path": ""
}
```

| Ключ | Значения | Описание |
|------|----------|----------|
| `theme` | `dark` / `light` | Тема интерфейса |
| `output_mode` | `source` / `custom` | Куда сохранять результат |
| `custom_output_path` | путь | Папка при `output_mode = custom` |

---

## 📄 Логи

Все операции записываются в `extractor.log` рядом с приложением — удобно для диагностики ошибок.

---

## 🧱 Технологии

- **Python 3.10+**
- **PySide6 (Qt)** — графический интерфейс
- **FFmpeg / ffprobe** — извлечение и анализ аудиопотоков
- **PyInstaller** — сборка portable `.exe`

---

## 📁 Структура проекта

```
AT Extractor/
├── main.py                    # точка входа
├── ui.py                      # интерфейс (окно, drag&drop, список файлов)
├── ui_colors.py               # цветовые палитры и стили (QSS)
├── extractor.py               # логика извлечения аудио + настройки
├── build.py                   # скрипт сборки в .exe
├── test_app.py                # автотесты
├── requirements.txt           # зависимости
├── config.json                # пользовательские настройки
└── Gengar.ico                 # иконка приложения
```


