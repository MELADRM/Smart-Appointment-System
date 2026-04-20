"""Appointment entity and status state machine."""

from abc import ABC, abstractmethod
from datetime import datetime
from .base import BaseModel

class AppointmentStatus(ABC):
    # Abstract base; concrete subclasses are the allowed status values.
    name: str = ''

    @abstractmethod
    def allowed_transitions(self) -> set:
        ...

    def can_review(self) -> bool:
        return False

    def can_reschedule(self) -> bool:
        return False

    def can_cancel(self) -> bool:
        return False

    def is_active(self) -> bool:
        return False

    def is_paid(self) -> bool:
        return False

    @staticmethod
    def from_name(name: str) -> 'AppointmentStatus':
        return _STATUS_REGISTRY.get(name, BookedStatus())

class BookedStatus(AppointmentStatus):
    name = 'booked'

    def allowed_transitions(self):
        return {'completed', 'cancelled', 'no_show'}

    def can_reschedule(self):
        return True

    def can_cancel(self):
        return True

    def is_active(self):
        return True

class CompletedStatus(AppointmentStatus):
    name = 'completed'

    def allowed_transitions(self):
        return set()

    def can_review(self):
        return True

    def is_paid(self):
        return True

class CancelledStatus(AppointmentStatus):
    name = 'cancelled'

    def allowed_transitions(self):
        return set()

class NoShowStatus(AppointmentStatus):
    name = 'no_show'

    def allowed_transitions(self):
        return set()

_STATUS_REGISTRY = {
    s.name: s for s in (BookedStatus(), CompletedStatus(), CancelledStatus(), NoShowStatus())
}

class Appointment(BaseModel):
    # A single booking; the status object governs what's allowed next.

    def __init__(
        self,
        id: str,
        user_id: str,
        biz_id: str,
        service_id: str = '',
        date: str = '',
        time: str = '',
        duration_min: int = 30,
        notes: str = '',
        reason: str = '',
        status: str = 'booked',
        admin_override: bool = False,
        created_at: str = '',
        updated_at: str = None,
        cancelled_at: str = None,
        rescheduled_at: str = None,
    ):
        self.id = id
        self.user_id = user_id
        self.biz_id = biz_id
        self.service_id = service_id or ''
        self.date = date
        self.time = time
        self.duration_min = int(duration_min or 30)
        self.notes = notes or ''
        self.reason = reason or ''
        self.status = status
        self.admin_override = bool(admin_override)
        self.created_at = created_at or self.now_iso()
        self.updated_at = updated_at
        self.cancelled_at = cancelled_at
        self.rescheduled_at = rescheduled_at

    def validate(self) -> None:
        if self.status not in _STATUS_REGISTRY:
            raise ValueError(f'Unknown status: {self.status!r}')
        if not self.date or not self.time:
            raise ValueError('Date and time are required.')

    @property
    def status_obj(self) -> AppointmentStatus:
        return AppointmentStatus.from_name(self.status)

    def is_active(self) -> bool:
        return self.status_obj.is_active()

    def is_paid(self) -> bool:
        return self.status_obj.is_paid()

    def can_cancel(self) -> bool:
        return self.status_obj.can_cancel()

    def can_review(self) -> bool:
        return self.status_obj.can_review()

    def can_reschedule(self) -> bool:
        return self.status_obj.can_reschedule()

    def when(self):
        # datetime built from self.date + self.time, or None on parse failure.
        try:
            return datetime.strptime(f'{self.date} {self.time}', '%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            return None

    def is_in_past(self) -> bool:
        w = self.when()
        return bool(w and w < datetime.now())

    def _transition_to(self, new_status: str) -> None:
        if new_status not in self.status_obj.allowed_transitions():
            raise ValueError(f'Cannot move from {self.status!r} to {new_status!r}.')
        self.status = new_status
        self.updated_at = self.now_iso()

    def mark_completed(self) -> None:
        self._transition_to('completed')

    def mark_no_show(self) -> None:
        self._transition_to('no_show')

    def cancel(self, reason: str = '') -> None:
        self._transition_to('cancelled')
        self.cancelled_at = self.now_iso()
        if reason:
            self.reason = reason
