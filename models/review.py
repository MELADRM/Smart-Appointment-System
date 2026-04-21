"""Review entity."""

from .base import BaseModel

class Review(BaseModel):
    # A customer rating for a completed appointment.

    MIN_RATING = 1
    MAX_RATING = 5
    REPLY_LIMIT = 500

    def __init__(
        self,
        id: str,
        appt_id: str,
        biz_id: str,
        user_id: str,
        rating: int,
        comment: str = '',
        owner_reply: str = '',
        owner_reply_at: str = None,
        created_at: str = '',
    ):
        self.id = id
        self.appt_id = appt_id
        self.biz_id = biz_id
        self.user_id = user_id
        self.rating = int(rating)
        self.comment = comment or ''
        self.owner_reply = owner_reply or ''
        self.owner_reply_at = owner_reply_at
        self.created_at = created_at or self.now_iso()

    def validate(self) -> None:
        if not (self.MIN_RATING <= self.rating <= self.MAX_RATING):
            raise ValueError(f'Rating must be {self.MIN_RATING}–{self.MAX_RATING}.')

    def has_reply(self) -> bool:
        return bool(self.owner_reply)

    def star_row(self) -> str:
        return '★' * self.rating + '☆' * (self.MAX_RATING - self.rating)

    def set_reply(self, text: str) -> bool:
        # Returns True if this is the first reply (caller fires the notification).
        # Empty text clears any existing reply.
        cleaned = (text or '').strip()[: self.REPLY_LIMIT]
        was_new = not self.owner_reply and bool(cleaned)
        if cleaned:
            self.owner_reply = cleaned
            self.owner_reply_at = self.now_iso()
        else:
            self.owner_reply = ''
            self.owner_reply_at = None
        return was_new
