from __future__ import annotations
import datetime as _dt
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Numeric, Integer, Text, Index, UniqueConstraint, TIMESTAMP, text, Column, Boolean, Date ,ForeignKey
import database as _database 
from datetime import date



class Employee(_database.Base):
    __tablename__ = "employees"

    # Columns taken EXACTLY from the sheet
    employee_id: Mapped[str]    = mapped_column(String(32), primary_key=True)  # e.g., "E1000"
    first_name:  Mapped[str]    = mapped_column(String(100), nullable=False)
    last_name:   Mapped[str]    = mapped_column(String(100), nullable=False)
    email:       Mapped[str]    = mapped_column(String(320), nullable=False, unique=True)
    department:  Mapped[str]    = mapped_column(String(120), nullable=False)
    cost_center: Mapped[str]    = mapped_column(String(50),  nullable=False)   # e.g., "CC102"
    grade:       Mapped[str]    = mapped_column(String(20),  nullable=False)   # e.g., "G1"
    hire_date:   Mapped[date]   = mapped_column(Date,       nullable=False)
    is_active:   Mapped[bool]   = mapped_column(Boolean,    nullable=False, default=True)
    corporate_card: Mapped[bool]= mapped_column(Boolean,    nullable=False, default=False)
    manager_id:  Mapped[str]    = mapped_column(String(32), nullable=False)    # e.g., "E1106"

    __table_args__ = (
        Index("ix_employees_department", "department"),
        Index("ix_employees_cost_center", "cost_center"),
        Index("ix_employees_manager_id", "manager_id"),
        Index("ix_employees_is_active", "is_active"),
    )


class PerDiemRate(_database.Base):
    __tablename__ = "per_diem_rates"

    # Auto PK for safety; your 3 requested columns follow
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)

    # --- REQUIRED COLUMNS (exactly these three) ---
    location = Column(Text, nullable=False)
    currency = Column(String(10), nullable=False)
    per_diem_rate = Column(Numeric(10, 2), nullable=False)

    # Optional audit column (doesn’t change your three columns)
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )

    __table_args__ = (
        # prevent duplicate rows for same (location, currency)
        UniqueConstraint("location", "currency", name="uq_per_diem_location_currency"),
        Index("idx_per_diem_location", "location"),
        Index("idx_per_diem_currency", "currency"),
    )



class ExpensePolicy(_database.Base):
    __tablename__ = "expense_policies"

    # Columns from Excel
    id               = Column(Integer, primary_key=True, autoincrement=True)
    policy_id        = Column(String(20), nullable=False)
    category         = Column(String(100), nullable=False)
    max_allowance    = Column(Numeric(10, 2), nullable=False)
    per_diem         = Column(Numeric(10, 2), nullable=False)
    applicable_grades = Column(String(100), nullable=False)
    notes            = Column(Text)

    __table_args__ = (
        Index("ix_policy_id", "policy_id"),
        Index("ix_category", "category"),
    )



class ReimbursementAccount(_database.Base):
    __tablename__ = "reimbursement_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    bank_account_id = Column(String(20), nullable=False, unique=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False)
    bank_name = Column(String(100), nullable=False)
    account_number_masked = Column(String(30), nullable=False)
    ifsc = Column(String(15), nullable=False)

    __table_args__ = (
        Index("ix_reimb_employee_id", "employee_id"),
        Index("ix_reimb_bank_name", "bank_name"),
        Index("ix_reimb_ifsc", "ifsc"),
    )



class Vendor(_database.Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)

    vendor_id = Column(String(20), unique=True, nullable=False)
    vendor_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    contract_rate_reference = Column(Numeric(10, 2), nullable=True)
    vendor_verified = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_vendor_name", "vendor_name"),
        Index("ix_vendor_category", "category"),
        Index("ix_vendor_country", "country"),
        Index("ix_vendor_verified", "vendor_verified"),
    )


class ExpenseClaim(_database.Base):
    __tablename__ = "expense_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)

    claim_id = Column(String(30), nullable=False, unique=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False)
    claim_date = Column(Date, nullable=False)
    expense_category = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    vendor_id = Column(String(20), ForeignKey("vendors.vendor_id"))
    linked_booking_id = Column(String(50))
    receipt_id = Column(String(50))
    payment_mode = Column(String(30))
    status = Column(String(30))
    Details = Column(Text)
    Others_1 = Column(Text)
    Others_2 = Column(Text)
    auto_approved = Column(Boolean, default=False, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    fraud_flag = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_claim_employee", "employee_id"),
        Index("ix_claim_status", "status"),
        Index("ix_claim_date", "claim_date"),
        Index("ix_claim_vendor", "vendor_id"),
)