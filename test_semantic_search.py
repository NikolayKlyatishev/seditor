#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки семантического поиска
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_semantic_indexer():
    """Тест семантического индексатора"""
    try:
        from seditor.search import SemanticIndexer
        
        # Используем текущую директорию проекта
        project_root = os.path.dirname(os.path.abspath(__file__))
        logger.info(f'Testing semantic indexer on: {project_root}')
        
        # Создаём индексатор
        logger.info('Creating indexer...')
        indexer = SemanticIndexer(project_root)
        
        # Проверяем, есть ли уже индекс
        if indexer.is_indexed():
            count = indexer.get_indexed_count()
            logger.info(f'Index already exists with {count} files')
        else:
            # Индексируем
            logger.info('Starting indexing...')
            
            def progress(current, total):
                if current % 10 == 0 or current == total:
                    logger.info(f'Progress: {current}/{total} files')
            
            indexed_count = indexer.index_directory(progress_callback=progress)
            logger.info(f'Indexing completed: {indexed_count} files indexed')
        
        # Тестовые запросы
        test_queries = [
            'файловое дерево',
            'командная палитра',
            'редактор текста',
            'семантический поиск',
            'индексация файлов'
        ]
        
        logger.info('\n' + '='*60)
        logger.info('Testing search queries:')
        logger.info('='*60)
        
        for query in test_queries:
            logger.info(f'\nQuery: "{query}"')
            results = indexer.search(query, top_k=5)
            
            if results:
                logger.info(f'Found {len(results)} results:')
                for i, (path, name, score) in enumerate(results, 1):
                    relative_path = os.path.relpath(path, project_root)
                    logger.info(f'  {i}. {name} ({relative_path}) - score: {score:.4f}')
            else:
                logger.info('  No results found')
        
        logger.info('\n' + '='*60)
        logger.info('Test completed successfully!')
        logger.info('='*60)
        
        return True
        
    except ImportError as e:
        logger.error(f'Import error: {e}')
        logger.error('Please install dependencies: poetry install')
        return False
    except Exception as e:
        logger.error(f'Test failed: {e}', exc_info=True)
        return False


if __name__ == '__main__':
    success = test_semantic_indexer()
    sys.exit(0 if success else 1)

