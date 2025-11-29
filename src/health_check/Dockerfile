# Use a small, common Python base image
FROM python:3.11-slim

# Ensure we’re on linux/amd64 when building (you’ll specify platform in the build command)
# Set working directory
WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY app.py .

# The service listens on port 8080
EXPOSE 8080

# Run the app
CMD ["python", "app.py"]
