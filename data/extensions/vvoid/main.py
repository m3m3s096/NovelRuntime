"""
Void Audio Extension - Аудио расширение с микшированием
Использует sounddevice + soundfile вместо pygame
"""
import sounddevice as sd
import soundfile as sf
import numpy as np
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from flask import Blueprint, jsonify, request

@dataclass
class AudioFile:
    """Информация об аудио файле"""
    name: str
    filename: str
    path: str
    size: int
    loaded: bool = False
    duration: float = 0.0

@dataclass
class ActiveChannel:
    """Активный канал воспроизведения"""
    id: int
    sound_name: str
    volume: float
    loops: int
    playing: bool
    paused: bool
    start_time: float
    stream: Any = None

class AudioMixer:
    """Микшер аудио с использованием sounddevice"""
    
    def __init__(self, audio_dir: Path):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        self.sounds: Dict[str, Dict[str, Any]] = {}  # {name: {data, sample_rate}}
        self.channels: Dict[int, ActiveChannel] = {}
        self.global_volume = 1.0
        self.muted = False
        self.max_channels = 32
        self.channel_counter = 0
        self._lock = threading.Lock()
        self.initialized = False
        self._file_index: Dict[str, Path] = {}  # Индекс файлов по имени
        
    def initialize(self):
        """Инициализация аудио системы"""
        try:
            # Проверяем доступные устройства
            devices = sd.query_devices()
            print(f"📢 Available audio devices: {len(devices)}")
            
            # Устанавливаем параметры по умолчанию
            sd.default.samplerate = 44100
            sd.default.channels = 2
            
            # Индексируем все аудио файлы
            self._index_audio_files()
            
            self.initialized = True
            print(f"🔊 Audio mixer initialized with {self.max_channels} channels")
            print(f"📁 Indexed {len(self._file_index)} audio files")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize audio: {e}")
            return False
    
    def _index_audio_files(self):
        """Индексация всех аудио файлов в директории"""
        self._file_index.clear()
        supported_formats = {'.mp3', '.wav', '.ogg', '.flac', '.m4a'}
        
        if self.audio_dir.exists():
            for file_path in self.audio_dir.rglob('*'):
                if file_path.suffix.lower() in supported_formats:
                    # Индексируем по имени файла без расширения
                    name = file_path.stem
                    # Также индексируем по относительному пути без расширения
                    relative_path = file_path.relative_to(self.audio_dir)
                    path_name = str(relative_path.with_suffix(''))
                    
                    self._file_index[name] = file_path
                    self._file_index[path_name] = file_path
                    
                    print(f"📁 Indexed: {name} -> {relative_path}")
    
    def refresh_index(self):
        """Обновление индекса файлов"""
        self._index_audio_files()
        return len(self._file_index)
    
    def shutdown(self):
        """Завершение работы"""
        self.stop_all()
        self.initialized = False
        print("Audio system shutdown")
    
    def find_sound_file(self, sound_name: str) -> Optional[Path]:
        """Поиск аудио файла по имени"""
        # Прямой поиск в индексе
        if sound_name in self._file_index:
            return self._file_index[sound_name]
        
        # Поиск без учета регистра
        sound_name_lower = sound_name.lower()
        for name, path in self._file_index.items():
            if name.lower() == sound_name_lower:
                return path
        
        # Частичное совпадение
        for name, path in self._file_index.items():
            if sound_name_lower in name.lower():
                return path
        
        return None
    
    def load_sound(self, sound_name: str) -> bool:
        """Загрузка звука в память"""
        with self._lock:
            if sound_name in self.sounds:
                return True
            
            # Ищем файл используя новый метод
            file_path = self.find_sound_file(sound_name)
            
            if not file_path:
                print(f"❌ Sound file not found: {sound_name}")
                return False
            
            try:
                print(f"📂 Loading: {file_path}")
                # Загружаем аудио файл
                data, sample_rate = sf.read(str(file_path))
                
                # Конвертируем в стерео если моно
                if len(data.shape) == 1:
                    data = np.column_stack((data, data))
                
                # Нормализуем
                if data.dtype != np.float32:
                    data = data.astype(np.float32)
                
                self.sounds[sound_name] = {
                    'data': data,
                    'sample_rate': sample_rate,
                    'duration': len(data) / sample_rate,
                    'file_path': str(file_path)
                }
                
                print(f"✅ Loaded sound: {sound_name} ({file_path.name}, {self.sounds[sound_name]['duration']:.2f}s)")
                return True
            except Exception as e:
                print(f"❌ Error loading sound {sound_name}: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def play(self, sound_name: str, loops: int = 0, volume: float = 1.0, 
             fade_in: int = 0) -> Optional[int]:
        """Воспроизведение звука, возвращает ID канала"""
        with self._lock:
            if not self.load_sound(sound_name):
                return None
            
            if len(self.channels) >= self.max_channels:
                # Пытаемся найти и остановить завершенные каналы
                self._cleanup_finished_channels()
                if len(self.channels) >= self.max_channels:
                    print("❌ No free channels available")
                    return None
            
            try:
                sound_data = self.sounds[sound_name]
                data = sound_data['data'].copy()
                sample_rate = sound_data['sample_rate']
                
                # Применяем громкость
                actual_volume = volume * self.global_volume
                if self.muted:
                    actual_volume = 0
                
                # Бесконечный цикл
                if loops == -1:
                    loops = 999999
                
                # Создаем поток для воспроизведения
                def callback(outdata, frames, time_info, status):
                    nonlocal loops
                    if status:
                        print(f"Audio status: {status}")
                    
                    # Определяем сколько данных нужно
                    data_len = len(data)
                    current_frame = getattr(callback, 'frame', 0)
                    
                    if current_frame + frames > data_len:
                        if loops > 0:
                            loops -= 1
                            callback.frame = 0
                            current_frame = 0
                        else:
                            outdata[:] = 0
                            raise sd.CallbackStop()
                    
                    end_frame = min(current_frame + frames, data_len)
                    chunk = data[current_frame:end_frame] * actual_volume
                    
                    if len(chunk) < frames:
                        # Дополняем тишиной если нужно
                        outdata[:len(chunk)] = chunk
                        outdata[len(chunk):] = 0
                    else:
                        outdata[:] = chunk
                    
                    callback.frame = end_frame
                
                callback.frame = 0
                
                stream = sd.OutputStream(
                    samplerate=sample_rate,
                    channels=2,
                    callback=callback,
                    blocksize=1024,
                    latency='low'
                )
                stream.start()
                
                # Сохраняем информацию о канале
                channel_id = self.channel_counter
                self.channel_counter += 1
                
                self.channels[channel_id] = ActiveChannel(
                    id=channel_id,
                    sound_name=sound_name,
                    volume=volume,
                    loops=loops,
                    playing=True,
                    paused=False,
                    start_time=time.time(),
                    stream=stream
                )
                
                print(f"▶️ Playing [{channel_id}]: {sound_name} (vol: {actual_volume:.2f})")
                return channel_id
                
            except Exception as e:
                print(f"❌ Error playing sound: {e}")
                import traceback
                traceback.print_exc()
                return None
    
    def _cleanup_finished_channels(self):
        """Очистка завершенных каналов"""
        to_remove = []
        for cid, channel in self.channels.items():
            if not channel.playing and not channel.paused:
                if channel.stream:
                    try:
                        channel.stream.close()
                    except:
                        pass
                to_remove.append(cid)
        
        for cid in to_remove:
            del self.channels[cid]
    
    def stop(self, channel_id: Optional[int] = None, sound_name: Optional[str] = None):
        """Остановка воспроизведения"""
        with self._lock:
            if channel_id is not None and channel_id in self.channels:
                channel = self.channels[channel_id]
                if channel.stream:
                    try:
                        channel.stream.stop()
                        channel.stream.close()
                    except:
                        pass
                channel.playing = False
                del self.channels[channel_id]
                
            elif sound_name:
                to_remove = []
                for cid, channel in self.channels.items():
                    if channel.sound_name == sound_name:
                        if channel.stream:
                            try:
                                channel.stream.stop()
                                channel.stream.close()
                            except:
                                pass
                        channel.playing = False
                        to_remove.append(cid)
                for cid in to_remove:
                    del self.channels[cid]
            else:
                self.stop_all()
    
    def pause(self, channel_id: Optional[int] = None):
        """Пауза"""
        if channel_id is not None and channel_id in self.channels:
            channel = self.channels[channel_id]
            if channel.stream:
                channel.stream.stop()
            channel.paused = True
            channel.playing = False
        else:
            for channel in self.channels.values():
                if channel.stream:
                    channel.stream.stop()
                channel.paused = True
                channel.playing = False
    
    def unpause(self, channel_id: Optional[int] = None):
        """Снятие с паузы"""
        if channel_id is not None and channel_id in self.channels:
            channel = self.channels[channel_id]
            if channel.stream:
                channel.stream.start()
            channel.paused = False
            channel.playing = True
        else:
            for channel in self.channels.values():
                if channel.stream:
                    channel.stream.start()
                channel.paused = False
                channel.playing = True
    
    def set_volume(self, channel_id: Optional[int] = None, 
                   sound_name: Optional[str] = None, volume: float = 1.0):
        """Установка громкости (требует перезапуска для применения)"""
        volume = max(0.0, min(1.0, volume))
        
        if channel_id is not None and channel_id in self.channels:
            self.channels[channel_id].volume = volume
        elif sound_name:
            for channel in self.channels.values():
                if channel.sound_name == sound_name:
                    channel.volume = volume
    
    def set_global_volume(self, volume: float):
        """Установка глобальной громкости"""
        self.global_volume = max(0.0, min(1.0, volume))
    
    def mute(self):
        """Включение беззвучного режима"""
        self.muted = True
    
    def unmute(self):
        """Выключение беззвучного режима"""
        self.muted = False
    
    def stop_all(self):
        """Остановка всего"""
        for channel in self.channels.values():
            if channel.stream:
                try:
                    channel.stream.stop()
                    channel.stream.close()
                except:
                    pass
        self.channels.clear()
    
    def get_audio_files(self) -> List[AudioFile]:
        """Получить список доступных аудио файлов"""
        audio_files = []
        supported_formats = {'.mp3', '.wav', '.ogg', '.flac', '.m4a'}
        
        if self.audio_dir.exists():
            for file_path in self.audio_dir.rglob('*'):
                if file_path.suffix.lower() in supported_formats:
                    # Получаем длительность если файл загружен
                    duration = 0.0
                    if file_path.stem in self.sounds:
                        duration = self.sounds[file_path.stem]['duration']
                    
                    audio_files.append(AudioFile(
                        name=file_path.stem,
                        filename=file_path.name,
                        path=str(file_path.relative_to(self.audio_dir)),
                        size=file_path.stat().st_size,
                        loaded=file_path.stem in self.sounds,
                        duration=duration
                    ))
        
        return sorted(audio_files, key=lambda x: x.name)
    
    def get_status(self) -> dict:
        """Получить статус микшера"""
        return {
            'initialized': self.initialized,
            'global_volume': self.global_volume,
            'muted': self.muted,
            'active_channels': len(self.channels),
            'loaded_sounds': len(self.sounds),
            'indexed_files': len(self._file_index),
            'available_files': len(self.get_audio_files()),
            'audio_directory': str(self.audio_dir),
            'channels': [
                {
                    'id': cid,
                    'sound': info.sound_name,
                    'volume': info.volume,
                    'loops': info.loops if info.loops < 999999 else -1,
                    'playing': info.playing,
                    'paused': info.paused,
                    'elapsed': time.time() - info.start_time
                }
                for cid, info in self.channels.items()
            ]
        }

class VoidAudioExtension:
    """Расширение для работы с аудио"""
    
    def __init__(self, audio_dir: Path = None):
        if audio_dir is None:
            audio_dir = Path("data/scenes/assets/audio")
        
        self.audio_dir = Path(audio_dir)
        self.mixer = AudioMixer(self.audio_dir)
        self.name = "vvoid"
        self.version = "1.0.0"
        self.blueprint = None
        
    def initialize(self) -> bool:
        """Инициализация расширения"""
        try:
            self.mixer.initialize()
            self._create_blueprint()
            print(f"✅ Extension '{self.name}' v{self.version} initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize extension: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def shutdown(self):
        """Завершение работы"""
        self.mixer.shutdown()
        print(f"Extension '{self.name}' shutdown")
    
    def _create_blueprint(self):
        """Создание Blueprint с API маршрутами"""
        self.blueprint = Blueprint('vvoid', __name__, url_prefix='/audio')
        
        @self.blueprint.route('/status')
        def get_status():
            """Получить статус аудио системы"""
            return jsonify(self.mixer.get_status())
        
        @self.blueprint.route('/files')
        def list_files():
            """Список доступных аудио файлов"""
            files = self.mixer.get_audio_files()
            return jsonify([asdict(f) for f in files])
        
        @self.blueprint.route('/refresh-index', methods=['POST'])
        def refresh_index():
            """Обновить индекс аудио файлов"""
            count = self.mixer.refresh_index()
            return jsonify({'success': True, 'indexed_files': count})
        
        @self.blueprint.route('/play', methods=['POST'])
        def play_sound():
            """Воспроизвести звук"""
            data = request.get_json() or {}
            sound = data.get('sound')
            loops = data.get('loops', 0)
            volume = data.get('volume', 1.0)
            fade_in = data.get('fade_in', 0)
            
            if not sound:
                return jsonify({'error': 'Sound name required'}), 400
            
            channel_id = self.mixer.play(sound, loops, volume, fade_in)
            if channel_id is not None:
                return jsonify({
                    'success': True, 
                    'channel_id': channel_id,
                    'sound': sound
                })
            return jsonify({'error': 'Failed to play sound'}), 500
        
        @self.blueprint.route('/search', methods=['GET'])
        def search_sounds():
            """Поиск звуков по имени"""
            query = request.args.get('q', '').lower()
            if not query:
                return jsonify({'error': 'Search query required'}), 400
            
            results = []
            for name, path in self.mixer._file_index.items():
                if query in name.lower():
                    results.append({
                        'name': name,
                        'path': str(path.relative_to(self.audio_dir)),
                        'loaded': name in self.mixer.sounds
                    })
            
            return jsonify({'results': results[:20]})  # Ограничиваем результаты
        
        @self.blueprint.route('/stop', methods=['POST'])
        def stop_sound():
            """Остановить звук"""
            data = request.get_json() or {}
            channel_id = data.get('channel_id')
            sound_name = data.get('sound')
            
            self.mixer.stop(channel_id, sound_name)
            return jsonify({'success': True})
        
        @self.blueprint.route('/pause', methods=['POST'])
        def pause_sound():
            """Поставить на паузу"""
            data = request.get_json() or {}
            channel_id = data.get('channel_id')
            
            self.mixer.pause(channel_id)
            return jsonify({'success': True})
        
        @self.blueprint.route('/unpause', methods=['POST'])
        def unpause_sound():
            """Снять с паузы"""
            data = request.get_json() or {}
            channel_id = data.get('channel_id')
            
            self.mixer.unpause(channel_id)
            return jsonify({'success': True})
        
        @self.blueprint.route('/volume', methods=['POST'])
        def set_volume():
            """Установить громкость"""
            data = request.get_json() or {}
            channel_id = data.get('channel_id')
            sound_name = data.get('sound')
            volume = data.get('volume', 1.0)
            global_vol = data.get('global')
            
            if global_vol is not None:
                self.mixer.set_global_volume(global_vol)
            else:
                self.mixer.set_volume(channel_id, sound_name, volume)
            
            return jsonify({'success': True})
        
        @self.blueprint.route('/mute', methods=['POST'])
        def mute():
            """Включить беззвучный режим"""
            data = request.get_json() or {}
            muted = data.get('muted', True)
            
            if muted:
                self.mixer.mute()
            else:
                self.mixer.unmute()
            
            return jsonify({'success': True, 'muted': self.mixer.muted})
        
        @self.blueprint.route('/load', methods=['POST'])
        def load_sound():
            """Загрузить звук в память"""
            data = request.get_json() or {}
            sound_name = data.get('sound')
            
            if not sound_name:
                return jsonify({'error': 'Sound name required'}), 400
            
            success = self.mixer.load_sound(sound_name)
            return jsonify({'success': success})
        
        @self.blueprint.route('/preload-all', methods=['POST'])
        def preload_all():
            """Предзагрузить все аудио файлы"""
            files = self.mixer.get_audio_files()
            loaded = 0
            for file in files:
                if self.mixer.load_sound(file.name):
                    loaded += 1
            
            return jsonify({
                'success': True,
                'total': len(files),
                'loaded': loaded
            })
        
        @self.blueprint.route('/stop-all', methods=['POST'])
        def stop_all():
            """Остановить все звуки"""
            self.mixer.stop_all()
            return jsonify({'success': True})
    
    def get_blueprint(self) -> Blueprint:
        """Получить Blueprint расширения"""
        if self.blueprint is None:
            self._create_blueprint()
        return self.blueprint