import datetime as _dt
import pydantic as _pydantic


class _BaseExpenseClaims(_pydantic.BaseModel):
    employee_id: str
    claim_date: _dt.date
    expense_category: str
    amount: float
    vendor_id: str | None = None
    linked_booking_id: str | None = None
    receipt_id: str | None = None
    currency: str
    # expense_date: _dt.date
    # description: str
    # receipt_provided: bool


class ExpenseClaims(_BaseExpenseClaims):
    claim_id: str
    date_created: _dt.datetime

class createExpenseClaims(_BaseExpenseClaims):
    pass