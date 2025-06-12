FROM python:3.11-slim

# 1. Устанавливаем системные зависимости для сборки расширений C (asyncpg, psycopg2)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Копируем и ставим зависимости
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 3. Копируем код приложения
COPY . .

# 4. Отключаем буферизацию вывода
ENV PYTHONUNBUFFERED=1

# 5. Открываем порт (необязательно, но удобно для документации)
EXPOSE 8000

# 6. Запуск
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
