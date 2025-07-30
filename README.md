# NovelRuntime
NovelForge — движок для создания визуальных новел и интерактивных историй
---

**NovelForge** — это лёгкий и гибкий движок для создания и запуска **интерактивных визуальных новел** с использованием веб-технологий (HTML, CSS, JavaScript) и нативного оконного интерфейса на Python. Подходит для писателей, педагогов, студентов и разработчиков, кто хочет создавать истории без глубокого программирования.

> 🚀 Простота, кроссплатформенность и автоматическая оптимизация под вашу видеокарту.

---

## 🌟 Особенности

- ✅ **HTML-сцены** — создавайте сцены с помощью HTML, CSS и JS
- ✅ **Нативное окно** — PySide6 (Qt) для красивого и быстрого интерфейса
- ✅ **Автоматическое определение GPU** — NVIDIA, AMD, Intel или слабый ПК (`potato_mode`)
- ✅ **Встроенная поддержка аудио, видео и анимации**
- ✅ **Модульная система** — легко расширять через Python-модули
- ✅ **Поддержка автономного запуска** (включая `.exe` через PyInstaller)
- ✅ **API для управления** — выход, настройки, конфигурация
- ✅ **Создание проекта за секунды** — `--new-project`

---

## 📦 Архитектура проекта

```
NovelForge/
├── templates/              # Ваши HTML-сцены (index.html, game.html и др.)
├── static/                 # Статика: стили, изображения, звуки, видео
├── bin/
│   ├── configs/            # Конфиги (runtime_conf.ini)
│   └── modules/            # Python-модули (музыка, API и т.д.)
├── run_runtime.py          # Главный скрипт запуска
└── requirements.txt        # Зависимости
```

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Создание нового проекта

```bash
python run_runtime.py --new-project
```

Будет создана базовая структура с `index.html`, `style.css` и конфигом.

### 3. Запуск движка

```bash
python run_runtime.py
```

Откроется окно с вашей визуальной новелой.

---

## 🔧 Режимы запуска

| Флаг | Описание |
|------|---------|
| `--new-project` | Создаёт новый проект с шаблонами |
| (без флагов) | Запускает окно + сервер |
| `--only-server` | Только Flask-сервер (для отладки) |

> ⚙️ Режим работы можно настроить в `bin/configs/runtime_conf.ini` → `[Runtime] mode = window\|server\|both`

---

## 🖼 Как создавать сцены?

Просто добавьте HTML-файл в папку `templates/`:

```html
<!-- templates/my_scene.html -->
<!DOCTYPE html>
<html>
<head>
  <title>Сцена 1</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <div class="scene" style="background: url('/static/bg/cafe.jpg') center;">
    <p>— Привет, — сказал он, не глядя на меня.</p>
    <button onclick="window.location.href='/templates/next_scene.html'">Ответить</button>
  </div>
</body>
</html>
```

Используйте `/static/` для изображений, звуков и видео.

---

## 🧩 Модули (расширения)

Добавляйте свои Python-модули в `bin/modules/`:

```python
# bin/modules/speech.py
def register(app):
    @app.route('/api/speak/<text>')
    def speak(text):
        # Ваш код озвучки
        return {"status": "ok", "played": text}
```

Движок автоматически загрузит и подключит модуль.

---

## ⚙️ Конфигурация

Файл: `bin/configs/runtime_conf.ini`

```ini
[Window]
Width = 1280
Height = 720
Fullscreen = False

[Server]
Host = 127.0.0.1
Port = 5000
Debug = True

[Runtime]
mode = both        ; window, server, both
server_console = False
```

---

## 🎵 Музыка и звук

Поддерживается:
- Автовоспроизведение аудио
- Управление громкостью через API
- Циклическое воспроизведение (настраивается в модулях)

---

## 🖥 Совместимость

| ОС | Поддержка |
|----|----------|
| Windows | ✅ |
| Linux | ✅ |
| macOS | ✅ (ограниченно, требуется QtWebEngine) |

> 💡 Для сборки `.exe` используйте `pyinstaller`.

---

## 📡 API

Доступные эндпоинты:

| Метод | URL | Описание |
|------|-----|---------|
| GET | `/system/exit` | Закрывает приложение |
| GET | `/system/gpu-info` | Информация о видеокарте |
| GET | `/config/get` | Все настройки |
| GET | `/config/section/<name>` | Конкретная секция |
| POST | `/config/set` | Изменение настройки (JSON) |

---

## 🧰 Требования

- Python 3.8+
- Flask
- PySide6 (Qt6)
- QtWebEngine

### Установка:

```bash
pip install flask PySide6
```

---

## 📄 Лицензия

MIT — свободное использование, модификация, распространение.

---

## 🤝 Вклад

Приветствуются:
- Pull requests
- Идеи для новых модулей
- Шаблоны сцен
- Документация и переводы

---

> **NovelForge** — инструмент для творчества.  
> Создавайте истории. Меняйте мир. Без кода. Без границ.

---

**Создано с ❤️ для молодёжи, педагогов и всех, кто верит в силу рассказа.**

--- 
