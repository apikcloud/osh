FROM mcr.microsoft.com/devcontainers/python:3.7

# Install extra system deps if needed
# RUN apt-get update && apt-get install -y <package> && rm -rf /var/lib/apt/lists/*

# Copy your CLI into the container
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: install your CLI in editable mode
# COPY . .
# RUN pip install --no-cache-dir -e .

CMD [ "bash" ]
