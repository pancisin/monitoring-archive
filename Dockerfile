FROM python:3.13.6-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y build-essential libpq-dev
RUN pip install -r requirements.txt

EXPOSE 5000
#flask run --host=0.0.0.0 --port=5000
CMD ["python", "-m", "src.app"]