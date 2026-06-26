FROM python:3.11-slim

# Install system dependencies (Git is required by GitPython)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy all repository files to container
COPY . .

# Expose port 8501
EXPOSE 8501

# Command to run Streamlit on port 8501, binding to all interfaces and disabling XSRF for proxy support
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.enableXsrfProtection", "false"]
