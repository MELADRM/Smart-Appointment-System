"""Notification types."""

from .base import BaseModel

class Notification(BaseModel):
    # Plain pre-formatted message in the user's notification list.

    KIND_DEFAULT = 'info'

    def __init__(
        self,
        id: str,
        user_id: str,
        message: str,
        kind: str = 'info',
        read: bool = False,
        created_at: str = '',
    ):
        self.id = id
        self.user_id = user_id
        self.message = message
        self.kind = kind
        self.read = bool(read)
        self.created_at = created_at or self.now_iso()

    def format(self) -> str:
        return self.message

    def validate(self) -> None:
        if not self.user_id:
            raise ValueError('Notification needs a user_id.')

    @classmethod
    def _make(cls, user_id: str, message: str, kind: str):
        return cls(
            id=cls.new_id('notif'),
            user_id=user_id,
            message=message,
            kind=kind,
            read=False,
            created_at=cls.now_iso(),
        )

class ReviewReplyNotification(Notification):
    # Sent to a customer the first time the business owner replies.

    @classmethod
    def create(cls, user_id: str, business_name: str) -> 'ReviewReplyNotification':
        msg = f'The owner of <strong>{business_name}</strong> ' f'replied to your review.'
        return cls._make(user_id, msg, kind='info')
