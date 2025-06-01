import redis

# Подключение к локальному Redis
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True  # Автоматически декодировать строки в UTF-8
)

# Проверка подключения
try:
    redis_client.ping()
    print("✅ Успешное подключение к Redis")
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")