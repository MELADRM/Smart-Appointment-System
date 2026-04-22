"""Business dashboard analytics."""

from datetime import datetime, timedelta
from models import Appointment, Service

class AnalyticsService:
    # 30-day trend + top services + repeat-customer rate for the dashboard.

    WINDOW_DAYS = 30
    TOP_N = 5

    def __init__(self, db: dict, business):
        # Accepts either a Business model or the legacy dict shape.
        self._db = db
        self._biz_id = business.id if hasattr(business, 'id') else business['id']
        self._today = datetime.today().date()

        self._appts = [
            Appointment.from_dict(a)
            for a in db.get('appointments', [])
            if a.get('biz_id') == self._biz_id
        ]
        self._services = [
            Service.from_dict(s)
            for s in db.get('services', [])
            if s.get('business_id') == self._biz_id
        ]

    def build(self) -> dict:
        trend = self._daily_trend()
        top = self._top_services()
        repeat_customers, total_customers = self._repeat_customer_counts()
        repeat_rate = repeat_customers * 100 // total_customers if total_customers else 0
        return {
            'trend_labels': trend['labels'],
            'trend_values': trend['values'],
            'trend_max': max(trend['values']) if trend['values'] else 0,
            'trend_total': sum(trend['values']),
            'top_services': top,
            'top_max': top[0][1] if top else 0,
            'total_revenue': sum(rev for _, rev, _ in top),
            'repeat_rate': repeat_rate,
            'repeat_customers': repeat_customers,
            'total_customers': total_customers,
        }

    def _daily_trend(self) -> dict:
        # Booking counts per day for the last WINDOW_DAYS, oldest -> newest.
        labels = [
            (self._today - timedelta(days=self.WINDOW_DAYS - 1 - i)).strftime('%b %d')
            for i in range(self.WINDOW_DAYS)
        ]
        values = [0] * self.WINDOW_DAYS
        for appt in self._appts:

            if appt.status == 'cancelled':
                continue
            when = appt.when()
            if not when:
                continue
            delta = (self._today - when.date()).days
            if 0 <= delta < self.WINDOW_DAYS:
                values[self.WINDOW_DAYS - 1 - delta] += 1
        return {'labels': labels, 'values': values}

    def _top_services(self) -> list:
        # Top N by revenue, as [(name, revenue, count), ...].
        svc_by_id = {s.id: s for s in self._services}
        revenue: dict = {}
        counts: dict = {}
        for appt in self._appts:
            if not appt.is_paid():
                continue
            svc = svc_by_id.get(appt.service_id)
            if not svc:
                continue
            revenue[svc.name] = revenue.get(svc.name, 0.0) + svc.price
            counts[svc.name] = counts.get(svc.name, 0) + 1
        ranked = sorted(
            ((name, revenue[name], counts[name]) for name in revenue),
            key=lambda t: t[1],
            reverse=True,
        )
        return ranked[: self.TOP_N]

    def _repeat_customer_counts(self) -> tuple:
        # Returns (repeat_customers, total_customers) based on completed appts.
        per_customer: dict = {}
        for appt in self._appts:
            if not appt.is_paid():
                continue
            per_customer[appt.user_id] = per_customer.get(appt.user_id, 0) + 1
        total = len(per_customer)
        repeat = sum(1 for n in per_customer.values() if n >= 2)
        return repeat, total
