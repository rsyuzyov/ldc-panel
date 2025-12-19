# Design Document: Linux DC Panel

## Overview

Linux DC Panel — веб-приложение для централизованного управления Samba AD DC, DNS и DHCP серверами. Архитектура: FastAPI backend + React frontend. Панель устанавливается на отдельный сервер и подключается к контроллерам по SSH для выполнения команд.

**Ключевые принципы:**
- Максимальная простота реализации
- Использование CLI-утилит (ldbsearch, ldapmodify, samba-tool) вместо библиотек для скорости
- Авторизация только под локальным root
- Хранение конфигурации в YAML файлах

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LDC Panel Server                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │   React     │───▶│   FastAPI   │───▶│   SSH Service   │  │
│  │  Frontend   │    │   Backend   │    │   (paramiko)    │  │
│  └─────────────┘    └─────────────┘    └────────┬────────┘  │
│                            │                     │           │
│                     ┌──────┴──────┐              │           │
│                     │  servers.yaml│              │           │
│                     │  keys/       │              │           │
│                     └─────────────┘              │           │
└─────────────────────────────────────────────────┼───────────┘
                                                   │ SSH
                    ┌──────────────────────────────┼──────────┐
                    ▼                              ▼          ▼
            ┌───────────┐                  ┌───────────┐ ┌───────────┐
            │   DC1     │                  │   DC2     │ │   DC3     │
            │ domain1   │                  │ domain1   │ │ domain2   │
            │ AD+DNS+DHCP                  │ AD+DNS    │ │ AD+DHCP   │
            └───────────┘                  └───────────┘ └───────────┘
```

## Components and Interfaces

### Backend (FastAPI)

```
app/
├── main.py              # FastAPI app, роутинг
├── config.py            # Конфигурация приложения
├── auth/
│   ├── pam.py           # PAM аутентификация (root only)
│   └── session.py       # JWT сессии
├── api/
│   ├── servers.py       # CRUD серверов
│   ├── users.py         # AD пользователи
│   ├── computers.py     # AD компьютеры
│   ├── groups.py        # AD группы
│   ├── dns.py           # DNS записи
│   ├── dhcp.py          # DHCP области и резервирования
│   ├── gpo.py           # Групповые политики
│   └── backup.py        # Backup/Restore
├── services/
│   ├── ssh.py           # SSH подключение (paramiko)
│   ├── ldap_cmd.py      # Генерация LDIF и команд ldap*
│   ├── dhcp_parser.py   # Парсер dhcpd.conf
│   └── samba_tool.py    # Обёртка над samba-tool
└── models/
    ├── server.py        # Pydantic модели серверов
    ├── ad.py            # Модели AD объектов
    ├── dhcp.py          # Модели DHCP
    └── dns.py           # Модели DNS
```

### Frontend (React + Tailwind)

```
frontend/
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── Sidebar.tsx
│   │   ├── DataTable.tsx
│   │   ├── ServersSection.tsx
│   │   ├── UsersSection.tsx
│   │   ├── DNSSection.tsx
│   │   ├── DHCPSection.tsx
│   │   └── GPOSection.tsx
│   ├── api/
│   │   └── client.ts    # API клиент (fetch)
│   └── hooks/
│       └── useAuth.ts   # Хук авторизации
└── package.json
```

### REST API Endpoints

```
# Auth
POST   /api/auth/login          # PAM аутентификация
POST   /api/auth/logout         # Завершение сессии
GET    /api/auth/me             # Текущий пользователь

# Servers
GET    /api/servers             # Список серверов
POST   /api/servers             # Добавить сервер
DELETE /api/servers/{id}        # Удалить сервер
POST   /api/servers/{id}/test   # Проверить подключение
POST   /api/servers/{id}/select # Выбрать текущий сервер

# AD Users
GET    /api/ad/users            # Список пользователей
POST   /api/ad/users            # Создать пользователя
PATCH  /api/ad/users/{dn}       # Изменить пользователя
DELETE /api/ad/users/{dn}       # Удалить пользователя
POST   /api/ad/users/{dn}/password  # Сменить пароль

# AD Computers
GET    /api/ad/computers
POST   /api/ad/computers
DELETE /api/ad/computers/{dn}

# AD Groups
GET    /api/ad/groups
POST   /api/ad/groups
DELETE /api/ad/groups/{dn}
POST   /api/ad/groups/{dn}/members      # Добавить члена
DELETE /api/ad/groups/{dn}/members/{member_dn}  # Удалить члена

# DNS
GET    /api/dns/zones
GET    /api/dns/zones/{zone}/records
POST   /api/dns/zones/{zone}/records
DELETE /api/dns/zones/{zone}/records/{name}/{type}

# DHCP
GET    /api/dhcp/subnets
POST   /api/dhcp/subnets
PATCH  /api/dhcp/subnets/{id}
DELETE /api/dhcp/subnets/{id}
GET    /api/dhcp/reservations
POST   /api/dhcp/reservations
DELETE /api/dhcp/reservations/{id}
GET    /api/dhcp/leases

# GPO
GET    /api/gpo
POST   /api/gpo
DELETE /api/gpo/{name}
POST   /api/gpo/{name}/link

# Backup
POST   /api/backup/ldif
POST   /api/backup/dhcp
GET    /api/backup/list
POST   /api/restore/{type}/{filename}

# Logs
GET    /api/logs
```

## Data Models

### Server Configuration (servers.yaml)

```yaml
servers:
  - id: "dc1"
    name: "DC1.domain.local"
    host: "192.168.1.10"
    port: 22
    user: "root"
    auth_type: "key"  # key | password
    key_path: "keys/dc1.pem"
    # password: "encrypted_password"  # если auth_type: password
    services:
      ad: true
      dns: true
      dhcp: true
    domain: "domain.local"
    base_dn: "DC=domain,DC=local"
```

### AD User (Pydantic)

```python
class ADUser(BaseModel):
    dn: str
    sAMAccountName: str
    cn: str
    sn: Optional[str]
    givenName: Optional[str]
    mail: Optional[str]
    userPrincipalName: str
    memberOf: List[str] = []
    userAccountControl: int
    
    @property
    def enabled(self) -> bool:
        return not (self.userAccountControl & 2)
```

### DHCP Subnet

```python
class DHCPSubnet(BaseModel):
    id: str  # generated
    network: str  # "192.168.1.0"
    netmask: str  # "255.255.255.0"
    range_start: Optional[str]
    range_end: Optional[str]
    routers: Optional[str]
    domain_name_servers: Optional[str]
    domain_name: Optional[str]
    default_lease_time: int = 86400
    max_lease_time: int = 172800
```

### DHCP Reservation

```python
class DHCPReservation(BaseModel):
    id: str
    hostname: str
    mac: str  # "00:11:22:33:44:55"
    ip: str
    description: Optional[str]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Session TTL correctness
*For any* успешную аутентификацию root, созданная сессия должна иметь TTL ровно 8 часов (28800 секунд)
**Validates: Requirements 1.2**

### Property 2: Non-root rejection
*For any* пользователя, не являющегося root, аутентификация должна быть отклонена
**Validates: Requirements 1.4**

### Property 3: Logout invalidates session
*For any* активную сессию, после logout токен должен быть недействителен
**Validates: Requirements 1.5**

### Property 4: SSH key permissions
*For any* загруженный SSH ключ, файл должен иметь права 600 (только владелец может читать/писать)
**Validates: Requirements 2.3**

### Property 5: Server config round-trip
*For any* конфигурацию сервера, сохранение в YAML и последующая загрузка должны вернуть эквивалентный объект
**Validates: Requirements 2.5, 11.1, 11.2**

### Property 6: Service availability affects menu
*For any* сервер с недоступным сервисом, соответствующий раздел меню должен быть disabled
**Validates: Requirements 2.8**

### Property 7: Search filter correctness
*For any* поисковый запрос и список объектов, результат фильтрации должен содержать только объекты, содержащие подстроку запроса
**Validates: Requirements 3.2**

### Property 8: LDIF add generation
*For any* валидные данные пользователя AD, сгенерированный LDIF для добавления должен содержать корректный DN, objectClass и все обязательные атрибуты
**Validates: Requirements 3.3**

### Property 9: LDIF modify generation
*For any* изменение атрибута пользователя, сгенерированный LDIF должен содержать changetype:modify и корректную операцию replace/add/delete
**Validates: Requirements 3.4**

### Property 10: Password encoding
*For any* пароль, кодировка unicodePwd должна быть: UTF-16LE строка в кавычках, затем base64
**Validates: Requirements 3.6**

### Property 11: Operation logging
*For any* операцию изменения (CRUD), должна создаваться запись в логе с timestamp, оператором и деталями
**Validates: Requirements 3.7, 10.1**

### Property 12: DHCP config round-trip
*For any* валидный dhcpd.conf, парсинг → модификация → сериализация → парсинг должен сохранять структуру и значения
**Validates: Requirements 7.4, 7.5, 7.6**

### Property 13: DNS command generation
*For any* DNS запись (A, AAAA, CNAME, MX, TXT, SRV), генерация команды samba-tool dns add должна содержать корректные параметры
**Validates: Requirements 6.3**

### Property 14: GPO command generation
*For any* имя GPO, генерация команд samba-tool gpo должна содержать корректный синтаксис
**Validates: Requirements 8.2, 8.3, 8.5**

### Property 15: Server deletion removes from config
*For any* удалённый сервер, он не должен присутствовать в servers.yaml после сохранения
**Validates: Requirements 11.3**

## Error Handling

### SSH Errors
- Connection refused → "Не удалось подключиться к серверу: порт закрыт или сервер недоступен"
- Authentication failed → "Ошибка аутентификации SSH: проверьте ключ или пароль"
- Command timeout → "Превышено время ожидания команды"

### LDAP Errors
- Invalid credentials → "Ошибка LDAP: неверные учётные данные"
- Object not found → "Объект не найден в каталоге"
- Constraint violation → "Нарушение ограничений: {details}"

### DHCP Errors
- Syntax error → "Ошибка синтаксиса dhcpd.conf: {line}"
- Service reload failed → "Не удалось перезагрузить DHCP сервис"

### Validation Errors
- Invalid IP → "Некорректный IP адрес"
- Invalid MAC → "Некорректный MAC адрес"
- Duplicate entry → "Запись уже существует"

## Testing Strategy

### Unit Tests (pytest)
- Тестирование генерации LDIF команд
- Тестирование парсера dhcpd.conf
- Тестирование валидации моделей
- Тестирование генерации команд samba-tool

### Property-Based Tests (hypothesis)
- **Property 5**: Server config round-trip
- **Property 7**: Search filter correctness
- **Property 8-10**: LDIF generation
- **Property 12**: DHCP config round-trip
- **Property 13-14**: Command generation

Каждый property-based тест должен выполнять минимум 100 итераций.

Формат комментария для PBT:
```python
# **Feature: ldc-panel, Property 5: Server config round-trip**
# **Validates: Requirements 2.5, 11.1, 11.2**
@given(server_config=server_configs())
def test_server_config_roundtrip(server_config):
    ...
```

### Integration Tests
- Тестирование SSH подключения (с mock сервером)
- Тестирование API endpoints
- Тестирование аутентификации PAM

### Frontend Tests (vitest)
- Тестирование компонентов React
- Тестирование API клиента
- Тестирование роутинга

## Technology Stack

### Backend
- Python 3.12+
- FastAPI
- Pydantic v2
- paramiko (SSH)
- PyYAML
- python-pam
- PyJWT
- hypothesis (PBT)
- pytest

### Frontend
- React 18
- TypeScript
- Tailwind CSS
- shadcn/ui components
- Vite
- vitest

### Deployment
- systemd service
- gunicorn + uvicorn workers
- nginx reverse proxy (HTTPS)
