from flask import Flask, render_template, send_from_directory, abort, render_template_string
import os
from pathlib import Path
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Базовые пути
TEMPLATES_DIR = Path('/data/scenes/templates')
ASSETS_DIR = Path('/data/scenes/assets')

# Настройка путей для Flask
app.template_folder = str(TEMPLATES_DIR)
app.static_folder = str(ASSETS_DIR)
app.static_url_path = '/assets'

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
    """Главная страница с навигацией"""
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

if __name__ == '__main__':
    # Создаем директории если их нет
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 50)
    print("Scene Server Starting...")
    print(f"Templates: {TEMPLATES_DIR}")
    print(f"Assets: {ASSETS_DIR}")
    print(f"Found {len(get_all_html_files())} templates")
    print(f"Found {len(get_all_asset_files())} assets")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)