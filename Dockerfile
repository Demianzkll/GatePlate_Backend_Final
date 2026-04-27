# ── Base image ──────────────────────────────────────────────
FROM python:3.12-slim


# ── System deps for OpenCV, YOLOv8, Tesseract, MySQL ──────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV runtimelibs
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    # Tesseract OCR (used by pytesseract)
    tesseract-ocr \
    tesseract-ocr-ukr \
    # MySQL client libs (for mysqlclient wheel)
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

# ── Створення не-root користувача (ВИМОГА HUGGING FACE) ─────
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# ── Working directory ──────────────────────────────────────
WORKDIR $HOME/app

# ── Install Python deps ───────────────────────────────────
COPY --chown=user requirements.txt .

# Встановлюємо CPU-версію PyTorch (займає 150МБ замість 2.5ГБ), а потім інші залежності
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy project code ─────────────────────────────────────
COPY --chown=user . $HOME/app

# ── Collect static files ──────────────────────────────────
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# ── Expose port 7860 (Hugging Face requirement) ───────────
EXPOSE 7860

# ── Run server on port 7860 ───────────────────────────────
CMD ["gunicorn", "core.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:7860"]

