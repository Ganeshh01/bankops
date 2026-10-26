from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    owner_name: str = Field(min_length=1, max_length=100)
    opening_balance: float = Field(ge=0, le=100000000, allow_inf_nan=False)

    @field_validator("owner_name")
    @classmethod
    def validate_owner_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Owner name cannot be blank")
        return value

    @field_validator("opening_balance")
    @classmethod
    def validate_money_precision(cls, value: float) -> float:
        if round(value * 100) != value * 100:
            raise ValueError("Opening balance can have at most two decimal places")
        return value


class Account(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_name: str
    balance: float
    created_at: datetime


class TransferCreate(BaseModel):
    from_account_id: int = Field(gt=0)
    to_account_id: int = Field(gt=0)
    amount: float = Field(gt=0, le=1000000, allow_inf_nan=False)

    @field_validator("amount")
    @classmethod
    def validate_money_precision(cls, value: float) -> float:
        if round(value * 100) != value * 100:
            raise ValueError("Transfer amount can have at most two decimal places")
        return value


class Transfer(BaseModel):
    id: int
    reference: UUID
    from_account_id: int
    to_account_id: int
    amount: float
    status: str
    created_at: datetime
