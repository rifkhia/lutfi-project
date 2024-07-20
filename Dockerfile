FROM ubuntu:20.04

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y python3 python3-pip

RUN pip install fastapi uvicorn

ENTRYPOINT ["uvicorn", "main:app", "--reload"]
