# -*- coding: utf-8 -*-
"""
Семантический индексатор файлов для быстрого поиска по смыслу
"""

import os
import logging
from typing import List, Tuple, Optional, Callable
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class SemanticIndexer:
    """Индексатор файлов с использованием векторных эмбеддингов"""
    
    # Расширения файлов для индексации
    INDEXABLE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs',
        '.cpp', '.c', '.h', '.hpp', '.rb', '.php', '.swift', '.kt',
        '.html', '.css', '.scss', '.sass', '.json', '.yaml', '.yml',
        '.md', '.txt', '.toml', '.ini', '.conf', '.sh', '.bash'
    }
    
    # Директории для игнорирования
    IGNORE_DIRS = {
        '.git', 'node_modules', '__pycache__', 'venv', '.venv',
        'env', '.env', 'dist', 'build', '.seditor', '.idea',
        '.vscode', 'target', 'bin', 'obj'
    }
    
    # Максимальный размер файла для индексации (1MB)
    MAX_FILE_SIZE = 1 * 1024 * 1024
    
    # Максимальный размер для чтения целиком (100KB)
    MAX_FULL_READ_SIZE = 100 * 1024
    
    # Размер частичного чтения (50KB)
    PARTIAL_READ_SIZE = 50 * 1024
    
    def __init__(self, root_path: str):
        """
        Инициализация индексатора
        
        Args:
            root_path: Корневой путь проекта для индексации
        """
        self.root_path = os.path.abspath(root_path)
        self.seditor_dir = os.path.join(self.root_path, '.seditor')
        self.chroma_dir = os.path.join(self.seditor_dir, 'chroma_db')
        
        # Ленивая инициализация для ускорения запуска
        self._model = None
        self._collection = None
        self._client = None
        
        # Создаём служебную директорию
        os.makedirs(self.seditor_dir, exist_ok=True)
        
        logger.info(f'SemanticIndexer initialized for: {self.root_path}')
    
    def _init_model(self):
        """Ленивая инициализация модели эмбеддингов"""
        if self._model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info('Loading sentence-transformers model...')
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info('Model loaded successfully')
        except Exception as e:
            logger.error(f'Failed to load model: {e}')
            raise
    
    def _init_chroma(self):
        """Ленивая инициализация ChromaDB"""
        if self._client is not None:
            return
        
        try:
            import chromadb
            
            logger.info(f'Initializing ChromaDB at: {self.chroma_dir}')
            
            # Используем новый API ChromaDB (PersistentClient)
            self._client = chromadb.PersistentClient(path=self.chroma_dir)
            
            # Получаем или создаём коллекцию
            try:
                self._collection = self._client.get_collection(name="files")
                logger.info(f'Loaded existing collection with {self._collection.count()} documents')
            except Exception:
                self._collection = self._client.create_collection(
                    name="files",
                    metadata={"description": "Indexed source files"}
                )
                logger.info('Created new collection')
            
        except Exception as e:
            logger.error(f'Failed to initialize ChromaDB: {e}')
            raise
    
    def _should_index_file(self, file_path: str) -> bool:
        """
        Проверить, нужно ли индексировать файл
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если файл нужно индексировать
        """
        # Проверка расширения
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.INDEXABLE_EXTENSIONS:
            return False
        
        # Проверка размера
        try:
            size = os.path.getsize(file_path)
            if size > self.MAX_FILE_SIZE:
                return False
        except OSError:
            return False
        
        return True
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """
        Прочитать содержимое файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Содержимое файла или None при ошибке
        """
        try:
            size = os.path.getsize(file_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                if size <= self.MAX_FULL_READ_SIZE:
                    # Читаем целиком
                    return f.read()
                else:
                    # Читаем частично
                    return f.read(self.PARTIAL_READ_SIZE)
        except Exception as e:
            logger.warning(f'Failed to read file {file_path}: {e}')
            return None
    
    def _get_file_id(self, file_path: str) -> str:
        """
        Получить уникальный ID для файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Уникальный ID (hash от пути)
        """
        relative_path = os.path.relpath(file_path, self.root_path)
        return hashlib.md5(relative_path.encode()).hexdigest()
    
    def _collect_files(self) -> List[str]:
        """
        Собрать список файлов для индексации
        
        Returns:
            Список путей к файлам
        """
        files = []
        
        for root, dirs, filenames in os.walk(self.root_path):
            # Фильтруем директории для игнорирования
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if self._should_index_file(file_path):
                    files.append(file_path)
        
        return files
    
    def index_directory(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> int:
        """
        Индексировать директорию
        
        Args:
            progress_callback: Функция для отслеживания прогресса (current, total)
            
        Returns:
            Количество проиндексированных файлов
        """
        # Инициализируем модель и БД
        self._init_model()
        self._init_chroma()
        
        # Собираем файлы
        files = self._collect_files()
        total_files = len(files)
        
        logger.info(f'Found {total_files} files to index')
        
        if total_files == 0:
            return 0
        
        indexed_count = 0
        
        # Обрабатываем файлы батчами для эффективности
        batch_size = 10
        batch_ids = []
        batch_documents = []
        batch_metadatas = []
        
        for idx, file_path in enumerate(files):
            # Читаем содержимое
            content = self._read_file_content(file_path)
            if content is None or len(content.strip()) == 0:
                continue
            
            # Подготавливаем метаданные
            relative_path = os.path.relpath(file_path, self.root_path)
            file_id = self._get_file_id(file_path)
            
            metadata = {
                'path': file_path,
                'relative_path': relative_path,
                'name': os.path.basename(file_path),
                'extension': os.path.splitext(file_path)[1],
                'size': os.path.getsize(file_path),
                'timestamp': os.path.getmtime(file_path)
            }
            
            batch_ids.append(file_id)
            batch_documents.append(content)
            batch_metadatas.append(metadata)
            
            # Когда батч заполнен или это последний файл
            if len(batch_ids) >= batch_size or idx == total_files - 1:
                try:
                    # Создаём эмбеддинги
                    embeddings = self._model.encode(batch_documents, show_progress_bar=False)
                    
                    # Добавляем в коллекцию (upsert для обновления существующих)
                    self._collection.upsert(
                        ids=batch_ids,
                        embeddings=embeddings.tolist(),
                        documents=batch_documents,
                        metadatas=batch_metadatas
                    )
                    
                    indexed_count += len(batch_ids)
                    
                    # Очищаем батч
                    batch_ids = []
                    batch_documents = []
                    batch_metadatas = []
                    
                except Exception as e:
                    logger.error(f'Failed to index batch: {e}')
            
            # Обновляем прогресс
            if progress_callback:
                progress_callback(idx + 1, total_files)
        
        logger.info(f'Indexed {indexed_count} files')
        return indexed_count
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, str, float]]:
        """
        Поиск файлов по семантическому запросу
        
        Args:
            query: Текстовый запрос пользователя
            top_k: Количество результатов
            
        Returns:
            Список кортежей (file_path, file_name, score)
        """
        if not query or len(query.strip()) == 0:
            return []
        
        # Инициализируем модель и БД
        self._init_model()
        self._init_chroma()
        
        # Проверяем, есть ли документы в коллекции
        if self._collection.count() == 0:
            logger.warning('Collection is empty, no results')
            return []
        
        try:
            # Создаём эмбеддинг для запроса
            query_embedding = self._model.encode([query], show_progress_bar=False)[0]
            
            # Ищем в коллекции
            results = self._collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(top_k, self._collection.count())
            )
            
            # Форматируем результаты
            search_results = []
            
            if results and results['metadatas'] and len(results['metadatas']) > 0:
                metadatas = results['metadatas'][0]
                distances = results['distances'][0] if 'distances' in results else [0] * len(metadatas)
                
                for metadata, distance in zip(metadatas, distances):
                    file_path = metadata.get('path', '')
                    file_name = metadata.get('name', os.path.basename(file_path))
                    
                    # Конвертируем distance в score (меньше distance = выше score)
                    score = 1.0 / (1.0 + distance)
                    
                    search_results.append((file_path, file_name, score))
            
            logger.info(f'Search for "{query}" returned {len(search_results)} results')
            return search_results
            
        except Exception as e:
            logger.error(f'Search failed: {e}')
            return []
    
    def is_indexed(self) -> bool:
        """
        Проверить, проиндексирована ли директория
        
        Returns:
            True если есть проиндексированные файлы
        """
        try:
            self._init_chroma()
            return self._collection.count() > 0
        except Exception:
            return False
    
    def get_indexed_count(self) -> int:
        """
        Получить количество проиндексированных файлов
        
        Returns:
            Количество документов в коллекции
        """
        try:
            self._init_chroma()
            return self._collection.count()
        except Exception:
            return 0

