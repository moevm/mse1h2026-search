FROM manticoresearch/manticore:17.5.1

RUN apt-get update && apt-get install -y wget gnupg && \
    wget -q https://repo.manticoresearch.com/manticore-repo.noarch.deb && \
    dpkg -i manticore-repo.noarch.deb && \
    apt-get update && \
    apt-get install -y manticore-extra manticore-language-packs && \
    rm manticore-repo.noarch.deb && \
    rm -rf /var/lib/apt/lists/*
