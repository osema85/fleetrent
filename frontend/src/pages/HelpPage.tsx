import { useAuth } from '../auth/AuthContext';
import { PageHeader } from '../components/ui';

export default function HelpPage() {
  const { isStaff, hasRole } = useAuth();
  return (
    <>
      <PageHeader title="Help" />
      {isStaff ? (
        <>
          <section className="card">
            <h2>Daily workflow</h2>
            <ol className="steps">
              <li><strong>Morning:</strong> open the Dashboard. Check <em>Pickups today</em>, <em>Returns today</em>, <em>Overdue</em> and <em>Pending approval</em>.</li>
              <li><strong>Approve online bookings:</strong> Reservations → filter <em>Pending</em> → open → <em>Confirm reservation</em> (or cancel with a reason).</li>
              <li><strong>Walk-in / phone booking:</strong> Reservations → <em>New reservation</em>: pick dates, search, choose a car, options and the customer. Staff bookings are confirmed immediately.</li>
              <li><strong>Pickup (check-out):</strong> open the reservation, check the driver license and ID, record the <em>deposit</em> payment, then fill in odometer, fuel and condition notes and confirm check-out.</li>
              <li><strong>Return (check-in):</strong> open the reservation (or Rentals → On the road), enter odometer, fuel, return time and any damage. The final bill is calculated automatically.</li>
              <li><strong>Settle:</strong> record the remaining <em>payment</em>, return the deposit (<em>Deposit returned</em>), then print the invoice.</li>
            </ol>
          </section>
          <section className="card">
            <h2>Pricing rules</h2>
            <ul>
              <li>Every started 24-hour period is charged as one day.</li>
              <li>Extras per day: basic insurance 12, full insurance 25 (halves the deposit), GPS 5, child seat 4, additional driver 8.</li>
              <li>300 km per day included; extra kilometres are charged.</li>
              <li>Returns more than 60 minutes late are charged per started day at 125%.</li>
              <li>Missing fuel/charge is charged per percent below the pickup level.</li>
            </ul>
          </section>
          {hasRole('admin', 'manager') && (
            <section className="card">
              <h2>Managers</h2>
              <ul>
                <li><strong>Fleet:</strong> add cars, change rates, retire vehicles (cars with history cannot be deleted).</li>
                <li><strong>Maintenance:</strong> schedule → <em>Start</em> (car becomes unavailable) → <em>Complete</em> (car is available again).</li>
                <li><strong>Blacklist:</strong> on a customer page; blacklisted customers cannot book.</li>
              </ul>
            </section>
          )}
          {hasRole('admin') && (
            <section className="card">
              <h2>Administrators</h2>
              <ul>
                <li><strong>Users:</strong> create staff accounts with the least role they need (agent &lt; manager &lt; admin).</li>
                <li>Accounts lock for 15 minutes after 5 wrong passwords; use <em>Unlock</em> if needed.</li>
                <li><strong>Audit log:</strong> review failed logins, token-reuse alerts and all money movements regularly.</li>
              </ul>
            </section>
          )}
        </>
      ) : (
        <section className="card">
          <h2>How to rent a car</h2>
          <ol className="steps">
            <li>Go to <strong>Book a car</strong>, choose pickup/return dates and search.</li>
            <li>Select a car and options; the price is shown instantly.</li>
            <li>Click <strong>Request booking</strong>. Our team confirms it shortly — see <strong>My reservations</strong>.</li>
            <li>At pickup bring your driver license and ID. A refundable deposit is taken.</li>
            <li>Return the car on time with the same fuel level to avoid extra fees.</li>
            <li>You can cancel a reservation online until the pickup time.</li>
          </ol>
        </section>
      )}
    </>
  );
}
