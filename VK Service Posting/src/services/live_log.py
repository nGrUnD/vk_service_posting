import re

from sqlalchemy.orm import Session

from src.models.live_log import LiveLogOrm
from src.schemas.live_log import LiveLogAdd


def _normalize_logtype(logtype: str) -> str:
    value = (logtype or "manual").strip().lower()
    return value[:50] or "manual"


def _normalize_log(log: str) -> str:
    value = (log or "").strip()
    return value[:500] or "Событие без текста"


def sanitize_logdescription(value: str | None, max_length: int = 2000) -> str | None:
    if value is None:
        return None

    text = str(value)
    text = re.sub(r"(access_token=)[^&\\s'\";]+", r"\1***", text, flags=re.IGNORECASE)
    text = re.sub(r"(token[=:]\\s*)[^\\s;,'\"]+", r"\1***", text, flags=re.IGNORECASE)
    text = re.sub(r"(password[=:]\\s*)[^\\s;,'\"]+", r"\1***", text, flags=re.IGNORECASE)
    text = re.sub(r"(cookie[s]?[=:]\\s*)[^\\n]+", r"\1***", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?P<scheme>https?://)?(?P<login>[^:@/\\s]+):(?P<password>[^@/\\s]+)@",
        lambda match: f"{match.group('scheme') or ''}***:***@",
        text,
    )
    return text[:max_length]


async def livelogadd(
        database,
        user_id: int,
        logtype: str,
        log: str,
        logdescription: str | None = None,
):
    event = await database.live_log.add(
        LiveLogAdd(
            user_id=user_id,
            logtype=_normalize_logtype(logtype),
            log=_normalize_log(log),
            logdescription=sanitize_logdescription(logdescription),
        )
    )
    await database.commit()
    return event


def livelogadd_sync(
        session: Session,
        user_id: int,
        logtype: str,
        log: str,
        logdescription: str | None = None,
) -> LiveLogOrm:
    event = LiveLogOrm(
        user_id=user_id,
        logtype=_normalize_logtype(logtype),
        log=_normalize_log(log),
        logdescription=sanitize_logdescription(logdescription),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
