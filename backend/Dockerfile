# Single image used for both dev and production — docker-compose.yml (dev)
# mounts the source and adds --reload; docker-compose.prod.yml uses this
# image's own CMD (no reload, no source mount). No logic is duplicated
# between the two: the Dockerfile never branches on environment.
FROM python:3.11-slim

# Tesseract + language pack, and the shared libs OpenCV/PyMuPDF need at
# runtime (not just build time) — matches backend/README.md's manual
# installation instructions, just baked into the image instead.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p storage/originals storage/processed storage/temporary

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
