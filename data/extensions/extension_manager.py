# data/extensions/extension_manager.py
"""
Менеджер расширений Scene Server
Управляет загрузкой, инициализацией и API расширений
"""
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from flask import Flask, Blueprint, jsonify, request
from flask_cors import CORS
import importlib.util

class ExtensionManager:
    """Менеджер расширений"""
    
    def __init__(self, extensions_dir: Path, base_dir: Path = None):
        self.extensions_dir = Path(extensions_dir)
        self.base_dir = base_dir or Path.cwd()
        self.extensions: Dict[str, Any] = {}
        self.manager_app = Flask(__name__)
        
        # ====== ВАЖНО: Настройка CORS ======
        CORS(self.manager_app, resources={
            r"/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": False
            }
        })
        
        # Добавляем CORS заголовки ко всем ответам
        @self.manager_app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response
        
        self.extension_port = 5001
        self._setup_manager_routes()
        self.running = False
    
    def _setup_manager_routes(self):
        """Настройка API менеджера расширений"""
        main_bp = Blueprint('extensions', __name__, url_prefix='/extension')
        
        @main_bp.route('/list')
        def list_extensions():
            """Список всех расширений"""
            extensions_info = []
            for name, ext in self.extensions.items():
                info = {
                    'name': name,
                    'version': getattr(ext, 'version', 'unknown'),
                    'initialized': hasattr(ext, 'initialized') and True,
                    'routes': []
                }
                
                if hasattr(ext, 'get_blueprint'):
                    bp = ext.get_blueprint()
                    if bp:
                        # Получаем правила маршрутизации
                        for rule in self.manager_app.url_map.iter_rules():
                            if rule.blueprint == 'vvoid':
                                info['routes'].append({
                                    'endpoint': rule.endpoint,
                                    'url': rule.rule,
                                    'methods': list(rule.methods)
                                })
                
                extensions_info.append(info)
            
            return jsonify(extensions_info)
        
        @main_bp.route('/status')
        def extension_status():
            """Статус менеджера расширений"""
            return jsonify({
                'running': self.running,
                'port': self.extension_port,
                'loaded_extensions': list(self.extensions.keys()),
                'available_extensions': self.discover_extensions()
            })
        
        self.manager_app.register_blueprint(main_bp)
    
    def discover_extensions(self) -> List[str]:
        """Поиск доступных расширений"""
        extensions = []
        if self.extensions_dir.exists():
            # Поиск в поддиректориях
            for ext_dir in self.extensions_dir.iterdir():
                if ext_dir.is_dir() and ext_dir.name != '__pycache__' and not ext_dir.name.startswith('_'):
                    manifest_path = ext_dir / 'manifest.json'
                    if manifest_path.exists():
                        extensions.append(ext_dir.name)
            
            # Также проверяем директории внутри подпапок
            for subdir in self.extensions_dir.iterdir():
                if subdir.is_dir() and subdir.name != '__pycache__' and not subdir.name.startswith('_'):
                    for ext_dir in subdir.iterdir():
                        if ext_dir.is_dir() and ext_dir.name != '__pycache__':
                            manifest_path = ext_dir / 'manifest.json'
                            if manifest_path.exists():
                                extensions.append(f"{subdir.name}/{ext_dir.name}")
        
        return extensions
    
    def load_manifest(self, extension_name: str) -> Optional[dict]:
        """Загрузка манифеста расширения"""
        manifest_path = self.extensions_dir / extension_name / 'manifest.json'
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def load_extension(self, extension_name: str) -> bool:
        """Загрузка расширения"""
        try:
            manifest = self.load_manifest(extension_name)
            if not manifest:
                print(f"❌ No manifest found for {extension_name}")
                return False
            
            if not manifest.get('enabled', True):
                print(f"⏭️ Extension {extension_name} is disabled")
                return False
            
            # Проверяем зависимости
            if not self._check_dependencies(manifest):
                print(f"⚠️ Continuing without some dependencies...")
            
            # Загружаем модуль расширения
            ext_path = self.extensions_dir / extension_name
            
            # Добавляем путь к расширению в sys.path
            if str(ext_path.parent) not in sys.path:
                sys.path.insert(0, str(ext_path.parent))
            
            # Импортируем модуль
            spec = importlib.util.spec_from_file_location(
                extension_name.replace('/', '.'),
                ext_path / 'main.py'
            )
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Ищем класс расширения
                ext_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        attr_name.endswith('Extension') and 
                        attr_name != 'Extension'):
                        ext_class = attr
                        break
                
                if ext_class:
                    # Создаем экземпляр расширения
                    extension = ext_class()
                    
                    # Инициализируем
                    if extension.initialize():
                        self.extensions[extension_name] = extension
                        
                        # Регистрируем Blueprint расширения
                        if hasattr(extension, 'get_blueprint'):
                            bp = extension.get_blueprint()
                            if bp:
                                self.manager_app.register_blueprint(bp)
                        
                        print(f"✅ Extension '{extension_name}' loaded successfully")
                        return True
                    else:
                        print(f"❌ Failed to initialize extension '{extension_name}'")
                else:
                    print(f"❌ No extension class found in {extension_name}")
            
            return False
            
        except Exception as e:
            print(f"❌ Error loading extension {extension_name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unload_extension(self, extension_name: str) -> bool:
        """Выгрузка расширения"""
        if extension_name in self.extensions:
            try:
                self.extensions[extension_name].shutdown()
                del self.extensions[extension_name]
                print(f"✅ Extension '{extension_name}' unloaded")
                return True
            except Exception as e:
                print(f"❌ Error unloading extension {extension_name}: {e}")
        return False
    
    def _check_dependencies(self, manifest: dict) -> bool:
        """Проверка зависимостей расширения"""
        dependencies = manifest.get('dependencies', {})
        packages = dependencies.get('packages', [])
        
        all_ok = True
        for package_req in packages:
            package_name = package_req.split('>=')[0].split('==')[0].strip()
            try:
                importlib.import_module(package_name.replace('-', '_'))
            except ImportError:
                print(f"⚠️ Missing dependency: {package_req}")
                print(f"   Please install: pip install {package_req}")
                all_ok = False
        
        return all_ok
    
    def start_server(self):
        """Запуск сервера расширений"""
        if not self.running:
            self.running = True
            print(f"🔌 Extension API starting on port {self.extension_port}")
            
            # Автозагрузка всех расширений
            available = self.discover_extensions()
            print(f"📦 Available extensions: {available}")
            
            for ext_name in available:
                manifest = self.load_manifest(ext_name)
                if manifest and manifest.get('auto_start', True):
                    self.load_extension(ext_name)
                    time.sleep(0.5)  # Небольшая задержка между загрузками
            
            # Запускаем Flask сервер
            self.manager_app.run(
                host='0.0.0.0',  # Слушаем все интерфейсы
                port=self.extension_port,
                debug=False,
                use_reloader=False
            )
    
    def stop_all(self):
        """Остановка всех расширений"""
        for name in list(self.extensions.keys()):
            self.unload_extension(name)
        self.running = False
    
    def get_manager_api_info(self) -> dict:
        """Информация об API менеджера"""
        return {
            'port': self.extension_port,
            'base_url': f'http://127.0.0.1:{self.extension_port}',
            'endpoints': {
                'list_extensions': '/extension/list',
                'status': '/extension/status',
                'extension_api': '/<extension_name>/<path>'
            }
        }