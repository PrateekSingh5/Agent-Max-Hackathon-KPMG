import database as _database
import models as _models
import schema as _schema
from typing  import TYPE_CHECKING


if TYPE_CHECKING:
    from sqlalchemy.orm import Session



def _add_tables():
    return _database.Base.metadata.create_all(
                        bind=_database.engine,
                        # tables = [_models.Employee.__table__, _models.PerDiemRate.__table__, _models.ExpensePolicy.__table__],
                        #   tables = [_models.ExpensePolicy.__table__],
                        tables = [_models.ReimbursementAccount.__table__, _models.Vendor.__table__, _models.ExpenseClaim.__table__],
                        )

def get_db():
    db = _database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def createExpenseClaims(
                expense_claims:_schema.createExpenseClaims,
                db: "Session") -> _schema.ExpenseClaims:
    contact = _models.ExpenseClaim(**expense_claims.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _schema.ExpenseClaims.from_orm(contact)

