"""Owner-reply workflow."""

from models import Review, ReviewReplyNotification

class ReviewReplyService:
    # Post / update / remove an owner's reply to a review.

    def __init__(self, db: dict):
        self._db = db

    def find_for_business(self, review_id: str, biz_id: str):
        # Scoped to one business so owners can't reply to others' reviews.
        for raw in self._db.get('reviews', []):
            if raw.get('id') == review_id and raw.get('biz_id') == biz_id:
                return raw
        return None

    def set_reply(self, review_row: dict, business_name: str, customer_id: str, text: str) -> str:
        # Returns 'posted', 'updated', or 'removed' so the route can flash the right message.
        review = Review.from_dict(review_row)
        had_reply_before = review.has_reply()
        is_new_reply = review.set_reply(text)

        review_row['owner_reply'] = review.owner_reply
        review_row['owner_reply_at'] = review.owner_reply_at

        if is_new_reply:
            notif = ReviewReplyNotification.create(
                user_id=customer_id,
                business_name=business_name,
            )
            self._db.setdefault('notifications', []).append(notif.to_dict())
            return 'posted'
        if review.has_reply() and had_reply_before:
            return 'updated'
        return 'removed'
