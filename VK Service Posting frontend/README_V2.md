# Frontend Versions

## Структура

- `vk_service_posting` - текущий frontend `V1`
- `vk_service_posting_v2` - новый frontend `V2`

## Локальный запуск

### V1

```bash
cd "VK Service Posting frontend/vk_service_posting"
npm run dev
```

Ожидаемый адрес: `http://localhost:5173/`

### V2

```bash
cd "VK Service Posting frontend/vk_service_posting_v2"
npm run dev
```

Ожидаемый адрес: `http://localhost:5174/v2/`

## Backend для V2

- `V2` использует тот же `VITE_API_BASE_URL`, что и `V1`
- для локальной разработки backend должен разрешать `http://localhost:5174`
- summary для нового overview отдается ручкой `/users/{user_id}/vk_accounts/v2_summary`

## Прод-схема

- `V1` обслуживается по `/`
- `V2` обслуживается по `/v2/`
- nginx и `Dockerfile` уже подготовлены под сборку и раздачу обеих версий в одном контейнере
