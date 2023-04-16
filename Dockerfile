FROM python:3.10-slim
ENV PYTHONUNBUFFERED 1
COPY requirements.txt /
RUN pip3 install -r /requirements.txt
RUN pip3 install gunicorn
COPY main.py /app/
COPY templates /app/templates
COPY static /app/static
WORKDIR /app
CMD ["gunicorn"  , "--threads", "8","-b", "0.0.0.0:8080", "main:app"]
