FROM python:alpine

RUN apk update && \
    apk upgrade && \
    apk add git

ADD copy_commit.py /copy_commit.py

ENTRYPOINT ["python", "/copy_commit.py"]
