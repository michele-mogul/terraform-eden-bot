FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# DejaVu Sans for the hexagram pictures (Pillow's built-in font has no accented letters)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY eden ./eden
RUN useradd -u 1000 -M eden
USER eden
CMD ["python", "-m", "eden"]
