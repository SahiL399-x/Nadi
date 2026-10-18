import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def log(db: Session, actor_user_id, action: str, entity: str, entity_id: str) -> None:
    db.add(
        AuditLog(
            id=uuid.uuid4(), actor_user_id=actor_user_id,
            action=action, entity=entity, entity_id=entity_id,
        )
    )
    db.commit()
