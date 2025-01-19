# Use the official Ubuntu 22.04 stable image from Amazon ECR Public Gallery
FROM public.ecr.aws/ubuntu/ubuntu:22.04_stable

# Set the frontend to noninteractive to avoid prompts during package installation
ARG DEBIAN_FRONTEND=noninteractive

# Update the package list
RUN apt-get update

# Install Python 3 and pip
RUN apt-get install -y python3 python3-pip

# Set the working directory to /app
WORKDIR /app

# Create necessary directories for dataset storage
RUN mkdir -p /mnt/efs/data/dataset/existing
RUN mkdir -p /mnt/efs/data/dataset/external

# Update the package list and install OpenCV for Python
RUN apt-get update && apt-get install -y python3-opencv

# Copy all files from the current directory to the container's working directory
COPY . .

# Install Python dependencies from requirements.txt
RUN pip install -r requirements.txt

# Expose port 8501 for the Streamlit app
EXPOSE 8501

# Define a health check to ensure the app is running
HEALTHCHECK CMD curl --fail http://0.0.0.0:8501/_stcore/health

# Set the entry point to run the Streamlit app with specified options
ENTRYPOINT ["streamlit", "run", \
    "--server.port=8501", \
    "--browser.gatherUsageStats=false", \
    "--server.enableCORS=false", \
    "--server.enableWebsocketCompression=false", \
    "--server.enableXsrfProtection=false", \
    "--server.headless=true", \
    "app.py"]