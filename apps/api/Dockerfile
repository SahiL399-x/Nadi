FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
COPY seed ./seed
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
