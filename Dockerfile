FROM python:3.11-slim-bookworm

COPY . /local

WORKDIR /local

RUN pip install fastapi uvicorn 'fastapi[standard]'

CMD ["fastapi", "run", "app.py"]