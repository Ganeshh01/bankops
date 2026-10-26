import os
import time
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "bankdb"),
        user=os.getenv("DB_USER", "bankapp"),
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    )


def init_db(retries: int = 10) -> None:
    """Create the schema, retrying while PostgreSQL starts."""
    for attempt in range(retries):
        try:
            with get_connection() as connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        owner_name VARCHAR(100) NOT NULL,
                        balance_cents BIGINT NOT NULL DEFAULT 0
                            CHECK (balance_cents >= 0),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)

                connection.execute("""
                    CREATE TABLE IF NOT EXISTS transfers (
                        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        reference UUID NOT NULL UNIQUE,
                        from_account_id BIGINT NOT NULL
                            REFERENCES accounts(id),
                        to_account_id BIGINT NOT NULL
                            REFERENCES accounts(id),
                        amount_cents BIGINT NOT NULL
                            CHECK (amount_cents > 0),
                        status VARCHAR(20) NOT NULL DEFAULT 'completed'
                            CHECK (status IN ('completed')),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        CHECK (from_account_id <> to_account_id)
                    )
                """)
            return
        except psycopg.OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(2)


@contextmanager
def connection_scope():
    """Provide a connection that commits on success and rolls back on error."""
    with get_connection() as connection:
        yield connection
