FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app/feature_implementer

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=src.app:create_app

# Create outputs directory with appropriate permissions
RUN mkdir -p outputs && chown -R appuser:appuser outputs

# Expose the port the app runs on
EXPOSE 5000

# Switch to non-root user
USER appuser

# Use gunicorn for production (more reliable than Flask's development server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "src.app:create_app()"]