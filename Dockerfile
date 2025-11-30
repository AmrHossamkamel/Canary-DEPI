FROM python:3.11-slim

WORKDIR /app

# نسخ ملفات المشروع
COPY . .

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# كشف المنفذ الذي سيعمل عليه التطبيق
EXPOSE 8000

# أمر تشغيل التطبيق
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]