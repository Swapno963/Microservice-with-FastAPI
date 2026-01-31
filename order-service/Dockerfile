FROM python:3.10-slim

# set envrionment variables
# prevents Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1 
# ensures that Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1
# set working directory 
ENV PYTHONPATY=/app 



# Install system dependencies
# will only install strict dependencies, skipping the optional “recommended” packages.
RUN apt-get update && apt-get install -y  --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*



# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt



# Copy .env
COPY .env .
COPY /app /app

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

