from flask import Flask, render_template, send_from_directory, abort, render_template_string
import os
import sys
import threading
from pathlib import Path
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from data.extensions.extension_manager import ExtensionManager

app = Flask(__name__)

# Базовые пути - теперь относительно скрипта
BASE_DIR = Path(__file__).parent  # Папка, где лежит скрипт
TEMPLATES_DIR = BASE_DIR / 'data' / 'scenes' / 'templates'
ASSETS_DIR = BASE_DIR / 'data' / 'scenes' / 'assets'

# Настройка путей для Flask
app.template_folder = str(TEMPLATES_DIR)
app.static_folder = str(ASSETS_DIR)
app.static_url_path = '/assets'

def create_project_structure():
    """Создание структуры проекта с необходимыми папками"""
    directories = [
        TEMPLATES_DIR,
        ASSETS_DIR,
        ASSETS_DIR / 'css',
        ASSETS_DIR / 'js',
        ASSETS_DIR / 'images',
        ASSETS_DIR / 'fonts',
        ASSETS_DIR / 'audio',
        ASSETS_DIR / 'video',
    ]
    
    print("Creating project structure...")
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created: {directory}")
    
    # Создаем пустой index.html
    index_html = TEMPLATES_DIR / 'index.html'
    if not index_html.exists():
        index_html.write_text("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scene</title>
</head>
<body>
    <h1>Scene Project</h1>
    <p>Welcome to your new scene project!</p>
</body>
</html>""")
        print(f"Created: {index_html}")
    
    print("✅ Project created successfully!")

def get_all_html_files():
    """Рекурсивно получить все HTML файлы"""
    html_files = []
    if TEMPLATES_DIR.exists():
        for html_file in TEMPLATES_DIR.rglob('*.html'):
            relative_path = html_file.relative_to(TEMPLATES_DIR)
            html_files.append(str(relative_path))
    return sorted(html_files)

def get_all_asset_files():
    """Рекурсивно получить все файлы из assets"""
    asset_files = []
    if ASSETS_DIR.exists():
        for asset_file in ASSETS_DIR.rglob('*'):
            if asset_file.is_file():
                relative_path = asset_file.relative_to(ASSETS_DIR)
                asset_files.append(str(relative_path))
    return sorted(asset_files)

@app.route('/')
def index():
    """Главная страница - сразу отдает index.html"""
    # Проверяем, есть ли index.html
    if (TEMPLATES_DIR / 'index.html').exists():
        return render_template('index.html')
    
    # Если index.html нет, показываем навигацию
    templates = get_all_html_files()
    assets = get_all_asset_files()
    
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scene Server</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0 auto;
                    max-width: 1200px;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container { display: flex; gap: 20px; }
                .column { 
                    flex: 1;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 { color: #333; margin-bottom: 20px; }
                h2 { color: #666; margin-bottom: 15px; }
                ul { list-style: none; }
                li { margin: 8px 0; }
                a { 
                    color: #0066cc;
                    text-decoration: none;
                    padding: 5px 10px;
                    display: block;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                a:hover { 
                    background: #e6f0ff;
                    text-decoration: none;
                }
                .count { 
                    background: #0066cc;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 0.8em;
                    margin-left: 10px;
                }
            </style>
        </head>
        <body>
            <h1>🚀 Scene Server</h1>
            <div class="container">
                <div class="column">
                    <h2>📄 Templates <span class="count">{{ templates|length }}</span></h2>
                    <ul>
                        {% for template in templates %}
                        <li>
                            <a href="/{{ template.replace('.html', '') }}">
                                📝 {{ template.replace('.html', '') }}
                            </a>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                <div class="column">
                    <h2>📁 Assets <span class="count">{{ assets|length }}</span></h2>
                    <ul>
                        {% for asset in assets %}
                        <li>
                            <a href="/assets/{{ asset }}" target="_blank">
                                📎 {{ asset }}
                            </a>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </body>
        </html>
    """, templates=templates, assets=assets)

@app.route('/<path:path>')
def serve_template_or_asset(path):
    """Умный роутинг: пробуем шаблон, потом assets"""
    # Сначала пробуем как шаблон
    html_path = f"{path}.html"
    if (TEMPLATES_DIR / html_path).exists():
        try:
            return render_template(html_path)
        except Exception as e:
            return f"Template error: {e}", 500
    
    # Если нет расширения .html, пробуем прямой путь
    if (TEMPLATES_DIR / path).exists():
        try:
            return render_template(path)
        except Exception as e:
            return f"Template error: {e}", 500
    
    # Если это не шаблон, пробуем как asset
    if (ASSETS_DIR / path).exists():
        return send_from_directory(str(ASSETS_DIR), path)
    
    abort(404)

@app.route('/assets/<path:filename>')
def serve_static(filename):
    """Явный маршрут для assets"""
    if (ASSETS_DIR / filename).exists():
        return send_from_directory(str(ASSETS_DIR), filename)
    abort(404)

@app.errorhandler(404)
def page_not_found(e):
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Not Found</title>
            <style>
                body { 
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: #f5f5f5;
                }
                .error { 
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 { color: #e74c3c; font-size: 48px; margin: 0; }
                p { color: #666; }
                a { color: #0066cc; }
            </style>
        </head>
        <body>
            <div class="error">
                <h1>404</h1>
                <p>Страница не найдена</p>
                <a href="/">← Вернуться на главную</a>
            </div>
        </body>
        </html>
    """), 404

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scene Server")
        self.setGeometry(100, 100, 1200, 800)
        
        # Создаем WebEngine view
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # Загружаем index.html напрямую, если он существует
        index_path = TEMPLATES_DIR / 'index.html'
        if index_path.exists():
            self.web_view.load(QUrl.fromLocalFile(str(index_path)))
        else:
            self.web_view.load(QUrl("http://127.0.0.1:5000"))

def run_flask():
    """Запуск Flask в отдельном потоке"""
    # Создаем директории если их нет (только базовые)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 50)
    print("Scene Server Starting...")
    print(f"Base dir: {BASE_DIR}")
    print(f"Templates: {TEMPLATES_DIR}")
    print(f"Assets: {ASSETS_DIR}")
    print(f"Found {len(get_all_html_files())} templates")
    print(f"Found {len(get_all_asset_files())} assets")
    print("=" * 50)
    
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def run_extensions():
        """Запуск менеджера расширений"""
        extensions_dir = BASE_DIR / 'data' / 'extensions'
        ext_manager = ExtensionManager(extensions_dir, BASE_DIR)
        ext_manager.start_server()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--newproject':
        create_project_structure()
    else:
        # Запускаем Flask в отдельном потоке
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Запускаем менеджер расширений в отдельном потоке
        extensions_thread = threading.Thread(target=run_extensions, daemon=True)
        extensions_thread.start()
        
        # Запускаем Qt приложение
        qt_app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(qt_app.exec_())