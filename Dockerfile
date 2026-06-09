FROM python:3.12-slim

WORKDIR /app

# Install Playwright system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-xcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libatk1.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libnspr4 libnss3 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps firefox

COPY backend/ .

EXPOSE 8000

CMD ["python", "-c", "import os, uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
