# Хранилище файлов с доступом по http
## Задание
Реализовать демон, который предоставит HTTP API для загрузки (upload) ,
скачивания (download) и удаления файлов.

+ Upload:
1. получив файл от клиента, демон возвращает в отдельном поле http
response хэш загруженного файла
2. демон сохраняет файл на диск в следующую структуру каталогов:
   store/ab/abcdef12345...
где "abcdef12345..." - имя файла, совпадающее с его хэшем.
/ab/ - подкаталог, состоящий из первых двух символов хэша файла.
3. Алгоритм хэширования - на ваш выбор.

+ Download:
Запрос на скачивание: клиент передаёт параметр - хэш файла. Демон ищет
файл в локальном хранилище и отдаёт его, если находит.

+ Delete:
Запрос на удаление: клиент передаёт параметр - хэш файла. Демон ищет
файл в локальном хранилище и удаляет его, если находит. 

## Установка
Приложение предназначено только для работы на unix-системах
Чтобы установить пакет нужно ввести данную команду

```bash
python setup.py install
```

## Как использовать?

Все доступные опции запуска любой команды можно получить с помощью аргумента --help:

```bash
file_loader --help 
```

Опции для запуска можно указывать как аргументами командной строки, так и переменными окружения с префиксом FILE_LOADER 
(например: вместо аргумента '--working_directory' можно воспользоваться FILE_LOADER_STORAGE').


Чтобы запустить приложение нужно написать

```bash
file_loader
```

Чтобы остановить приложение нужно написать

```bash
file_loader --status stop
```

## Разработка
Установить пакет с обычными и extra-зависимостями "dev"

>pip install -e . .[dev]

Установить пакет только с обычными зависимостями

>pip install -e .

## TODO 
+ tests