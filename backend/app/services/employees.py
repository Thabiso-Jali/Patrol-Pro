from sqlalchemy.orm import Session

from .. import models


def employee_for_user(db: Session, *, organisation_id: int, user_id: int) -> models.Employee | None:
    return db.query(models.Employee).filter(
        models.Employee.organisation_id == organisation_id,
        models.Employee.user_id == user_id,
        models.Employee.is_deleted.is_(False),
    ).first()
