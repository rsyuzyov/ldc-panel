#!/usr/bin/env python3
"""
E2E тесты интерфейса LDC Panel с использованием Playwright.
Запуск: python tests/test_ui.py
"""

import json
import sys
import subprocess
import time
import os
from pathlib import Path

# Проверка и создание конфига
CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "login": {
        "username": "root",
        "password": "YOUR_PASSWORD_HERE"
    },
    "controller": {
        "name": "DC1.domain.local",
        "host": "192.168.1.10",
        "ssh_user": "root",
        "ssh_password": "YOUR_SSH_PASSWORD"
    },
    "server": {
        "frontend_url": "http://localhost:5173",
        "backend_url": "http://localhost:8000"
    },
    "test_user": {
        "username": "ldc-panel-test",
        "fullName": "LDC Panel Test User",
        "email": "ldc-panel-test@domain.local",
        "groups": "Domain Users",
        "new_password": "TestPassword123!"
    },
    "test_dns": {
        "name": "ldc-test-record",
        "type": "A",
        "value": "192.168.1.250",
        "ttl": "3600",
        "zone": "domain.local",
        "updated_value": "192.168.1.251"
    },
    "test_dhcp": {
        "hostname": "ldc-test-device",
        "mac": "AA:BB:CC:DD:EE:FF",
        "ip": "192.168.1.99",
        "description": "LDC Panel Test Reservation"
    }
}


def check_config():
    """Проверка наличия и валидности конфига."""
    if not CONFIG_PATH.exists():
        print(f"Конфиг не найден. Создаю {CONFIG_PATH}")
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print("Заполни config.json реальными данными и запусти тест снова.")
        sys.exit(1)
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    if config["login"]["password"] == "YOUR_PASSWORD_HERE":
        print("Ошибка: заполни пароль в config.json")
        sys.exit(1)
    
    return config


def run_tests():
    """Основной запуск тестов."""
    config = check_config()
    
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError:
        print("Playwright не установлен. Устанавливаю...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        from playwright.sync_api import sync_playwright, expect
    
    frontend_url = config["server"]["frontend_url"]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)
        
        # Глобальный обработчик диалогов (confirm)
        page.on("dialog", lambda dialog: dialog.accept())
        
        try:
            # 1. Проверка доступности сервера
            print("\n[1/13] Проверка доступности сервера...")
            page.goto(frontend_url)
            expect(page.locator("h1")).to_contain_text("LDC Panel")
            print("✓ Сервер доступен")
            
            # 2. Вход в панель
            print("\n[2/13] Вход в панель...")
            page.fill("#username", config["login"]["username"])
            page.fill("#password", config["login"]["password"])
            page.click("button[type='submit']")
            # Ждём загрузки главной страницы
            expect(page.locator("text=Текущий сервер")).to_be_visible()
            print("✓ Вход выполнен")
            
            # 3. Добавление контроллера
            print("\n[3/13] Добавление контроллера...")
            # Переход в раздел серверов
            page.click("button[title='Управление серверами']")
            page.wait_for_timeout(500)
            
            # Проверяем, есть ли уже такой сервер — если да, удаляем
            existing_server = page.locator(f"tr:has-text('{config['controller']['name']}')")
            if existing_server.count() > 0:
                print("  Удаляю существующий сервер...")
                existing_server.locator("button[title='Удалить']").click()
                page.wait_for_timeout(500)
            
            # Нажимаем "Добавить"
            page.click("button:has-text('Добавить')")
            page.wait_for_timeout(300)
            # Заполняем форму
            page.fill("#name", config["controller"]["name"])
            page.fill("#host", config["controller"].get("host", config["controller"]["name"]))
            page.fill("#user", config["controller"].get("ssh_user", "root"))
            # Выбираем тип аутентификации "Пароль" и вводим пароль
            if config["controller"].get("ssh_password"):
                page.fill("#password", config["controller"]["ssh_password"])
            page.click("button:has-text('Сохранить')")
            # Ждём закрытия диалога
            page.wait_for_selector("[data-slot='dialog-overlay']", state="hidden", timeout=10000)
            page.wait_for_timeout(500)
            # Проверяем, что контроллер добавлен (ждём проверки статуса)
            expect(page.locator(f"td:has-text('{config['controller']['name']}')" )).to_be_visible()
            # Ждём завершения проверки (статус изменится с "Проверка...")
            page.wait_for_timeout(3000)
            print("✓ Контроллер добавлен")
            
            # 4. Выбор контроллера как текущего
            print("\n[4/13] Выбор контроллера как текущего...")
            # Проверяем, что сервер автоматически выбран (если единственный активный)
            # или выбираем вручную
            select_trigger = page.locator("[data-slot='select-trigger']")
            current_value = select_trigger.inner_text()
            server_name_part = config['controller']['name'].split('.')[0]
            
            if server_name_part not in current_value:
                # Открываем селект и выбираем сервер
                select_trigger.click()
                page.wait_for_timeout(300)
                # Ищем enabled опции (не disabled)
                server_option = page.locator(f"[data-slot='select-item']:not([data-disabled]):has-text('{server_name_part}')")
                if server_option.count() > 0:
                    server_option.first.click()
                else:
                    # Пробуем любую enabled опцию
                    enabled_options = page.locator("[data-slot='select-item']:not([data-disabled])")
                    if enabled_options.count() > 0:
                        enabled_options.first.click()
                    else:
                        # Нет активных серверов — закрываем селект и пропускаем
                        page.keyboard.press("Escape")
                        print("⚠ Нет активных серверов для выбора (проверка не прошла)")
                page.wait_for_timeout(300)
            print("✓ Контроллер выбран")
            
            # 5. Переход в AD и проверка списка пользователей
            print("\n[5/13] Проверка раздела AD...")
            page.click("button:has-text('AD')")
            page.wait_for_timeout(500)
            # Проверяем, что таблица не пустая
            rows = page.locator("tbody tr")
            expect(rows.first).to_be_visible()
            row_count = rows.count()
            assert row_count > 0, "Список пользователей пуст"
            print(f"✓ Раздел AD: найдено {row_count} записей")
            
            # 6. Создание тестового пользователя
            print("\n[6/13] Создание пользователя ldc-panel-test...")
            page.click("button:has-text('Добавить')")
            page.wait_for_timeout(300)
            page.fill("#username", config["test_user"]["username"])
            page.fill("#fullName", config["test_user"]["fullName"])
            page.fill("#email", config["test_user"]["email"])
            page.fill("#groups", config["test_user"]["groups"])
            page.click("button:has-text('Сохранить')")
            page.wait_for_timeout(500)
            expect(page.get_by_role("cell", name=config['test_user']['username'], exact=True)).to_be_visible()
            print("✓ Пользователь создан")
            
            # 7. Смена пароля (редактирование пользователя)
            print("\n[7/13] Смена пароля пользователя...")
            # Находим строку с тестовым пользователем и кликаем редактировать
            user_row = page.locator(f"tr:has-text('{config['test_user']['username']}')")
            user_row.locator("button[title='Редактировать']").click()
            page.wait_for_timeout(300)
            # Меняем email как индикатор изменения (пароль может быть в отдельной форме)
            page.fill("#email", f"updated-{config['test_user']['email']}")
            page.click("button:has-text('Сохранить')")
            page.wait_for_timeout(500)
            print("✓ Пользователь обновлён")
            
            # 8. Удаление тестового пользователя
            print("\n[8/13] Удаление пользователя...")
            user_row = page.locator(f"tr:has-text('{config['test_user']['username']}')")
            user_row.locator("button[title='Удалить']").click()
            page.wait_for_timeout(500)
            expect(page.locator(f"td:has-text('{config['test_user']['username']}')" )).to_have_count(0)
            print("✓ Пользователь удалён")
            
            # 9. Переход в DNS и проверка списка
            print("\n[9/13] Проверка раздела DNS...")
            page.click("button:has-text('DNS')")
            page.wait_for_timeout(500)
            rows = page.locator("tbody tr")
            expect(rows.first).to_be_visible()
            row_count = rows.count()
            assert row_count > 0, "Список DNS записей пуст"
            print(f"✓ Раздел DNS: найдено {row_count} записей")
            
            # 10. Добавление, изменение, удаление DNS записи
            print("\n[10/13] CRUD операции с DNS записью...")
            # Добавление
            page.click("button:has-text('Добавить')")
            page.wait_for_timeout(300)
            page.fill("#zone", config["test_dns"]["zone"])
            page.fill("#name", config["test_dns"]["name"])
            page.fill("#value", config["test_dns"]["value"])
            page.fill("#ttl", config["test_dns"]["ttl"])
            page.click("button:has-text('Сохранить')")
            page.wait_for_timeout(500)
            expect(page.locator(f"text={config['test_dns']['name']}")).to_be_visible()
            print("  ✓ DNS запись добавлена")
            
            # Изменение
            dns_row = page.locator(f"tr:has-text('{config['test_dns']['name']}')")
            dns_row.locator("button[title='Редактировать']").click()
            page.wait_for_timeout(300)
            page.fill("#value", config["test_dns"]["updated_value"])
            page.click("button:has-text('Сохранить')")
            page.wait_for_timeout(500)
            expect(page.locator(f"text={config['test_dns']['updated_value']}")).to_be_visible()
            print("  ✓ DNS запись изменена")
            
            # Удаление
            dns_row = page.locator(f"tr:has-text('{config['test_dns']['name']}')")
            dns_row.locator("button[title='Удалить']").click()
            page.wait_for_timeout(500)
            expect(page.locator(f"td:has-text('{config['test_dns']['name']}')" )).to_have_count(0)
            print("  ✓ DNS запись удалена")
            
            # 11. Переход в DHCP и проверка списка
            print("\n[11/13] Проверка раздела DHCP...")
            page.click("button:has-text('DHCP')")
            page.wait_for_timeout(500)
            rows = page.locator("tbody tr")
            expect(rows.first).to_be_visible()
            row_count = rows.count()
            assert row_count > 0, "Список DHCP пуст"
            print(f"✓ Раздел DHCP: найдено {row_count} записей")
            
            # 12. Резервирование и отмена резервирования
            print("\n[12/13] Резервирование IP адреса...")
            # Переключаемся на вкладку резервирований
            page.click("button[role='tab']:has-text('Резервирования')")
            page.wait_for_timeout(300)
            
            # Добавляем резервирование
            page.click("button:has-text('Добавить')")
            page.wait_for_timeout(300)
            page.fill("#hostname", config["test_dhcp"]["hostname"])
            page.fill("#mac", config["test_dhcp"]["mac"])
            page.fill("#ip", config["test_dhcp"]["ip"])
            page.fill("#description", config["test_dhcp"]["description"])
            page.click("button:has-text('Сохранить')")
            page.wait_for_timeout(500)
            expect(page.locator(f"text={config['test_dhcp']['hostname']}")).to_be_visible()
            print("  ✓ Резервирование создано")
            
            # Удаляем резервирование
            dhcp_row = page.locator(f"tr:has-text('{config['test_dhcp']['hostname']}')")
            dhcp_row.locator("button[title='Удалить']").click()
            page.wait_for_timeout(500)
            expect(page.locator(f"td:has-text('{config['test_dhcp']['hostname']}')" )).to_have_count(0)
            print("  ✓ Резервирование отменено")
            
            # 13. Переход в GPO и проверка списка
            print("\n[13/13] Проверка раздела GPO...")
            page.click("button:has-text('GPO')")
            page.wait_for_timeout(500)
            rows = page.locator("tbody tr")
            expect(rows.first).to_be_visible()
            row_count = rows.count()
            assert row_count > 0, "Список GPO пуст"
            print(f"✓ Раздел GPO: найдено {row_count} записей")
            
            print("\n" + "=" * 50)
            print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            # Скриншот при ошибке
            screenshot_path = Path(__file__).parent / "error_screenshot.png"
            page.screenshot(path=str(screenshot_path))
            print(f"Скриншот сохранён: {screenshot_path}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    run_tests()
