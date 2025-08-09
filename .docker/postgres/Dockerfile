FROM postgres:17.5

COPY .docker/postgres/pg_hba.conf /etc/postgresql/pg_hba.conf

USER postgres

CMD ["postgres", "-c", "hba_file=/etc/postgresql/pg_hba.conf"]
