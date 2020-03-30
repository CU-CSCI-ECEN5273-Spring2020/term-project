FROM python:3
WORKDIR /usr/src/app
RUN apt-get update
RUN apt-get install -y git sqlite3 unzip
COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt
CMD [ "python3", "./scan_bot.py" ]
