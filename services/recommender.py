"""Content-based business recommendations for customers."""

from collections import Counter


class Recommender:
    # Suggest businesses to a customer based on their booking history.

    DEFAULT_LIMIT = 3
    NEUTRAL_RATING = 3.0

    def __init__(self, db: dict):
        self._db = db
        self._biz_by_id = {b['id']: b for b in db.get('businesses', [])}

    def for_user(self, user_id: str, limit: int = None) -> list:
        # Pick the top-N businesses this user has not booked yet,
        # in the categories they have used most often.
        if limit is None:
            limit = self.DEFAULT_LIMIT

        category_counts = Counter()
        booked_biz_ids = set()
        for ap in self._db.get('appointments', []):
            if ap.get('user_id') != user_id:
                continue
            biz = self._biz_by_id.get(ap.get('biz_id'))
            if not biz:
                continue
            booked_biz_ids.add(biz['id'])
            category_counts[biz.get('category', '')] += 1

        if not category_counts:
            return []

        candidates = [
            b for b in self._db.get('businesses', [])
            if b.get('status') == 'approved'
            and b['id'] not in booked_biz_ids
            and b.get('category') in category_counts
        ]

        avg_by_biz = self._average_ratings()

        def score(b):
            cat_pref = category_counts[b['category']]
            rating = avg_by_biz.get(b['id'], self.NEUTRAL_RATING)
            return cat_pref * rating

        candidates.sort(key=score, reverse=True)
        return candidates[:limit]

    def _average_ratings(self) -> dict:
        # Average star rating per business id.
        totals = {}
        counts = {}
        for r in self._db.get('reviews', []):
            bid = r.get('biz_id')
            if not bid:
                continue
            totals[bid] = totals.get(bid, 0) + int(r.get('rating', 0))
            counts[bid] = counts.get(bid, 0) + 1
        return {bid: totals[bid] / counts[bid] for bid in totals if counts[bid]}
