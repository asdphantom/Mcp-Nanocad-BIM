# 🏗 nanoCAD MCP Server

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-1085%20passed-green.svg)]()

**MCP-сервер для автоматизации nanoCAD 26** — 221 инструмент для 2D/3D черчения,
инженерных символов, размеров, параметризации, листового металла, сборок и MultiCAD API.

Работает через протокол [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
с любыми MCP-клиентами: opencode, Claude Desktop, Cursor и др.

```
AI Agent (opencode / Claude / Cursor)
     │
     │ MCP (stdio / SSE)
     ▼
Python MCP Server (221 инструмент)
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
| BIM Строительство | 13 | DWG-конструкции и нативные стены, окна, перекрытия, крыши, помещения |
| **ИТОГО** | **221** | |


## nanoCAD BIM Строительство

В редакции BIM Строительство доступны команды `get_construction_status`,
`create_wall_solid`, `create_monolithic_slab`, `insert_construction_plan`,
`set_construction_material`, `complete_window_opening` и
`create_pitched_roof_panel`, `create_native_roof`. Размеры задаются в миллиметрах. Для проёма окна
`complete_window_opening` достраивает подоконную часть стены и перемычку
в уже существующем сквозном разрыве стены.

Геометрия этих команд — редактируемые 3D-тела DWG с назначенным материалом.
Перечисленные выше команды создают DWG-геометрию. Нативные объекты nBIM
создают отдельные инструменты `create_bim_*`, описанные ниже. Для установленной BIM-редакции переключение 3D-вида
через старый .NET endpoint отключено: на данной версии оно аварийно закрывает
процесс. Вид можно сменить в интерфейсе nanoCAD.

## 🚀 Быстрый старт

### 1. Установка

```powershell
# Клонировать репозиторий
git clone https://github.com/Evans-Sense/nanoCAD-MCP.git
cd nanoCAD-MCP

# Установить Python-пакет
cd server
pip install -e .
pip install -e ".[sse,dev]"   # для SSE транспорта и разработки
```

### 2. Установка .NET плагина

**Вариант А (рекомендуется):** В репозитории уже есть собранный плагин —
`engine\dist\CadEngine.Plugin.dll` (Release). Сборка не требуется.

**Вариант Б:** Собрать из исходников:
```powershell
dotnet build engine\CadEngine.Plugin\CadEngine.Plugin.csproj --configuration Release
```

### 3. Подключение плагина к nanoCAD

Добавьте путь к DLL в файл `nCad.ini` (раздел `[\NetModules]`):

```
C:\full\path\to\nanoCAD-MCP\engine\dist\CadEngine.Plugin.dll
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
| Автоматические тесты | 1085 passed, 257 skipped | ✅ |
| Нативные BIM объекты в nanoCAD | стена, окно, перекрытие, крыша, помещение | ✅ Проверено |
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
└── presentation/        # MCP сервер (stdio/SSE), 221 tool definitions, MCP Resources/Prompts

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
| Tools | ✅ 221 | Полный набор 2D/3D/инженерных инструментов |
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
## Нативные инструменты nBIM SDK 26

`create_bim_wall` создаёт `LinearBuildingWall` через
`LinearBuildingWallFactory.Create` из `ncBIMSmgd.dll`. Параметры:
`x1, y1, x2, y2, base_z, height, thickness` (миллиметры).
`wall_type` и `level` пока отклоняются с явной ошибкой: их соответствие
параметрам SDK не проверено. Стена не заменяется 3D-телом.

Для сборки плагина нужны установленная Платформа nanoCAD 26,
SDK .NET 8 (для сборки проекта net6.0-windows) и nBIM SDK 26. Распакуйте архив nBIM SDK в
`work/ncBIM_SDK_26` либо задайте свойство MSBuild `NCadBIMSDK`
с путём к распакованному SDK. Проект по умолчанию ссылается на
платформенные DLL из `C:\Program Files\Nanosoft\nanoCAD x64 26.0`;
путь можно переопределить свойством `NanoCadPlatformRoot`.

Пример вызова MCP:

```json
{"name":"create_bim_wall","arguments":{"x1":0,"y1":0,"x2":6000,"y2":0,"base_z":0,"height":3300,"thickness":300}}
```

`list_bim_windows` получает объекты библиотеки, а `create_bim_window` вставляет
нативный `BuildingOpening` в указанную стену и связывает проём со стеной.
`create_bim_slab`, `create_bim_roof` и `create_bim_space` создают нативные
контурные объекты SDK по массиву точек `[[x,y], ...]`. Все размеры в миллиметрах;
угол крыши задаётся в градусах.

Полная [матрица совместимости SDK](docs/SDK_COMPATIBILITY.md) показывает
реализованные фабрики и остальные разделы архива. SDK содержит 102 команды в
примерах; они ещё не все доступны через MCP.

После сохранения чертежей и закрытия nanoCAD скопируйте собранный файл:

```powershell
Copy-Item engine\CadEngine.Plugin\bin\Release\CadEngine.Plugin.dll engine\dist\CadEngine.Plugin.dll -Force
```

В текущей установке `nCad.ini` уже загружает DLL из `engine/dist`.
Запустите nanoCAD BIM Строительство 26 с новым тестовым чертежом
и проверьте, что результат содержит нативный тип объекта, например
`entity_type: LinearBuildingWall`.
