FROM python:3.11-slim

# install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# set working directory
WORKDIR /app

# copy all files
COPY . .

# install python packages
RUN pip install --no-cache-dir -r requirements.txt

# run bot
CMD ["python", "super_bot_free_final.py"]