# 🏗 nanoCAD MCP Server

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-1038%20unit-green.svg)]()

**MCP-сервер для автоматизации nanoCAD 26** — 207 инструментов для 2D/3D черчения,
инженерных символов, размеров, параметризации, листового металла, сборок и MultiCAD API.

Работает через протокол [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
с любыми MCP-клиентами: opencode, Claude Desktop, Cursor и др.

```
AI Agent (opencode / Claude / Cursor)
     │
     │ MCP (stdio / SSE)
     ▼
Python MCP Server (207 инструментов)
     │
     │ HTTP REST (localhost:5080)
     ▼
.NET Engine Plugin (внутри nanoCAD 26)
     │
     │ Multicad.* API / Teigha
     ▼
nanoCAD — чертёж
```

## ✨ Возможности

| Категория | Инструментов | Примеры |
|-----------|:-----------:|---------|
| 2D примитивы | 16 | линия, окружность, дуга, сплайн, эллипс, геликс |
| 3D тела | 16 | box, сфера, цилиндр, конус, тор, клин, пирамида |
| Булевы операции | 3 | объединение, вычитание, пересечение |
| 3D операции | 7 | выдавливание, вращение, сдвиг, лофтинг, скругление, фаска |
| Размеры | 8 | линейный, радиальный, диаметральный, угловой, ординатный |
| Инженерные символы | 9 | шероховатость (ГОСТ), допуски, базы, сварка, выноски |
| Слои | 11 | создание, изоляция, заморозка, удаление |
| Блоки | 6 | создание, вставка, расчленение, удаление |
| Таблицы | 4 | создание, редактирование ячеек |
| Штриховка | 4 | штриховка, градиент |
| Трансформации | 7 | перемещение, поворот, масштаб, зеркало |
| 3D трансформации | 6 | 3D массив, выравнивание, 3D зеркало |
| 2D ограничения | 12 | параллельность, перпендикулярность, касание, концентричность |
| Сборки | 5 | сопряжение, вставка детали, симметрия |
| Листовой металл | 5 | базовая пластина, отбортовка, гибка, развёртка |
| 3D особенности | 13 | отверстия, оболочка, эскизы, выдавливание, вращение |
| Документы | 16 | создание, открытие, сохранение, экспорт PDF/DWG/DXF/STEP/STL/IFC |
| Система | 6 | переменные, шрифты, типы линий, произвольные команды |
| Измерения | 6 | расстояние, угол, площадь, информация об объекте |
| NURBS / IFC | 5 | NURBS-кривые, поверхности, IFC импорт |
| MultiCAD API | 12 | оси, помещения, параметрические объекты, реакторы |
| Прочее | 12 | сетка, выборка, обрезка, удлинение, смещение, вьюпорт, рендер |
| **ИТОГО** | **207** | |

## 🚀 Быстрый старт

### 1. Установка

```powershell
# Клонировать репозиторий
git clone https://github.com/nanoCAD/nanoCAD-MCP.git
cd nanoCAD-MCP

# Установить Python-пакет
cd server
pip install -e .
pip install -e ".[sse,dev]"   # для SSE транспорта и разработки
```

### 2. Установка .NET плагина

**Вариант А (рекомендуется):** В репозитории уже есть собранный плагин —
`engine\dist\CadEngine.Plugin.dll` (Release, 254 KB). Сборка не требуется.

**Вариант Б:** Собрать из исходников:
```powershell
dotnet build engine\CadEngine.Plugin\CadEngine.Plugin.csproj --configuration Release
```

### 3. Подключение плагина к nanoCAD

Добавьте путь к DLL в файл `nCad.ini` (раздел `[\NetModules]`):

```
F:\full\path\to\nanoCAD-MCP\engine\CadEngine.Plugin\bin\Debug\CadEngine.Plugin.dll
```

### 4. Запуск

```powershell
# Терминал 1: Запустите nanoCAD 26 (с загруженным плагином)

# Терминал 2: Запустите MCP-сервер
cd server
py -m src.presentation.server
```

### 5. Подключение клиента

**opencode** (`opencode.json`):
```json
{
  "mcp": {
    "nanoCAD": {
      "command": ["python", "-u", "-m", "src.presentation.server"],
      "cwd": "F:\\nanoCAD\\server",
      "environment": { "PYTHONPATH": "F:\\nanoCAD\\server" }
    }
  }
}
```

> **Важно:** флаг `-u` (unbuffered stdout) обязателен на Windows.
> Без него MCP-клиент не получит ответ от сервера из-за буферизации вывода.

**Claude Desktop** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "nanoCAD": {
      "command": "python",
      "args": ["-u", "-m", "src.presentation.server"],
      "cwd": "F:\\nanoCAD\\server"
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "nanoCAD": {
      "command": "python",
      "args": ["-u", "-m", "src.presentation.server"],
      "cwd": "F:\\nanoCAD\\server"
    }
  }
}
```

### 6. Проверка

```powershell
# Проверить, что сервер отвечает
Invoke-RestMethod -Uri "http://localhost:5080/api/system/health"
```

## 🔧 Команды

```powershell
# Запуск сервера (флаг -u обязателен на Windows)
py -u -m src.presentation.server
py -u -m src.presentation.server --transport sse --port 8081   # удалённый доступ

# Тесты
py -m pytest server/tests/ -v -q                                # все
py -m pytest server/tests/unit/ --cov=src                       # unit + coverage
py -m pytest server/tests/integration/ -v                       # интеграционные

# Линтинг
py -m ruff check server/src/
py -m ruff format server/src/
py -m mypy server/src/
```

## 🧪 Тестовый статус

| Вид тестов | Количество | Статус |
|-----------|:----------:|:------:|
| Unit-тесты | 1038 | ✅ Pass |
| Интеграционные (живой nanoCAD) | 2 (+257 skipped) | ✅ Pass |
| Типы (mypy --strict) | 0 errors | ✅ Clean |
| Линтер (ruff) | 0 errors | ✅ Clean |
| Покрытие Python-кода | 85% | ✅ |
| MCP E2E (init → list → call) | 3/3 шага | ✅ |
| MCP Resources | 4 + 1 template | ✅ |
| MCP Prompts | 2 stubs | ✅ |

## 🔌 Архитектура

```
server/src/
├── domain/              # Сущности, Value Objects, порты (ICadRepository, protocols)
├── application/         # Use cases, DTO, бизнес-логика
├── infrastructure/      # HTTP bridge (.NET plugin), COM bridge (fallback)
└── presentation/        # MCP сервер (stdio/SSE), 207 tool definitions, MCP Resources/Prompts

engine/CadEngine.Plugin/
├── Services/            # 35+ C# сервисов (EntityService, SolidService, SymbolService ...)
├── Models/              # DTO модели запросов/ответов
└── HttpServer.cs        # REST API (localhost:5080, 170+ endpoints)
```

**Приоритет подключения:** HTTP (.NET engine) → COM → offline

**Graceful degradation:** Если nanoCAD недоступен, все инструменты возвращают
понятное русское сообщение об ошибке. `health_check` и `get_system_info`
остаются рабочими для диагностики.

## ✅ MCP Compliance

| Возможность | Статус | Описание |
|-------------|:------:|----------|
| Tools | ✅ 207 | Полный набор 2D/3D/инженерных инструментов |
| Resources | ✅ 4 + 1 template | Чтение документа, слоёв, системы, параметров, сущностей |
| Prompts | ✅ 2 stubs | `create-part` и `parametric-design` для пошаговых сценариев |
| isError | ✅ | Все пути ошибок возвращают `CallToolResult(isError=True)` |
| Input validation | ✅ | Автоматическая валидация через `validate_tool_input` |
| SSE transport | ✅ | Альтернативный транспорт для удалённого доступа на :8081 |

## 📦 Системные требования

- **ОС:** Windows 10/11 64-bit
- **Python:** 3.12+
- **nanoCAD:** 26 (Free/Plus/Pro) с загруженным .NET плагином
- **.NET:** 8.0 SDK (только для сборки плагина)

## 🛠 Разработка

### Добавление нового инструмента

1. **C# (engine):** DTO в `ApiModels.cs`, метод в сервисе, route в `HttpServer.cs`
2. **Python bridge:** Метод в `http_bridge.py`
3. **Use case:** Класс в `extended_use_cases.py` / `use_cases.py`
4. **MCP:** Определение в `tool_defs.py`, handler map в `server.py`
5. **Тесты:** Unit + integration

### Принципы

- **MultiCAD API first** — все новые инструменты через .NET engine
- **Никаких SendCommand** — все вызовы через синхронный `Editor.Command()` или programmatic API
- **Clean Architecture** — строгие границы слоёв (domain → application → infrastructure → presentation)
- **TDD** — сначала тест, потом реализация

## 📄 Лицензия

MIT License — проект с открытым исходным кодом.

## 👤 Автор

**Виноградов Иван** — разработчик и архитектор проекта.

## 🙏 Благодарности

- Разработчикам [nanoCAD](https://nanocad.ru) и MultiCAD API
- Сообществу [Model Context Protocol](https://modelcontextprotocol.io/)
- Всем контрибьюторам и тестировщикам
