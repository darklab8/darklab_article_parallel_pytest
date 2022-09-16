FROM python:3.10

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /install

WORKDIR /code

COPY ./requirements.txt ./constraints.txt ./
RUN pip install -r requirements.txt -c constraints.txt

COPY make make
COPY src src