# 3D Label Generator - Docker Configuration
FROM python:3.11-slim

# OCI Labels for container metadata
LABEL org.opencontainers.image.source="https://github.com/qwertz098/3d_label_generator"
LABEL org.opencontainers.image.description="Web-based 3D label generator with CadQuery and Three.js"
LABEL org.opencontainers.image.licenses="MIT"

# Install system dependencies for CadQuery and font rendering
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglu1-mesa \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY download_fonts.py .
COPY templates/ templates/

# Create directories
RUN mkdir -p fonts exports

# Download fonts during build
RUN python download_fonts.py || echo "Font download failed, will use fallback fonts"

# Optional: Register fonts with fontconfig for system-wide discovery
# This is a backup - our app registers fonts directly with OpenCASCADE
RUN mkdir -p /usr/local/share/fonts/custom && \
    cp fonts/*.ttf /usr/local/share/fonts/custom/ 2>/dev/null || true && \
    fc-cache -fv 2>/dev/null || true

# Expose port
EXPOSE 5000

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

# Run application
CMD ["python", "app.py"]
