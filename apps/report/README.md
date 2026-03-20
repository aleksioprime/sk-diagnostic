# Report Service for NocoBase

Готовый сервис генерации отчётов на FastAPI для вызова из NocoBase.

## Что умеет
- генерировать DOCX по шаблону Word через `docxtpl`
- конвертировать DOCX в PDF через `Gotenberg`
- генерировать XLSX по JSON-описанию шаблона
- отдавать готовый файл по ссылке
- использоваться из NocoBase через HTTP Request node

## Структура
- `app/` — код FastAPI
- `templates/` — шаблоны отчётов
- `output/` — готовые файлы
- `docker-compose.yml` — запуск сервиса и Gotenberg

## Запуск
```bash
cp .env.example .env
# при необходимости отредактируй REPORT_API_TOKEN и REPORT_BASE_URL

docker compose up -d --build
```

Проверка:
```bash
curl http://localhost:8000/health
```

## Эндпойнты
### 1) Список шаблонов
```bash
curl -H "X-API-Token: change-me" http://localhost:8000/templates
```

### 2) Генерация DOCX
```bash
curl -X POST http://localhost:8000/reports/render \
  -H "Content-Type: application/json" \
  -H "X-API-Token: change-me" \
  -d '{
    "template": "diagnostic_result.docx",
    "filename": "report_123",
    "output": "docx",
    "data": {
      "student": {"full_name": "Иванов Иван", "class_name": "8А"},
      "result": {"total_score": 42, "level": "III", "interpretation": "Норма"},
      "scales": [
        {"title": "Тревожность", "value": 18, "level": "high"},
        {"title": "Познавательная активность", "value": 25, "level": "medium"}
      ]
    }
  }'
```

### 3) Генерация PDF
```bash
curl -X POST http://localhost:8000/reports/render \
  -H "Content-Type: application/json" \
  -H "X-API-Token: change-me" \
  -d '{
    "template": "diagnostic_result.docx",
    "filename": "report_123",
    "output": "pdf",
    "data": {
      "student": {"full_name": "Иванов Иван", "class_name": "8А"},
      "result": {"total_score": 42, "level": "III", "interpretation": "Норма"},
      "scales": [
        {"title": "Тревожность", "value": 18, "level": "high"},
        {"title": "Познавательная активность", "value": 25, "level": "medium"}
      ]
    }
  }'
```

### 4) Генерация XLSX
```bash
curl -X POST http://localhost:8000/reports/render \
  -H "Content-Type: application/json" \
  -H "X-API-Token: change-me" \
  -d '{
    "template": "diagnostic_export_template.json",
    "filename": "report_123",
    "output": "xlsx",
    "data": {
      "student": {"full_name": "Иванов Иван", "class_name": "8А"},
      "result": {"total_score": 42, "level": "III", "interpretation": "Норма"},
      "scales": [
        {"title": "Тревожность", "value": 18, "level": "high"},
        {"title": "Познавательная активность", "value": 25, "level": "medium"}
      ]
    }
  }'
```

## Как сделать шаблон DOCX
Сервис использует `docxtpl`: в Word-шаблон вставляются Jinja-переменные, например:
- `{{ student.full_name }}`
- `{{ result.total_score }}`
- цикл по шкалам:
  - `{% for item in scales %}`
  - `{{ item.title }}`
  - `{{ item.value }}`
  - `{{ item.level }}`
  - `{% endfor %}`

## Интеграция с NocoBase
В NocoBase можно использовать built-in HTTP Request node, который отправляет JSON или `application/x-www-form-urlencoded` на внешний сервис.

### Вариант 1: через workflow
1. Создай workflow.
2. Добавь trigger от кнопки или post-action.
3. Добавь узел **HTTP Request**.
4. Настрой:
   - Method: `POST`
   - URL: `http://report-service:8000/reports/render`
   - Headers:
     - `Content-Type: application/json`
     - `X-API-Token: change-me`
   - Body:
```json
{
  "template": "diagnostic_result.docx",
  "filename": "diagnostic_{{$nRecord.id}}",
  "output": "pdf",
  "data": {
    "student": {
      "full_name": "{{$nRecord.person?.full_name}}",
      "class_name": "{{$nRecord.person?.class_name}}"
    },
    "result": {
      "total_score": "{{$nRecord.total_score}}",
      "level": "{{$nRecord.level}}",
      "interpretation": "{{$nRecord.interpretation}}"
    },
    "scales": "{{$json.scales}}"
  }
}
```
5. Возьми из ответа `download_url` и сохрани в поле записи, либо покажи пользователю.

### Вариант 2: через свой action / кнопку
Можно вызывать этот же endpoint с кнопки и открывать `download_url`.

## Что нужно поменять под себя
- положить реальный шаблон `diagnostic_result.docx` в папку `templates/`
- при необходимости поставить внешний `REPORT_BASE_URL`, например `https://reports.example.com`
- вынести `REPORT_API_TOKEN` в секреты Coolify / Docker Compose

## Ограничения текущей версии
- PDF строится только из DOCX через Gotenberg
- XLSX сейчас генерируется не из xlsx-шаблона, а из JSON-описания
- очистка старых файлов пока не добавлена cron-задачей

## Почему такой стек
FastAPI нормально разворачивается в контейнерах, `docxtpl` предназначен для генерации DOCX из Word-шаблонов, а Gotenberg умеет конвертировать офисные документы в PDF через LibreOffice. В NocoBase есть встроенный HTTP Request node для вызова внешних сервисов. citeturn615768search0turn615768search1turn615768search2turn615768search6
