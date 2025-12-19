# Requirements Document

## Introduction

Linux DC Panel — веб-панель администрирования для управления Samba AD DC, DNS и DHCP серверами с поддержкой мультидоменов и мультиконтроллеров. Панель устанавливается на отдельный сервер и подключается к контроллерам домена по SSH. Авторизация только под локальным root. Все операции выполняются через CLI-утилиты (ldbsearch, ldapmodify, samba-tool) для максимальной производительности.

## Glossary

- **LDC Panel** — Linux DC Panel, веб-панель администрирования
- **DC (Domain Controller)** — контроллер домена Samba AD
- **Samba AD** — реализация Active Directory на базе Samba
- **LDAP** — протокол доступа к каталогам
- **DHCP** — протокол динамической конфигурации хостов
- **DNS** — система доменных имён
- **GPO (Group Policy Object)** — объект групповой политики
- **SSH** — протокол безопасного удалённого доступа
- **ldbsearch** — утилита быстрого поиска в Samba LDB
- **ldapmodify** — утилита модификации LDAP записей
- **Backend** — серверная часть приложения (FastAPI)
- **Frontend** — клиентская часть приложения (React)

## Requirements

### Requirement 1: Аутентификация

**User Story:** As a системный администратор, I want авторизоваться в панели под локальным root, so that я могу безопасно управлять контроллерами доменов.

#### Acceptance Criteria

1. WHEN пользователь открывает панель без активной сессии THEN THE LDC Panel SHALL отобразить форму входа с полями логин и пароль
2. WHEN пользователь вводит корректные учётные данные root THEN THE LDC Panel SHALL создать сессию с TTL 8 часов и перенаправить на главную страницу
3. WHEN пользователь вводит некорректные учётные данные THEN THE LDC Panel SHALL отобразить сообщение об ошибке и записать попытку в лог
4. WHEN пользователь не является root THEN THE LDC Panel SHALL отклонить авторизацию с сообщением "Доступ разрешён только для root"
5. WHEN пользователь нажимает кнопку Logout THEN THE LDC Panel SHALL завершить сессию и перенаправить на форму входа

### Requirement 2: Управление серверами (контроллерами)

**User Story:** As a системный администратор, I want добавлять и удалять контроллеры доменов, so that я могу управлять несколькими DC из разных доменов через единую панель.

#### Acceptance Criteria

1. WHEN пользователь открывает раздел "Серверы" THEN THE LDC Panel SHALL отобразить список всех добавленных контроллеров с их статусом
2. WHEN пользователь добавляет новый сервер THEN THE LDC Panel SHALL запросить: hostname, IP, SSH порт, SSH пользователь, способ аутентификации (пароль или ключ)
3. WHEN пользователь загружает SSH ключ THEN THE LDC Panel SHALL сохранить ключ в защищённую директорию на сервере панели
4. WHEN пользователь сохраняет сервер THEN THE LDC Panel SHALL проверить SSH подключение и наличие сервисов (samba-ad-dc, isc-dhcp-server, bind9)
5. WHEN проверка подключения успешна THEN THE LDC Panel SHALL сохранить конфигурацию сервера в YAML файл и отобразить доступные сервисы
6. WHEN проверка подключения неуспешна THEN THE LDC Panel SHALL отобразить сообщение об ошибке с деталями
7. WHEN пользователь выбирает текущий сервер из выпадающего списка THEN THE LDC Panel SHALL переключить контекст и обновить доступность разделов (AD, DNS, DHCP, GPO)
8. WHEN сервис недоступен на выбранном сервере THEN THE LDC Panel SHALL отключить соответствующий раздел в меню

### Requirement 3: Управление пользователями AD

**User Story:** As a системный администратор, I want управлять пользователями Active Directory, so that я могу создавать, редактировать и удалять учётные записи.

#### Acceptance Criteria

1. WHEN пользователь открывает раздел "AD → Пользователи" THEN THE LDC Panel SHALL отобразить список пользователей с полями: логин, полное имя, email, группы, статус
2. WHEN пользователь выполняет поиск THEN THE LDC Panel SHALL отфильтровать список по введённому тексту
3. WHEN пользователь добавляет нового пользователя THEN THE LDC Panel SHALL выполнить ldapmodify с changetype:add на выбранном DC
4. WHEN пользователь редактирует существующего пользователя THEN THE LDC Panel SHALL выполнить ldapmodify с changetype:modify на выбранном DC
5. WHEN пользователь удаляет пользователя THEN THE LDC Panel SHALL запросить подтверждение и выполнить ldapdelete на выбранном DC
6. WHEN пользователь меняет пароль пользователя AD THEN THE LDC Panel SHALL выполнить ldapmodify с атрибутом unicodePwd в base64
7. WHEN операция CRUD завершена THEN THE LDC Panel SHALL записать действие в лог с указанием оператора и деталей операции

### Requirement 4: Управление компьютерами AD

**User Story:** As a системный администратор, I want просматривать и управлять компьютерами домена, so that я могу контролировать устройства в сети.

#### Acceptance Criteria

1. WHEN пользователь открывает раздел "AD → Компьютеры" THEN THE LDC Panel SHALL отобразить список компьютеров с полями: имя, ОС, IP, последняя активность, статус
2. WHEN пользователь добавляет компьютер THEN THE LDC Panel SHALL выполнить ldapmodify с changetype:add для объекта computer
3. WHEN пользователь удаляет компьютер THEN THE LDC Panel SHALL запросить подтверждение и выполнить ldapdelete
4. WHEN операция завершена THEN THE LDC Panel SHALL записать действие в лог

### Requirement 5: Управление группами AD

**User Story:** As a системный администратор, I want управлять группами Active Directory, so that я могу организовывать пользователей и назначать права.

#### Acceptance Criteria

1. WHEN пользователь открывает раздел "AD → Группы" THEN THE LDC Panel SHALL отобразить список групп с полями: имя, описание, количество членов
2. WHEN пользователь создаёт группу THEN THE LDC Panel SHALL выполнить ldapmodify с changetype:add для объекта group
3. WHEN пользователь добавляет члена в группу THEN THE LDC Panel SHALL выполнить ldapmodify с add:member
4. WHEN пользователь удаляет члена из группы THEN THE LDC Panel SHALL выполнить ldapmodify с delete:member
5. WHEN пользователь удаляет группу THEN THE LDC Panel SHALL запросить подтверждение и выполнить ldapdelete

### Requirement 6: Управление DNS

**User Story:** As a системный администратор, I want управлять DNS записями, so that я могу настраивать разрешение имён в домене.

#### Acceptance Criteria

1. WHEN пользователь открывает раздел "DNS" THEN THE LDC Panel SHALL отобразить список DNS зон
2. WHEN пользователь выбирает зону THEN THE LDC Panel SHALL отобразить записи зоны (A, AAAA, CNAME, MX, TXT, SRV)
3. WHEN пользователь добавляет DNS запись THEN THE LDC Panel SHALL выполнить samba-tool dns add на выбранном DC
4. WHEN пользователь удаляет DNS запись THEN THE LDC Panel SHALL выполнить samba-tool dns delete на выбранном DC
5. WHEN пользователь редактирует DNS запись THEN THE LDC Panel SHALL удалить старую и создать новую запись

### Requirement 7: Управление DHCP

**User Story:** As a системный администратор, I want управлять DHCP сервером, so that я могу настраивать автоматическую выдачу IP адресов.

#### Acceptance Criteria

1. WHEN пользователь открывает раздел "DHCP → Области" THEN THE LDC Panel SHALL отобразить список subnet из dhcpd.conf
2. WHEN пользователь открывает раздел "DHCP → Резервирования" THEN THE LDC Panel SHALL отобразить список host записей из dhcpd.conf
3. WHEN пользователь открывает раздел "DHCP → Аренды" THEN THE LDC Panel SHALL отобразить активные аренды из dhcpd.leases
4. WHEN пользователь добавляет область DHCP THEN THE LDC Panel SHALL добавить блок subnet в dhcpd.conf и выполнить systemctl reload isc-dhcp-server
5. WHEN пользователь добавляет резервирование THEN THE LDC Panel SHALL добавить блок host в dhcpd.conf и выполнить systemctl reload isc-dhcp-server
6. WHEN пользователь редактирует или удаляет запись THEN THE LDC Panel SHALL обновить dhcpd.conf и выполнить reload сервиса
7. WHEN конфигурация DHCP изменена THEN THE LDC Panel SHALL проверить синтаксис перед применением через dhcpd -t

### Requirement 8: Управление GPO

**User Story:** As a системный администратор, I want управлять групповыми политиками, so that я могу централизованно настраивать параметры для пользователей и компьютеров.

#### Acceptance Criteria

1. WHEN пользователь открывает раздел "GPO" THEN THE LDC Panel SHALL отобразить список групповых политик через samba-tool gpo listall
2. WHEN пользователь создаёт GPO THEN THE LDC Panel SHALL выполнить samba-tool gpo create
3. WHEN пользователь связывает GPO с OU THEN THE LDC Panel SHALL выполнить samba-tool gpo setlink
4. WHEN пользователь редактирует параметры GPO THEN THE LDC Panel SHALL модифицировать соответствующие файлы политики в SYSVOL
5. WHEN пользователь удаляет GPO THEN THE LDC Panel SHALL выполнить samba-tool gpo del

### Requirement 9: Backup и Restore

**User Story:** As a системный администратор, I want создавать резервные копии и восстанавливать данные, so that я могу защитить конфигурацию от потери.

#### Acceptance Criteria

1. WHEN пользователь нажимает "Backup LDIF" THEN THE LDC Panel SHALL выполнить ldapsearch и сохранить результат в /backups/ldif/ на DC
2. WHEN пользователь нажимает "Backup DHCP" THEN THE LDC Panel SHALL скопировать dhcpd.conf в /backups/dhcp/ на DC
3. WHEN пользователь выбирает backup для восстановления THEN THE LDC Panel SHALL отобразить список доступных бэкапов
4. WHEN пользователь подтверждает восстановление LDIF THEN THE LDC Panel SHALL выполнить ldapadd из выбранного файла
5. WHEN пользователь подтверждает восстановление DHCP THEN THE LDC Panel SHALL заменить dhcpd.conf и выполнить reload сервиса

### Requirement 10: Логирование

**User Story:** As a системный администратор, I want видеть историю всех операций, so that я могу отслеживать изменения и проводить аудит.

#### Acceptance Criteria

1. WHEN любая операция изменения выполняется THEN THE LDC Panel SHALL записать в лог: timestamp, уровень, оператор, действие, объект, детали
2. WHEN пользователь открывает раздел "Логи" THEN THE LDC Panel SHALL отобразить последние записи с возможностью фильтрации
3. WHILE логфайл существует более 1 года THEN THE LDC Panel SHALL применить ротацию через logrotate

### Requirement 11: Конфигурация серверов

**User Story:** As a системный администратор, I want хранить конфигурацию серверов в файле, so that конфигурация сохраняется между перезапусками панели.

#### Acceptance Criteria

1. WHEN пользователь добавляет сервер THEN THE LDC Panel SHALL сохранить конфигурацию в servers.yaml в корне проекта
2. WHEN панель запускается THEN THE LDC Panel SHALL загрузить список серверов из servers.yaml
3. WHEN пользователь удаляет сервер THEN THE LDC Panel SHALL удалить запись из servers.yaml
4. WHEN SSH ключ загружается THEN THE LDC Panel SHALL сохранить ключ в директорию keys/ с правами 600
