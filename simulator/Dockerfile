FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY simulator.py .
USER nobody
CMD ["python", "simulator.py"]
