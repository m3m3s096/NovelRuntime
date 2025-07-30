import sys
import threading
import webbrowser
import configparser
import argparse
import shutil
from flask import Flask, render_template, send_from_directory, abort
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer
from PySide6.QtGui import QKeyEvent
import os
import subprocess
import importlib.util
import glob
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget
import platform
import multiprocessing
import time

# Пути к папкам templates и static
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Определяем, запущено ли приложение из скомпилированного exe
if getattr(sys, 'frozen', False):
    # Приложение скомпилировано - используем _internal
    BASE_DIR = os.path.dirname(sys.executable)
    INTERNAL_DIR = os.path.join(BASE_DIR, '_internal')
    TEMPLATES_DIR = os.path.join(INTERNAL_DIR, 'templates')
    STATIC_DIR = os.path.join(INTERNAL_DIR, 'static')
    CONFIG_DIR = os.path.join(INTERNAL_DIR, 'bin', 'configs')
    PROJECT_JSON = os.path.join(INTERNAL_DIR, 'project.json')
else:
    # Приложение запущено из исходников
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
    CONFIG_DIR = os.path.join(BASE_DIR, 'bin', 'configs')
    PROJECT_JSON = os.path.join(BASE_DIR, 'project.json')

print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"📁 TEMPLATES_DIR: {TEMPLATES_DIR}")
print(f"📁 STATIC_DIR: {STATIC_DIR}")
print(f"📁 CONFIG_DIR: {CONFIG_DIR}")
print(f"📁 PROJECT_JSON: {PROJECT_JSON}")

# Чтение единого конфига
config = configparser.ConfigParser()
config_file = os.path.join(CONFIG_DIR, 'runtime_conf.ini')

# Проверяем существование файла конфигурации
if os.path.exists(config_file):
    config.read(config_file, encoding='utf-8')
    print(f"📋 Загружен конфигурационный файл: {config_file}")
else:
    print(f"⚠️ Конфигурационный файл не найден: {config_file}")
    print("📋 Используются настройки по умолчанию")

potato_settings = config.getboolean('Window', 'Potato', fallback=True)

# Функция для определения типа видеокарты
def get_gpu_type():
    try:
        if platform.system() == "Windows":
            # Используем PowerShell для получения информации о GPU
            result = subprocess.run(
                ["powershell", "-Command", "Get-WmiObject -Class Win32_VideoController | Select-Object Name | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                gpu_info = result.stdout.strip()
                gpu_name = gpu_info.lower()
                
                if "nvidia" in gpu_name:
                    return "nvidia"
                elif "amd" in gpu_name or "radeon" in gpu_name:
                    return "amd"
                elif "intel" in gpu_name:
                    return "intel"
                else:
                    return "intel"  # По умолчанию
            else:
                return "intel"  # По умолчанию
        else:
            # Для Linux и других систем
            try:
                result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    gpu_info = result.stdout.lower()
                    if "nvidia" in gpu_info:
                        return "nvidia"
                    elif "amd" in gpu_info or "radeon" in gpu_info:
                        return "amd"
                    elif "intel" in gpu_info:
                        return "intel"
            except:
                pass
            return "intel"  # По умолчанию
    except:
        return "intel"  # По умолчанию

# Определяем тип GPU и устанавливаем соответствующие флаги
gpu_type = get_gpu_type()

if gpu_type == "nvidia":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu --enable-accelerated-video-decode --disable-gpu-sandbox"
    print("🎮 Используется NVIDIA GPU с аппаратным ускорением")
    os.environ["QT_OPENGL"] = "desktop"
elif gpu_type == "amd":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu --enable-accelerated-video-decode --disable-gpu-sandbox"
    print("🎮 Используется AMD GPU с аппаратным ускорением")
elif gpu_type == "intel":
    # Intel GPU с OpenGL рендерингом
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu --use-gl=desktop --disable-gpu-sandbox --enable-accelerated-video-decode"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_OPENGL"] = "desktop"
    print("🎮 Используется Intel GPU с OpenGL рендерингом")
else:  # Неизвестная видеокарта
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-software-rasterizer"
    os.environ["QT_QUICK_BACKEND"] = "software"
    print("🎮 Используется программный рендеринг (неизвестная видеокарта)")

def create_new_project():
    """Создает новый проект NovelForge с базовой структурой"""
    print("🚀 Создание нового проекта NovelForge...")
    
    # Определяем базовую папку для создания проекта
    if getattr(sys, 'frozen', False):
        # Если запущено из exe, создаем в папке с exe
        project_base = os.path.dirname(sys.executable)
    else:
        # Если запущено из исходников, создаем в текущей папке
        project_base = BASE_DIR
    
    print(f"📁 Базовая папка проекта: {project_base}")
    
    # Создаем основные директории
    directories = [
        os.path.join(project_base, 'templates'),
        os.path.join(project_base, 'templates', 'game'),
        os.path.join(project_base, 'static'),
        os.path.join(project_base, 'static', 'sfx'),
        os.path.join(project_base, 'static', 'sprites'),
        os.path.join(project_base, 'static', 'media'),
        os.path.join(project_base, 'bin'),
        os.path.join(project_base, 'bin', 'configs'),
        os.path.join(project_base, 'bin', 'modules')
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Создана папка: {directory}")
    
    # Создаем базовый конфигурационный файл
    config_content = """[Window]
Potato = True
Width = 1280
Height = 720
Fullscreen = False

[Server]
Host = 127.0.0.1
Port = 5000
Debug = True

[Graphics]
OpenGL = True
HardwareAcceleration = True
VideoCodec = auto

[Audio]
MusicVolume = 0.7
SFXVolume = 0.8
AutoPlay = True

[System]
AutoSave = True
LogLevel = INFO

[Runtime]
mode = both
server_console = False
"""
    
    config_file = os.path.join(project_base, 'bin', 'configs', 'runtime_conf.ini')
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    print(f"⚙️ Создан конфигурационный файл: {config_file}")
    
    # Создаем базовый index.html
    index_content = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NovelForge - Главное меню</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <div class="menu">
            <h1>🎮 NovelForge</h1>
            <div class="menu-buttons">
                <button onclick="startGame()" class="menu-btn">🎬 НАЧАТЬ ИГРУ</button>
                <button onclick="openSettings()" class="menu-btn">⚙️ НАСТРОЙКИ</button>
                <button onclick="exitGame()" class="menu-btn">🚪 ВЫХОД</button>
            </div>
        </div>
    </div>
    
    <script>
        function startGame() {
            window.location.href = '/game?startgame';
        }
        
        function openSettings() {
            window.location.href = '/settings';
        }
        
        function exitGame() {
            if (confirm('Вы уверены, что хотите выйти?')) {
                window.location.href = '/system/exit';
            }
        }
    </script>
</body>
</html>"""
    
    index_file = os.path.join(project_base, 'templates', 'index.html')
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"📄 Создан index.html: {index_file}")
    
    # Создаем базовый CSS
    css_content = """body {
    margin: 0;
    padding: 0;
    font-family: 'Arial', sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.container {
    text-align: center;
    color: white;
}

.menu h1 {
    font-size: 3em;
    margin-bottom: 2em;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}

.menu-buttons {
    display: flex;
    flex-direction: column;
    gap: 1em;
}

.menu-btn {
    padding: 1em 2em;
    font-size: 1.2em;
    border: none;
    border-radius: 10px;
    background: rgba(255,255,255,0.2);
    color: white;
    cursor: pointer;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}

.menu-btn:hover {
    background: rgba(255,255,255,0.3);
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}"""
    
    css_file = os.path.join(project_base, 'static', 'style.css')
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(css_content)
    print(f"🎨 Создан style.css: {css_file}")
    
    print("\n🎉 Проект создан успешно!")
    print("💡 Для запуска выполните: python run_runtime.py")

def create_minimal_project():
    """Создает минимальный проект NovelForge с базовой структурой"""
    print("🚀 Создание минимального проекта NovelForge...")
    
    # Создаем только необходимые директории
    directories = [
        'templates',
        'static',
        'bin/configs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Создана папка: {directory}")
    
    # Создаем минимальный конфигурационный файл
    config_content = """[Window]
Potato = True
Width = 1280
Height = 720
Fullscreen = False

[Server]
Host = 127.0.0.1
Port = 5000
Debug = True

[Runtime]
mode = both
server_console = False
"""
    
    with open('bin/configs/runtime_conf.ini', 'w', encoding='utf-8') as f:
        f.write(config_content)
    print("⚙️ Создан конфигурационный файл: bin/configs/runtime_conf.ini")
    
    # Создаем минимальный index.html
    index_content = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>NovelForge</title>
    <style>
        body { margin: 0; padding: 0; font-family: Arial; background: linear-gradient(45deg, #667eea, #764ba2); color: white; height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { text-align: center; }
        h1 { font-size: 3em; margin-bottom: 30px; }
        button { padding: 15px 30px; font-size: 1.2em; background: rgba(255,255,255,0.2); border: 2px solid white; color: white; cursor: pointer; margin: 10px; border-radius: 10px; }
        button:hover { background: rgba(255,255,255,0.3); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 NovelForge</h1>
        <button onclick="startGame()">🎬 НАЧАТЬ ИГРУ</button>
        <button onclick="exitGame()">🚪 ВЫХОД</button>
    </div>
    <script>
        function startGame() { window.location.href = '/game'; }
        function exitGame() { if(confirm('Выйти?')) window.close(); }
    </script>
</body>
</html>"""
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_content)
    print("📄 Создан главный файл: templates/index.html")
    
    # Создаем минимальный game.html
    game_content = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>NovelForge - Игра</title>
    <style>
        body { margin: 0; padding: 20px; font-family: Arial; background: linear-gradient(45deg, #667eea, #764ba2); color: white; min-height: 100vh; }
        .game-content { max-width: 800px; margin: 0 auto; text-align: center; }
        h1 { font-size: 2.5em; margin-bottom: 20px; }
        p { font-size: 1.2em; margin-bottom: 30px; }
        .feature { background: rgba(255,255,255,0.1); padding: 20px; margin: 20px 0; border-radius: 10px; }
        button { padding: 12px 24px; font-size: 1em; background: rgba(255,255,255,0.2); border: 2px solid white; color: white; cursor: pointer; margin: 10px; border-radius: 10px; }
        button:hover { background: rgba(255,255,255,0.3); }
    </style>
</head>
<body>
    <div class="game-content">
        <h1>🎮 NovelForge Runtime Engine</h1>
        <p>Добро пожаловать в движок для создания визуальных новел!</p>
        
        <div class="feature">
            <h3>📝 Создание сцен</h3>
            <p>Добавляйте HTML файлы в папку templates/ для создания новых сцен</p>
        </div>
        
        <div class="feature">
            <h3>🎨 Стилизация</h3>
            <p>Используйте CSS для создания уникального дизайна</p>
        </div>
        
        <div class="feature">
            <h3>🔊 Аудио и видео</h3>
            <p>Поддерживается фоновая музыка, звуковые эффекты и видео</p>
        </div>
        
        <button onclick="showMessage()">📢 Показать сообщение</button>
        <button onclick="goBack()">🔙 Назад</button>
    </div>
    
    <script>
        function showMessage() {
            alert('🎉 Движок готов к работе!');
        }
        
        function goBack() {
            window.location.href = '/';
        }
    </script>
</body>
</html>"""
    
    with open('templates/game.html', 'w', encoding='utf-8') as f:
        f.write(game_content)
    print("🎮 Создан игровой файл: templates/game.html")
    
    # Создаем минимальный README
    readme_content = """# NovelForge Runtime Engine - Минимальный проект

## 🚀 Быстрый старт

1. Запустите `run_runtime.py`
2. Откройте браузер на `http://localhost:5000`
3. Нажмите "НАЧАТЬ ИГРУ"

## 📁 Структура

```
NovelForge/
├── templates/
│   ├── index.html     # Главное меню
│   └── game.html      # Игровая сцена
├── static/            # Статические файлы
├── bin/configs/       # Настройки
└── run_runtime.py     # Главный файл
```

## 🎮 Создание контента

Добавляйте HTML файлы в `templates/` для создания новых сцен.

---
Создано с помощью NovelForge Runtime Engine
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("📖 Создан README: README.md")
    
    print("\n✅ Минимальный проект NovelForge успешно создан!")
    print("🎯 Для запуска выполните: python run_runtime.py")
    print("🌐 Откройте браузер на: http://localhost:5000")
    
    return True

# Flask сервер
app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

# Автоматическая загрузка модулей из папки modules
def load_modules(app, modules_dir='bin/modules'):
    if getattr(sys, 'frozen', False):
        # Если скомпилировано, ищем модули в _internal
        modules_path = os.path.join(INTERNAL_DIR, 'bin', 'modules')
    else:
        # Если запущено из исходников
        modules_path = os.path.join(BASE_DIR, modules_dir)
    
    loaded_modules = 0
    
    if os.path.exists(modules_path):
        for module_file in glob.glob(os.path.join(modules_path, '*.py')):
            module_name = os.path.splitext(os.path.basename(module_file))[0]
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'register'):
                module.register(app)
                loaded_modules += 1
                print(f"✓ Загружен модуль: {module_name}")
    
    print(f"\n📦 Всего загружено модулей: {loaded_modules}")

load_modules(app)

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"❌ Ошибка при загрузке index.html: {e}")
        # Возвращаем базовую страницу
        return """
        <!DOCTYPE html>
        <html>
        <head><title>NovelForge</title></head>
        <body>
            <h1>🎮 NovelForge Runtime Engine</h1>
            <p>Добро пожаловать! Создайте файл templates/index.html для настройки главного меню.</p>
        </body>
        </html>
        """

@app.route('/game')
def game():
    try:
        return render_template('game.html')
    except Exception as e:
        print(f"❌ Ошибка при загрузке game.html: {e}")
        # Возвращаем базовую игровую страницу
        return """
        <!DOCTYPE html>
        <html>
        <head><title>NovelForge - Игра</title></head>
        <body>
            <h1>🎮 Игровая сцена</h1>
            <p>Создайте файл templates/game.html для настройки игровой сцены.</p>
            <a href="/">← Назад</a>
        </body>
        </html>
        """

@app.route('/game/<path:game_file>')
def game_file(game_file):
    """Обработка игровых файлов в папке game"""
    try:
        # Проверяем, что файл существует в папке templates/game/
        template_path = f'game/{game_file}'
        return render_template(template_path)
    except Exception as e:
        print(f"❌ Ошибка при загрузке игрового файла {game_file}: {e}")
        abort(404)

# Динамический рендеринг любого шаблона (с поддержкой подпапок)
@app.route('/templates/<path:template_path>')
def render_any_template(template_path):
    if not template_path.endswith('.html'):
        abort(404)
    try:
        return render_template(template_path)
    except Exception as e:
        print(f"❌ Ошибка при загрузке шаблона {template_path}: {e}")
        abort(404)

# Динамическая отдача любого статического файла (с поддержкой подпапок)
@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        file_path = os.path.join(STATIC_DIR, filename)
        if not os.path.isfile(file_path):
            print(f"❌ Статический файл не найден: {file_path}")
            abort(404)
        return send_from_directory(STATIC_DIR, filename)
    except Exception as e:
        print(f"❌ Ошибка при загрузке статического файла {filename}: {e}")
        abort(404)

# API для системных операций
@app.route('/system/exit', methods=['GET', 'POST'])
def system_exit():
    """Закрытие приложения через API"""
    try:
        print("🔄 Получен запрос на закрытие приложения через API")
        # Запускаем закрытие в отдельном потоке, чтобы ответ успел отправиться
        threading.Timer(0.5, lambda: os._exit(0)).start()
        return {"status": "success", "message": "Приложение будет закрыто"}, 200
    except Exception as e:
        print(f"❌ Ошибка при закрытии приложения: {e}")
        return {"status": "error", "message": str(e)}, 500

# API для работы с конфигурацией
@app.route('/config/get', methods=['GET'])
def get_config():
    """Получение всех настроек конфигурации"""
    try:
        config_data = {}
        for section in config.sections():
            config_data[section] = dict(config[section])
        return {"status": "success", "config": config_data}, 200
    except Exception as e:
        print(f"❌ Ошибка при получении конфигурации: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/config/set', methods=['POST'])
def set_config():
    """Установка настроек конфигурации"""
    try:
        from flask import request
        data = request.get_json()
        
        if not data or 'section' not in data or 'key' not in data or 'value' not in data:
            return {"status": "error", "message": "Неверные параметры"}, 400
        
        section = data['section']
        key = data['key']
        value = data['value']
        
        # Проверяем существование секции
        if not config.has_section(section):
            config.add_section(section)
        
        # Устанавливаем значение
        config.set(section, key, str(value))
        
        # Сохраняем конфигурацию
        with open('bin/configs/runtime_conf.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        
        print(f"✅ Настройка обновлена: [{section}] {key} = {value}")
        return {"status": "success", "message": "Настройка обновлена"}, 200
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении конфигурации: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/config/section/<section_name>', methods=['GET'])
def get_config_section(section_name):
    """Получение настроек конкретной секции"""
    try:
        if not config.has_section(section_name):
            return {"status": "error", "message": "Секция не найдена"}, 404
        
        section_data = dict(config[section_name])
        return {"status": "success", "section": section_name, "data": section_data}, 200
    except Exception as e:
        print(f"❌ Ошибка при получении секции конфигурации: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/system/gpu-info', methods=['GET'])
def get_gpu_info():
    """Получение информации о GPU"""
    try:
        gpu_type = get_gpu_type()
        renderer_info = {
            "nvidia": {
                "name": "NVIDIA GPU",
                "renderer": "hardware",
                "description": "Аппаратное ускорение с поддержкой CUDA"
            },
            "amd": {
                "name": "AMD GPU", 
                "renderer": "hardware",
                "description": "Аппаратное ускорение с поддержкой OpenCL"
            },
            "intel": {
                "name": "Intel GPU",
                "renderer": "opengl",
                "description": "OpenGL рендеринг для оптимальной производительности"
            },
            "unknown": {
                "name": "Неизвестная видеокарта",
                "renderer": "software",
                "description": "Программный рендеринг"
            }
        }
        
        info = renderer_info.get(gpu_type, renderer_info["unknown"])
        info["type"] = gpu_type
        
        return {"status": "success", "gpu": info}, 200
    except Exception as e:
        print(f"❌ Ошибка при получении информации о GPU: {e}")
        return {"status": "error", "message": str(e)}, 500

def run_flask():
    host = config.get('Server', 'host', fallback='127.0.0.1')
    port = config.getint('Server', 'port', fallback=5000)
    debug = config.getboolean('Server', 'debug', fallback=True)
    app.run(host=host, port=port, debug=debug, use_reloader=False)

# PySide6 окно
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        w = config['Window']
        self.setWindowTitle(w.get('title', 'NovelForge'))
        
        # Проверяем полноэкранный режим
        fullscreen = w.getboolean('fullscreen', False)
        
        if fullscreen:
            # Полноэкранный режим
            self.showFullScreen()
            print("🖥️ Запуск в полноэкранном режиме")
        else:
            # Оконный режим с указанными размерами
            self.setGeometry(
                int(w.get('x', 100)),
                int(w.get('y', 100)),
                int(w.get('width', 1200)),
                int(w.get('height', 800))
            )
            print(f"🪟 Запуск в оконном режиме: {w.get('width', 1200)}x{w.get('height', 800)}")
        
        # Убираем отступы у главного окна
        self.setContentsMargins(0, 0, 0, 0)
        self.url = w.get('url', f"http://{config.get('Server', 'host', fallback='127.0.0.1')}:{config.get('Server', 'port', fallback='5000')}/")
        
        # Создаём браузерный виджет с улучшенными настройками для видео
        self.web_view = QWebEngineView()
        
        # Настройки для поддержки видео и медиа
        self.setup_web_engine_settings()
        
        # Убираем отступы у виджета
        self.web_view.setContentsMargins(0, 0, 0, 0)
        
        # Показываем базовый html
        self.web_view.setHtml(self.get_base_html())
        
        # Размещаем его в окне
        central_widget = QWidget()
        central_widget.setContentsMargins(0, 0, 0, 0)  # Убираем отступы у центрального виджета
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы layout
        layout.setSpacing(0)  # Убираем промежутки между виджетами
        layout.addWidget(self.web_view)
        self.setCentralWidget(central_widget)
        
        # Через 2 секунды загружаем основной url
        QTimer.singleShot(2000, self.load_main_url)
        
        # Сохраняем состояние полноэкранного режима
        self.is_fullscreen = fullscreen

    def setup_web_engine_settings(self):
        """Настройка WebEngine для поддержки видео и медиа"""
        try:
            from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
            
            # Получаем профиль и настройки
            profile = self.web_view.page().profile()
            settings = self.web_view.page().settings()
            
            # Включаем поддержку видео и медиа
            settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.SpatialNavigationEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebSecurityEnabled, False)
            
            print("✅ WebEngine настройки для видео применены")
            
        except Exception as e:
            print(f"⚠️ Не удалось применить настройки WebEngine: {e}")
            print("📹 Видео может работать с ограничениями")

    def keyPressEvent(self, event: QKeyEvent):
        """Обработка нажатий клавиш"""
        if event.key() == 16777216:  # Escape key
            if self.is_fullscreen:
                print("🪟 Выход из полноэкранного режима")
                self.showNormal()
                self.is_fullscreen = False
            else:
                print("🖥️ Переход в полноэкранный режим")
                self.showFullScreen()
                self.is_fullscreen = True
        super().keyPressEvent(event)

    def get_base_html(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                    background: #000;
                }
                html {
                    margin: 0;
                    padding: 0;
                }
            </style>
        </head>
        <body>
            <div style="width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; color: white; font-family: Arial, sans-serif;">
                <h1>Загрузка NovelForge...</h1>
            </div>
        </body>
        </html>
        """
        return """
        <!DOCTYPE html>
        <html lang='ru'>
        <head>
            <meta charset='UTF-8'>
            <title>Загрузка...</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f8f8ff; color: #222; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .loader { text-align: center; }
                .loader h1 { color: #4a90e2; margin-bottom: 0.5em; }
                .loader p { color: #888; }
            </style>
        </head>
        <body>
            <div class='loader'>
                <h1>NovelForge</h1>
                <p>Загрузка приложения...</p>
            </div>
        </body>
        </html>
        """

    def load_main_url(self):
        """Загрузка основного URL с обработкой ошибок"""
        try:
            print(f"🌐 Загружаем URL: {self.url}")
            
            # Добавляем обработчики событий для диагностики
            self.web_view.loadStarted.connect(self.on_load_started)
            self.web_view.loadFinished.connect(self.on_load_finished)
            self.web_view.loadProgress.connect(self.on_load_progress)
            
            # Загружаем URL
            self.web_view.setUrl(self.url)
            
        except Exception as e:
            print(f"❌ Ошибка при загрузке URL: {e}")

    def on_load_started(self):
        """Событие начала загрузки"""
        print("🔄 Начало загрузки страницы...")

    def on_load_finished(self, success):
        """Событие завершения загрузки"""
        if success:
            print("✅ Страница успешно загружена")
        else:
            print("❌ Ошибка загрузки страницы")
            # Попытка перезагрузки через 3 секунды
            QTimer.singleShot(3000, self.retry_load)

    def on_load_progress(self, progress):
        """Событие прогресса загрузки"""
        if progress % 25 == 0:  # Логируем каждые 25%
            print(f"📊 Прогресс загрузки: {progress}%")

    def retry_load(self):
        """Повторная попытка загрузки"""
        print("🔄 Повторная попытка загрузки...")
        self.web_view.setUrl(self.url)

def start_music_controller():
    """Инициализация музыкального контроллера"""
    try:
        from bin.modules.music_controller import get_music_controller
        controller = get_music_controller()
        print("🎵 Музыкальный контроллер инициализирован")
        return controller
    except Exception as e:
        print(f"❌ Ошибка в музыкальном контроллере: {e}")
        return None

def main():
    try:
        # Обработка аргументов командной строки
        parser = argparse.ArgumentParser(description='NovelForge Runtime Engine')
        parser.add_argument('--new-project', action='store_true', 
                           help='Создать новый проект NovelForge')
        parser.add_argument('--only-server', action='store_true',
                           help='Запустить только сервер (без GUI)')
        
        args = parser.parse_args()
        
        # Если запрошено создание нового проекта
        if args.new_project:
            try:
                create_new_project()
                print("\n🎉 Проект создан успешно!")
                print("💡 Для запуска выполните: python run_runtime.py")
                return
            except Exception as e:
                print(f"❌ Ошибка при создании проекта: {e}")
                input("Нажмите Enter для выхода...")
                return
        
        # Проверяем наличие необходимых файлов
        config_file_path = os.path.join(CONFIG_DIR, 'runtime_conf.ini')
        if not os.path.exists(config_file_path):
            print(f"⚠️ Конфигурационный файл не найден: {config_file_path}")
            print("💡 Для создания нового проекта выполните: python run_runtime.py --new-project")
            input("Нажмите Enter для выхода...")
            return
        
        runtime_mode = config.get('Runtime', 'mode', fallback='both').strip().lower()
        server_console = config.getboolean('Runtime', 'server_console', fallback=False)

        print("Runtime mode:", runtime_mode)
        print("Server console:", server_console)

        # Инициализируем музыкальный контроллер
        try:
            music_controller = start_music_controller()
            if music_controller:
                print("🎵 Музыкальный контроллер готов к работе")
            else:
                print("⚠️ Музыкальный контроллер не инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации музыкального контроллера: {e}")

        if runtime_mode == 'window':
            # Только окно
            app_qt = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            sys.exit(app_qt.exec())
        elif runtime_mode == 'server':
            # Только сервер
            if server_console:
                # Запуск сервера в отдельной консоли
                subprocess.Popen([sys.executable, __file__, '--only-server'], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                run_flask()
        else:
            # Окно + сервер
            if server_console:
                subprocess.Popen([sys.executable, __file__, '--only-server'], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                flask_thread = threading.Thread(target=run_flask, daemon=True)
                flask_thread.start()
            app_qt = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            sys.exit(app_qt.exec())
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        print(f"📋 Подробности: {traceback.format_exc()}")
        print("\n💡 Если проблема повторяется, попробуйте:")
        print("   1. Проверить наличие всех файлов проекта")
        print("   2. Установить зависимости: pip install -r requirements.txt")
        print("   3. Запустить в режиме отладки")
        input("Нажмите Enter для выхода...")

if __name__ == '__main__':
    if '--only-server' in sys.argv:
        try:
            run_flask()
        except Exception as e:
            print(f"❌ Ошибка сервера: {e}")
            input("Нажмите Enter для выхода...")
    else:
        main() 
