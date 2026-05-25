# DOCUMENT CONVERTER

## Конфигурация

Все параметры читаются из переменных окружения. Для локального запуска скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Поддерживаемые переменные:

| Переменная | Обязательная | Описание |
|---|---|---|
| `OPENAI_API_KEY` | да | API-ключ OpenAI (или совместимого провайдера) |
| `OPENAI_DEFAULT_MODEL_OCR` | да | Модель LLM по умолчанию для OCR |
| `OPENAI_DEFAULT_MODEL_IMAGE` | да | Модель LLM по умолчанию для интерпретации изображений |
| `OPENAI_BASE_URL` | нет | Альтернативный base URL для OpenAI-совместимого API |
| `YANDEX_OCR_API_KEY` | да | API-ключ Yandex OCR |
| `LOGGING_LEVEL` | нет | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, ...), по умолчанию `INFO` |
| `REDIS_HOST` | да | Хост Redis (в `docker-compose` задаётся автоматически) |

## Запуск

```bash
docker compose up --build
```

API будет доступно по адресу `http://127.0.0.1:8110`.

## To Markdown

`POST /api/v1/convert/to-markdown` — конвертация документа в Markdown. Авторизация не требуется. Описание схемы запросов и ответов — в [docs/endpoints.yaml](docs/endpoints.yaml).
