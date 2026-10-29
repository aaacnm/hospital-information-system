from sqlalchemy.orm import Session

from app.models import DrugStock, StockMovement, User


def record_movement(
    db: Session,
    stock: DrugStock,
    quantity_delta: int,
    kind: str,
    user: User | None,
    prescription_id: int | None = None,
) -> None:
    db.add(
        StockMovement(
            drug_id=stock.drug_id,
            stock=stock,
            prescription_id=prescription_id,
            quantity_delta=quantity_delta,
            balance_after=stock.quantity,
            kind=kind,
            created_by=user.id if user else None,
        )
    )
