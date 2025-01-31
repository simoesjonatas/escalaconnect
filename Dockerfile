FROM python:3.13
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
COPY requirements.txt /code/
WORKDIR /code
RUN pip -V
RUN python --version
RUN pip install -r requirements.txt
COPY . /code/
