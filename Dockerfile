FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get -y update
RUN apt-get install -y sqlite3 libsqlite3-dev

CMD ["python", "ictapi.py"]