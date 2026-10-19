### Lab 3 | РБПО| Горбачева Маргарита Валерьевна 24КНТ4

#### Структура работы:
1) Программа на C++ с намеренными уязвимостями в коде `vulnerableZoo.cpp`
2) Исправленная программа на C++ `okZoo.cpp`
3) Инструкция сборки
4) Промпт и название использованной для генерации кода LLM
5) Команды и отчеты инструментов
6) Краткая таблица разбора с OWASP/БДУ ФСТЭК

#### Запуск программы:
1. Запуск уязвимой версии
```bash
g++ -O0 -g -o vulnerablezoo vulnerableZoo.cpp -lz
./vulnerablezoo
```
2. Запуск исправленной версии
```bash
g++ -O0 -g -o okzoo okZoo.cpp -lz
./okzoo
```
Затем можно вводить животных, например:
```bash
Penguin, Trololo, 5
```
Или же можно вводить из файла:
```bash
./vulnerablezoo input.txt
./okzoo input.txt
```

**Важно:** перед тем, как проверять файлы на уязвимости, необходимо установить пакеты для работы с SAST, SCA

```bash
brew install cppcheck clang-tidy flawfinder syft trivy

brew install llvm
```