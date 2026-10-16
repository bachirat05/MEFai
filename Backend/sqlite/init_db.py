from Backend.sqlite.database import Base, engine

# Ces imports garantissent que les modèles sont enregistrés
# dans les métadonnées SQLAlchemy.
from Backend.sqlite.activity_models import ActivityLogModel
from Backend.sqlite.chat_models import (
    ChatMessageModel,
    ConversationModel,
)
from Backend.sqlite.leave_models import LeaveRequestModel

from services.audit.activity_log_service import (
    ensure_activity_log_indexes,
)


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_activity_log_indexes(engine)