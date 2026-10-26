#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE einstein_test;
    ALTER DATABASE einstein_test OWNER TO "$POSTGRES_USER";
EOSQL