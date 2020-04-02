FROM local/term-project-base
WORKDIR /usr/src/app
COPY . .
EXPOSE 5000
CMD [ "gunicorn", "--bind", "0.0.0.0:5000", "controller:app" ]
