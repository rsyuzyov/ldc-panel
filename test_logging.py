#!/usr/bin/env python3
"""Test logging system"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.logger import archive_old_log, cleanup_old_logs, get_logger
from app.config import settings

print("=" * 60)
print("Тест системы логирования")
print("=" * 60)

print(f"\n1. Пути:")
print(f"   Logs dir: {settings.logs_dir}")
print(f"   Log file: {settings.log_file}")
print(f"   Logs dir exists: {settings.logs_dir.exists()}")

print(f"\n2. Архивирование старого лога...")
archived = archive_old_log(settings.log_file)
if archived:
    print(f"   Архивирован: {archived}")
else:
    print(f"   Старый лог не найден, архивирование не требуется")

print(f"\n3. Очистка старых логов (>30 дней)...")
cleanup_old_logs(settings.logs_dir, max_age_days=30)
print(f"   Очистка выполнена")

print(f"\n4. Тест логирования...")
logger = get_logger("test")
logger.info("Test INFO message")
logger.warning("Test WARNING message")
logger.error("Test ERROR message")
logger.debug("Test DEBUG message")

print(f"\n5. Проверка лог-файла...")
if settings.log_file.exists():
    with open(settings.log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"   Создан: {settings.log_file}")
    print(f"   Размер: {settings.log_file.stat().st_size} bytes")
    print(f"   Строк: {len(lines)}")
    if lines:
        print(f"\n   Последние 3 строки:")
        for line in lines[-3:]:
            print(f"     {line.rstrip()}")
else:
    print(f"   ОШИБКА: Лог-файл не создан!")

print(f"\n6. Файлы в logs/:")
if settings.logs_dir.exists():
    for file in settings.logs_dir.iterdir():
        print(f"   - {file.name} ({file.stat().st_size} bytes)")
else:
    print(f"   Директория logs/ не существует")

print("\n" + "=" * 60)
print("Тест завершен")
print("=" * 60)
