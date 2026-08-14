FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m pip install --no-cache-dir fastapi==0.128.0 uvicorn[standard]==0.40.0

COPY backend/tests/mock_neis /app/mock_neis

EXPOSE 8081

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/hub/schoolInfo?Key=test&Type=json&pIndex=1&pSize=1&SCHUL_NM=%ED%95%9C%EA%B5%AD', timeout=2).read()"

CMD ["uvicorn", "mock_neis.app:app", "--host", "0.0.0.0", "--port", "8081"]
