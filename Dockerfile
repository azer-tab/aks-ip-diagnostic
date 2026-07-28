FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY pyproject.toml README.md ./
COPY src ./src

ARG APP_VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AKS_IP_DIAGNOSTIC=${APP_VERSION}

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

USER appuser

ENTRYPOINT ["aks-ip-diagnostic"]
CMD ["--help"]