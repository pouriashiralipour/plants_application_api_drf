FROM python:3.12.12-alpine3.22

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apk update && apk add --no-cache gettext postgresql-client libjpeg zlib curl build-base gcc musl-dev python3-dev && rm -rf /var/cache/apk/*

RUN addgroup -g 1001 app && adduser -u 1001 -S -G app app

WORKDIR /app

COPY requirements.txt .
RUN python -m venv $VIRTUAL_ENV && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R app:app /app

# USER app

EXPOSE 8000

# RUN python manage.py collectstatic --noinput

CMD ["sh", "-c", "python", "manage.py", "runserver", "0.0.0.0:8000"]

# CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
