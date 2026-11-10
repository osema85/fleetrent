from decimal import Decimal

from app.models import Reservation
from app.models.enums import PaymentKind, RentalStatus
from app.schemas.booking import Balance


def balance_for(reservation: Reservation) -> Balance:
    paid = Decimal("0")
    deposit = Decimal("0")
    for p in reservation.payments:
        if p.kind == PaymentKind.payment:
            paid += p.amount
        elif p.kind == PaymentKind.refund:
            paid -= p.amount
        elif p.kind == PaymentKind.deposit:
            deposit += p.amount
        elif p.kind == PaymentKind.deposit_refund:
            deposit -= p.amount

    rental = reservation.rental
    is_final = rental is not None and rental.status == RentalStatus.closed and rental.total_amount is not None
    total_due = rental.total_amount if is_final else reservation.estimated_total
    return Balance(
        total_due=total_due,
        paid=paid,
        balance=total_due - paid,
        deposit_required=reservation.deposit_amount,
        deposit_held=deposit,
        is_final=is_final,
    )
