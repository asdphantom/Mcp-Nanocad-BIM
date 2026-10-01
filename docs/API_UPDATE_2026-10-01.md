# Обновление API nanoCAD от 01.10.2026

В этой ветке добавлены **18 инструментов** нативного SDK BIM Строительство 26.
Всего MCP-сервер предоставляет **248 инструментов**.

## Навигация

| Область | Функций | Контракты |
|---|---:|---|
| Материалы BIM | 5 | [BIM_MATERIALS.md](BIM_MATERIALS.md) |
| Стены и марки проёмов | 3 | [BIM_EDIT.md](BIM_EDIT.md) |
| Сетки осей, контуры плит, новая марка | 10 | [BIM_SDK_EXTENSIONS.md](BIM_SDK_EXTENSIONS.md) |

[Карта работ](PROGRESS_MAP.md), [матрица SDK](SDK_COMPATIBILITY.md),
[покрытие 102 команд примеров SDK](SDK_COMMANDS.md).

## Примеры аргументов MCP

Примеры handle ниже условные: замените их значениями существующих нативных
объектов активного документа. Примеры создания меняют чертёж.

```json
{"tool":"list_bim_library_materials","arguments":{"name":"бетон","limit":20}}
{"tool":"create_bim_rectangular_grid","arguments":{"name":"Оси камеры","x":[0,5000,10000],"y":[0,5000,10000],"z":[0,3000]}}
{"tool":"create_bim_circular_grid","arguments":{"name":"Круговые оси","x":[3000,6000],"y":[0,90,180,270],"z":[0,3000]}}
{"tool":"redistribute_bim_grid_axes","arguments":{"handle":"A1","axis":"x"}}
{"tool":"shift_bim_wall","arguments":{"handle":"A2","dx":1000,"dy":0,"dz":0}}
{"tool":"get_bim_window_mark","arguments":{"handle":"A3"}}
{"tool":"copy_bim_window_mark","arguments":{"source_handle":"A3","handle":"A4"}}
{"tool":"new_bim_window_mark","arguments":{"handle":"A4","prefix":"ОК"}}
{"tool":"cut_bim_slab_contour","arguments":{"handle":"A5","points":[[1000,1000],[2000,1000],[2000,2000],[1000,2000]]}}
```

Для назначения материала сначала получите точный `id` из библиотеки,
вызовите `add_bim_project_material` с этим `material_id`, затем
`assign_bim_material` с тем же ID и handle объекта. Для привязки к сетке
используйте `assign_bim_coordinate_grid` с handle структурного элемента и
`grid_handle`, полученным при создании или чтении сетки. Обычные линии и solids
не заменяют требуемые нативные классы.

## Установка и проверка

Для новых функций нужны обе части этой версии: Python MCP-сервер и
собранный `engine/dist/CadEngine.Plugin.dll`. Загрузку выполняйте по
[инструкции репозитория](../README.md); плагин в работающем nanoCAD этой
разработкой не заменялся. SDK и DLL nanoCAD отдельно не распространяются.

Последняя полная проверка: **1233 passed, 257 skipped**, общее покрытие строк
Python **86,51%**. Новый SDK use case и остальные BIM use case имеют **100%
покрытия строк**. Это не 100% покрытия ветвей и не покрытие нативного C# SDK.
Сборка Release/x64: **0 ошибок, 11 прежних предупреждений**.

257 пропущенных тестов включают проверки, требующие запущенного nanoCAD.
Новые функции ещё необходимо проверить в приложении: тип созданного объекта,
геометрию, свойства, связи и сохранение результата после повторного открытия DWG.
Поэтому PR остаётся черновиком.
