FROM python:3.12.15-slim-trixie

# Refresh the distribution CA store separately from Python package bundles.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Hash-verified bootstrap also replaces pip's separately vendored CA bundle.
RUN python -m pip install --no-cache-dir --upgrade \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# python3-saml は xmlsec のネイティブ依存を必要とする
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential pkg-config gcc \
       libxml2-dev libxmlsec1-dev libxmlsec1-openssl xmlsec1 \
    && rm -rf /var/lib/apt/lists/*

# ビルドコンテキストはリポジトリルート（shared/ を共有するため）
COPY backend/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY backend/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
