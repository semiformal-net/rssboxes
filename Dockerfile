# Note that this dockerfile is only used for development. deploying to GCP uses another container (per app.yaml)

FROM python:3.10-slim 
ENV PYTHONUNBUFFERED 1 
COPY requirements.txt / 
RUN pip3 install --no-cache-dir -r /requirements.txt 
# requirements.txt does not include gunicorn, per google app engine instructions. for debugging this image will need it
RUN pip3 install --no-cache-dir gunicorn 
COPY main.py /app/ 
COPY rss_config.py /app/ 
COPY templates /app/templates 
COPY static /app/static 
WORKDIR /app 
CMD ["gunicorn", "--threads", "8","-b", "0.0.0.0:8080", "main:app"]
