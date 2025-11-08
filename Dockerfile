FROM python:3.11-slim

# Install system dependencies for PipeWire, PulseAudio, and MPV
RUN apt-get update && apt-get install -y \
    pipewire \
    pulseaudio-utils \
    libmpv2 \
    libmpv-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package
RUN pip install -e .

# Create config directory
RUN mkdir -p /app/.config/pipeplay

# Expose the API port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "-m", "pipeplay", "--daemon"]