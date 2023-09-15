# Use an official Python runtime as a parent image
FROM continuumio/miniconda3

# Set environment variables
ENV ML_API_PORT=5000

# Create a directory for your API code
WORKDIR /readable_e_paper

# Copy the current directory contents into the container at /app
COPY . /readable_e_paper

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

# Install any required Python packages and dependencies
RUN pip install -r requirements.txt

# Expose the port your API will run on
EXPOSE $ML_API_PORT

# Define the command to run your API
CMD ["python", "app.py"]
