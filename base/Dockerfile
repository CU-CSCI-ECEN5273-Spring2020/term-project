FROM python:3
WORKDIR /usr/src/app
RUN apt-get update
COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt
ENTRYPOINT ["/bin/sh", "-c", "exit 0"]