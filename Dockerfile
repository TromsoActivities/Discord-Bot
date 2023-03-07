FROM python:3.10-alpine
LABEL org.opencontainers.image.authors="ultraxime@yahoo.fr"

RUN apk update

RUN pip install --upgrade pip && pip install discord zmq pyyaml

ENTRYPOINT ["python3", "-u", "/usr/local/bin/main.py"]
CMD ["start"]

EXPOSE 25564

HEALTHCHECK --interval=20s --timeout=2s --start-period=600s --retries=3 \
    CMD python3 -u /usr/local/bin/main.py healthcheck

COPY . /usr/local/bin
