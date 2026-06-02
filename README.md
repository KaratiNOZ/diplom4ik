# ORDENTIST CLINIC — АИС стоматологической клиники

Веб-приложение на Flask для автоматизации работы стоматологической клиники.

## Стек

- **Backend:** Python 3.10+, Flask 3.1, SQLAlchemy 2.0
- **БД:** MySQL 8+ (через PyMySQL)
- **Frontend:** Jinja2, HTML/CSS/JS (без фреймворков)

## Функциональность

- Регистрация и авторизация (пациент / врач / менеджер / администратор)
- Онлайн-запись на приём с выбором врача, услуги, времени
- Личный кабинет для каждой роли
- История лечения с печатью в PDF
- Система достижений для пациентов
- Прайс-лист услуг с поиском
- Управление пациентами и сотрудниками
- Карточка пациента с полной историей
- Восстановление пароля
- Мобильная версия

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone <url>
cd diplom
```

### 2. Создать и активировать виртуальное окружение

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Создать базу данных MySQL

```sql
CREATE DATABASE ais_dentistry CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Настроить подключение к БД

Открой `config.py` и укажи свои данные:

```python
DB_USER     = "root"
DB_PASSWORD = "твой_пароль"
DB_NAME     = "ais_dentistry"
```

Или задай через переменные окружения:

```bash
set DB_PASSWORD=твой_пароль   # Windows
export DB_PASSWORD=твой_пароль  # Linux/macOS
```

### 6. Инициализировать БД и загрузить демо-данные

```bash
python init_db.py
```

### 7. Запустить приложение

```bash
python app.py
```

Открыть в браузере: **http://127.0.0.1:5000**

---

## Демо-аккаунты

| Email | Пароль | Роль |
|---|---|---|
| patient@demo.ru | 1234 | Пациент |
| doctor@demo.ru | 1234 | Врач (терапевт) |
| doctor2@demo.ru | 1234 | Врач (ортодонт) |
| manager@demo.ru | 1234 | Менеджер |
| admin@demo.ru | 1234 | Администратор |

---

## Структура проекта

```
diplom/
├── app.py              # Точка входа, все роуты
├── models.py           # ORM-модели SQLAlchemy
├── config.py           # Конфигурация (БД, Flask)
├── init_db.py          # Создание таблиц и демо-данных
├── requirements.txt    # Зависимости Python
├── templates/          # HTML-шаблоны Jinja2
├── css/                # Стили
├── js/                 # JavaScript
└── images/             # Изображения (логотип, фото врачей)
```
