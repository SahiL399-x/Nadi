from fastapi import APIRouter, Depends, HTTPException
from livekit import api
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.video import VideoTokenIn, VideoTokenOut
from app.services import consultation_service

router = APIRouter(prefix="/v1/video", tags=["video"])


@router.post("/token", response_model=VideoTokenOut)
def create_token(
    body: VideoTokenIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoTokenOut:
    # Only a participant (the patient or the assigned doctor) of this consultation
    # may mint a join token — otherwise any authenticated user who learned a
    # consultationId could join a private medical call (PHI breach). 404 (not 403)
    # so we don't confirm the consultation exists to a non-participant.
    if not consultation_service.is_participant(db, body.consultationId, user):
        raise HTTPException(status_code=404, detail="not found")
    # Mint a LiveKit join token for this consultation's room. Both the patient and
    # the doctor request a token for the same room (nadi-{consultationId}) and meet.
    room = f"nadi-{body.consultationId}"
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(str(user.id))
        .with_name(user.name)
        .with_grants(api.VideoGrants(room_join=True, room=room))
        .to_jwt()
    )
    return VideoTokenOut(url=settings.livekit_url, token=token, room=room)
