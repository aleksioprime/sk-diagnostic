# SK Diagnostics Frontend

Frontend для NocoBase-коллекций диагностики.

Основные сценарии:

- авторизованный пользователь видит только свои попытки из `attempts` и проходит выданный тест;
- пользователь с ролью `psycho` или `admin` видит список результатов из `attempt_results`;
- детальная страница результата показывает оформленный отчёт и полную таблицу по JSON.

Запуск:

```bash
npm install
npm run dev
```

Сборка:

```bash
npm run build
```

Ключевые env:

- `VITE_API_URL` — URL NocoBase для dev proxy.
- `VITE_APP_TITLE` — заголовок приложения.
- `VITE_PSYCHO_ROLE` — имя роли для доступа к страницам результатов.
