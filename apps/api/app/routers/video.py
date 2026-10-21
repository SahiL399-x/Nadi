from fastapi import APIRouter, Depends
from livekit import api

from app.core.config import settings
from app.core.deps import get_current_user
from app.models import User
from app.schemas.video import VideoTokenIn, VideoTokenOut

router = APIRouter(prefix="/v1/video", tags=["video"])


@router.post("/token", response_model=VideoTokenOut)
def create_token(body: VideoTokenIn, user: User = Depends(get_current_user)) -> VideoTokenOut:
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
