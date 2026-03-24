FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg for the video-to-audio extraction (moviepy)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Create a non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .
RUN chown -R user:user /app /home/user
USER user

# Hugging Face Spaces typically routes to port 7860
EXPOSE 7860

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "7860"]
