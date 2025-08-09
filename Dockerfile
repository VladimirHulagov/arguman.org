FROM python:3.13
ARG UID=1000
ARG GID=$UID
ARG USER=arguman
ARG GROUP=$USER
ENV PYTHONUNBUFFERED 1
WORKDIR /code
# Setup user & group
RUN groupadd --gid $GID $GROUP && \
    useradd --uid $UID --gid $GID -m $USER && \
    chown -R ${UID}:${GID} /code/
COPY --chown=$UID:$GID --chmod=555 requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt
COPY --chown=$UID:$GID --chmod=555 ./web/ ./web/
USER ${USER}
RUN python -m textblob.download_corpora
EXPOSE 8000
CMD python web/manage.py migrate --noinput ; python web/manage.py runserver 0.0.0.0:8000
