from contextlib import asynccontextmanager
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

import psycopg
from fastapi import FastAPI, HTTPException, status

from app.database import get_connection, init_db
from app.models import AccountCreate, TransferCreate


def money_to_cents(amount: float) -> int:
    value = Decimal(str(amount)) * 100
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_money(cents: int) -> float:
    return cents / 100


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="BankOps Banking API",
    version="1.0.0",
    description="A simulated banking service for DevOps practice.",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def readiness():
    connection = None
    try:
        connection = get_connection()
        connection.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )
    finally:
        if connection is not None:
            connection.close()


@app.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate):
    connection = get_connection()
    try:
        row = connection.execute(
            """
            INSERT INTO accounts (owner_name, balance_cents)
            VALUES (%s, %s)
            RETURNING id, owner_name, balance_cents, created_at
            """,
            (payload.owner_name, money_to_cents(payload.opening_balance)),
        ).fetchone()

        return {
            "id": row["id"],
            "owner_name": row["owner_name"],
            "balance": cents_to_money(row["balance_cents"]),
            "created_at": row["created_at"],
        }
    except psycopg.Error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Database operation failed")
    finally:
        connection.close()


@app.get("/accounts/{account_id}")
def get_account(account_id: int):
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT id, owner_name, balance_cents, created_at
            FROM accounts WHERE id = %s
            """,
            (account_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Account not found")

        return {
            "id": row["id"],
            "owner_name": row["owner_name"],
            "balance": cents_to_money(row["balance_cents"]),
            "created_at": row["created_at"],
        }
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database operation failed")
    finally:
        connection.close()


@app.post("/transfers", status_code=status.HTTP_201_CREATED)
def create_transfer(payload: TransferCreate):
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(
            status_code=422,
            detail="Source and destination accounts must be different",
        )

    amount_cents = money_to_cents(payload.amount)
    reference = uuid4()

    connection = get_connection()
    try:
        # Lock both accounts in a consistent order to avoid transfer races.
        account_ids = sorted(
            [payload.from_account_id, payload.to_account_id]
        )
        rows = connection.execute(
            """
            SELECT id, balance_cents
            FROM accounts
            WHERE id = ANY(%s)
            ORDER BY id
            FOR UPDATE
            """,
            (account_ids,),
        ).fetchall()

        accounts = {row["id"]: row for row in rows}

        if payload.from_account_id not in accounts:
            raise HTTPException(status_code=404, detail="Source account not found")

        if payload.to_account_id not in accounts:
            raise HTTPException(
                status_code=404,
                detail="Destination account not found",
            )

        source = accounts[payload.from_account_id]
        if source["balance_cents"] < amount_cents:
            raise HTTPException(
                status_code=409,
                detail="Insufficient funds",
            )

        connection.execute(
            """
            UPDATE accounts
            SET balance_cents = balance_cents - %s
            WHERE id = %s
            """,
            (amount_cents, payload.from_account_id),
        )

        connection.execute(
            """
            UPDATE accounts
            SET balance_cents = balance_cents + %s
            WHERE id = %s
            """,
            (amount_cents, payload.to_account_id),
        )

        transfer = connection.execute(
            """
            INSERT INTO transfers
                (reference, from_account_id, to_account_id, amount_cents)
            VALUES (%s, %s, %s, %s)
            RETURNING id, reference, from_account_id, to_account_id,
                      amount_cents, status, created_at
            """,
            (
                reference,
                payload.from_account_id,
                payload.to_account_id,
                amount_cents,
            ),
        ).fetchone()

        # The connection context commits all three operations together.
        return {
            "id": transfer["id"],
            "reference": transfer["reference"],
            "from_account_id": transfer["from_account_id"],
            "to_account_id": transfer["to_account_id"],
            "amount": cents_to_money(transfer["amount_cents"]),
            "status": transfer["status"],
            "created_at": transfer["created_at"],
        }

    except HTTPException:
        connection.rollback()
        raise
    except psycopg.Error:
        connection.rollback()
        raise HTTPException(status_code=503, detail="Transfer failed")
    finally:
        connection.close()


@app.get("/transfers")
def list_transfers():
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, reference, from_account_id, to_account_id,
                   amount_cents, status, created_at
            FROM transfers
            ORDER BY id
            """
        ).fetchall()

        return [
            {
                "id": row["id"],
                "reference": row["reference"],
                "from_account_id": row["from_account_id"],
                "to_account_id": row["to_account_id"],
                "amount": cents_to_money(row["amount_cents"]),
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database operation failed")
    finally:
        connection.close()
