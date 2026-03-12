FROM python:3.11-slim

# Cài các thư viện hệ thống cơ bản 
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements trước để cache layer pip
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source
COPY . /app

# Mặc định chạy server.py 
CMD ["python", "server.py"]