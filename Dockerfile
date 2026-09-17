# create-teaching-content -- schlanker Build-/Web-Container.
# Typst + Pandoc + gebuendelte Fonts + Python-Web-Schicht. Bewusst OHNE
# Docling (das waere ein GB-schweres ML-Image -> separater ingest-Service).
# Pandoc ist dagegen ein schlankes natives Binary -> gehoert hier rein
# (export.py: editorial.json -> DOCX/EPUB/ODT). Die Docker-CLI ist ebenfalls
# drin (nur der Client, keine Compose-Plugin), damit der Webserver ingest.py
# als Sibling-Container ueber den gemounteten Host-Docker-Socket starten
# kann (Docker-outside-of-Docker, siehe docker-compose.yml).
FROM python:3.12-slim

ARG TYPST_VERSION=0.15.0
ARG DOCKER_CLI_VERSION=27.3.1

# Typst-CLI + Docker-CLI + Pandoc + DejaVu als Symbol-/Fallback-Font (fuer ✓ / ⚠ etc.)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl xz-utils ca-certificates fonts-dejavu-core pandoc \
 && curl -fsSL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" -o /tmp/typst.tar.xz \
 && tar -xf /tmp/typst.tar.xz -C /tmp \
 && mv /tmp/typst-x86_64-unknown-linux-musl/typst /usr/local/bin/typst \
 && rm -rf /tmp/typst* \
 && curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_CLI_VERSION}.tgz" -o /tmp/docker-cli.tgz \
 && tar -xf /tmp/docker-cli.tgz -C /tmp \
 && mv /tmp/docker/docker /usr/local/bin/docker \
 && rm -rf /tmp/docker* \
 && apt-get purge -y curl xz-utils \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Web-Schicht als Standard. Fuer reine CLI-Nutzung:
#   docker run --rm -v ./units:/app/units create-teaching-content \
#     python build.py units/<unit>
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
