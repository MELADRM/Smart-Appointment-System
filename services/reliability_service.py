"""Customer reliability scoring."""

from models import Appointment

class ReliabilityService:
    # No-show counts + flagging threshold.

    FLAG_THRESHOLD = 3

    def __init__(self, db: dict):
        self._appts = [Appointment.from_dict(a) for a in db.get('appointments', [])]

    def count_for(self, user_id: str) -> int:
        return sum(1 for a in self._appts if a.user_id == user_id and a.status == 'no_show')

    def is_flagged(self, user_id: str) -> bool:
        return self.count_for(user_id) >= self.FLAG_THRESHOLD

    def no_show_map(self) -> dict:
        # {user_id: count} across every customer.
        out: dict = {}
        for a in self._appts:
            if a.status == 'no_show':
                out[a.user_id] = out.get(a.user_id, 0) + 1
        return out

    def flagged_user_ids(self) -> set:
        return {uid for uid, n in self.no_show_map().items() if n >= self.FLAG_THRESHOLD}
