# FleetRent Tutorial

This guide walks you through FleetRent step by step: installing it, setting up your agency, and then running a complete rental from booking to invoice. It ends with a section for customers.

**Contents**
1. [Install and first login](#1-install-and-first-login)
2. [Set up your agency (admin)](#2-set-up-your-agency-admin)
3. [Roles: who can do what](#3-roles-who-can-do-what)
4. [A complete rental, step by step](#4-a-complete-rental-step-by-step)
5. [How the bill is calculated](#5-how-the-bill-is-calculated)
6. [Daily routine](#6-daily-routine)
7. [Fleet and maintenance (manager)](#7-fleet-and-maintenance-manager)
8. [Security tasks (admin)](#8-security-tasks-admin)
9. [For customers: booking online](#9-for-customers-booking-online)

---

## 1. Install and first login

You need Docker, and a terminal open in the project folder.

```bash
./scripts/generate-env.sh you@your-agency.com
docker compose up -d --build
```

1. The first command creates the private `.env` file and **prints the admin password once**. Save it in a password manager.
2. Wait until `docker compose ps` shows all three services as `healthy`. The first build takes a few minutes.
3. Open **https://localhost:8443**. The browser warns you about the certificate because it's self-signed. Choose *Advanced → Continue*.
4. Log in with the admin email and password.
5. Go to **My profile → Change password** right away. You'll be signed out, then sign in again with the new password.

> If demo data is enabled (`SEED_DEMO_DATA=true`), you already have 2 branches, 9 cars and 2 customers to practise with.

---

## 2. Set up your agency (admin)

Do these steps in this order. Each step needs the one before it.

### 2.1 Branches
**Branches → Add branch.** Enter a name, address, city, phone and email. Every car belongs to a branch, and customers choose pickup and return branches when they book.
To close a branch temporarily, click *Edit* and untick *Branch is open*. Customers will no longer see it.

### 2.2 Staff accounts
**Users → Add user.** Give each person their own account. Never share accounts, because the audit log records who did what.

| Give this role… | …to |
|---|---|
| **agent** | counter staff: customers, bookings, pickups, returns, payments |
| **manager** | agents' rights **plus** fleet, prices, maintenance and the blacklist |
| **admin** | managers' rights **plus** users, branches and the audit log |

Set an initial password, which must have 12+ characters with upper and lower case, a digit and a symbol. Share it through a secure channel and ask the person to change it under *My profile*.

### 2.3 Fleet
**Fleet → Add car** (manager or admin). Required fields: make, model, year, plate number, VIN (17 characters), color, category, transmission, fuel, seats, mileage, daily rate and branch.

The category also sets the security deposit:

| Category | Deposit |
|---|---|
| economy | 200 |
| compact | 250 |
| midsize | 300 |
| SUV / van | 400 |
| luxury | 1000 |

Full insurance halves the deposit.

---

## 3. Roles: who can do what

| Action | Customer | Agent | Manager | Admin |
|---|:-:|:-:|:-:|:-:|
| Book online, see own bookings and invoices | ✅ | | | |
| Dashboard, customers, reservations, rentals, payments | | ✅ | ✅ | ✅ |
| Check-out / check-in cars | | ✅ | ✅ | ✅ |
| Add and edit cars, maintenance, blacklist customers | | | ✅ | ✅ |
| Users, branches (edit), audit log, delete records | | | | ✅ |

The server enforces every one of these rules. Even if someone types a URL by hand, the API refuses actions their role doesn't allow.

---

## 4. A complete rental, step by step

This example follows one customer, Alice, through the whole process.

### Step 1 — Register the customer
**Customers → New customer.** Enter her name, date of birth, email, phone, driver license number, issuing country and expiry date.

Customers who sign up online already have a record, so you don't need to create one for them.

FleetRent then refuses any booking where:
- the driver is under **21** on the pickup date
- the license **expires before the return date**
- the customer is **blacklisted**

### Step 2 — Create the reservation
**Reservations → New reservation** (or the *New reservation* button on Alice's customer page):

1. Choose **pickup and return date/time**, and optionally a category and branches. Click **Search available cars**. Only cars that are free for the whole period are shown.
2. **Click a car.** A live price appears on the right.
3. Choose **insurance and extras**. The price updates as you go.
4. Search for and select **Alice** as the customer.
5. Click **Create confirmed reservation**. You land on the reservation page, which has a code like `R-7KQ2M9XA`.

> Bookings made by staff are confirmed immediately. Online bookings arrive as **Pending**. Open them and click **Confirm reservation**, or cancel them with a reason.

### Step 3 — Take the deposit
On the reservation page, under **Payments → Record a payment**:
- Type: **Deposit received**
- Amount: the *Deposit required* shown in the *Money* box
- Method: card, cash or transfer
- Reference: the card terminal receipt number, for example

The customer can also pay the rental up front with type **Payment**.

### Step 4 — Hand over the car (check-out)
When Alice arrives:
1. Check her **driver license and ID** against the customer record.
2. Walk around the car with her and note any existing scratches.
3. In the **Check-out** box, enter the **odometer** reading, the **fuel/charge level %** and your **condition notes**. Then click **Confirm check-out**.

The reservation becomes **Active**, the car becomes **Rented**, and a rental contract is created.

### Step 5 — Receive the car back (check-in)
When the car comes back, open the reservation (or **Rentals → On the road**). In the **Check-in** box:
1. Enter the **odometer**, the **fuel level** and the **actual return time**.
2. If there is new damage, describe it and enter a **damage fee**.
3. Tick **Send the car to maintenance** if it needs repair or cleaning.
4. Click **Close rental & compute final bill**.

FleetRent calculates the final total and frees the car. The car's mileage and branch are updated too: the branch becomes the return branch.

### Step 6 — Settle and print
1. The **Money** box shows the **final total**, the amount **paid** and the **balance due**.
2. Record the remaining **Payment**.
3. Return the deposit with a **Deposit returned** payment. If you keep part of it for damage, enter the returned amount only.
4. Click **Invoice → Print / Save as PDF** to give Alice her invoice.

### Other outcomes
- **Cancel:** open the reservation, enter a reason, then click *Cancel reservation*. This works while the booking is pending or confirmed. A refund can be recorded with type **Refund**.
- **No-show:** once the pickup time has passed, click *Mark as no-show* on a confirmed reservation. This frees the car.

---

## 5. How the bill is calculated

| Item | Rule |
|---|---|
| Rental days | Every started 24 h counts as a day. 3 days and 1 hour = 4 days. |
| Base | days × the daily rate (frozen at booking time, so later price changes don't affect existing bookings) |
| Extras per day | basic insurance 12 · full insurance 25 · GPS 5 · child seat 4 · additional driver 8 |
| Late return | After a 60-minute grace period, each started day costs (daily rate + extras) × 1.25 |
| Mileage | 300 km per day included. Each extra km costs 0.30. |
| Fuel / charge | Each % below the pickup level costs 1.50 |
| Damage | The amount entered at check-in |
| Tax | `TAX_RATE` (default 20%) applied to everything above |

**Example:** a 3-day rental at 50/day with basic insurance and GPS, returned on time.

- Base: 3 × 50 = 150
- Extras: 3 × (12 + 5) = 51
- Subtotal: 201
- Tax (20%): 40.20
- **Total: 241.20**

---

## 6. Daily routine

**Morning:** open the **Dashboard**.
- *Pickups today* tells you which cars to prepare.
- *Returns today* tells you who is coming back.
- *Overdue* (in red) means calling the customer.
- *Pending approval* lists online bookings to confirm.

**During the day:** create bookings for walk-in and phone customers, and do check-outs and check-ins.

**Evening:** check **Payments** filtered by today's date and compare the totals with the cash drawer and card terminal.

---

## 7. Fleet and maintenance (manager)

- **Change a price:** *Fleet → Edit → Daily rate*. Only new bookings use the new price.
- **Take a car out of service:** *Maintenance → Schedule maintenance*. Pick the car, type, date, cost and garage. Then:
  - **Start** makes the car unavailable for booking. You can't start maintenance on a car that is currently rented.
  - **Complete** makes it available again and updates its mileage.
- **Sell or retire a car:** *Fleet → Edit → Status: Retired*. Cars with history can't be deleted, which keeps your records intact.
- **Blacklist a customer:** open the customer, enter a reason, then click **Blacklist customer**. They can no longer book.

---

## 8. Security tasks (admin)

- **Audit log:** review it weekly. Rows highlighted in yellow are failed logins, blocked logins and refresh-token reuse. Token reuse is a sign that someone may have stolen a session. Filter by `payment` to review money movements.
- **Locked accounts:** an account locks for 15 minutes after 5 wrong passwords. Use *Users → Unlock* if the user really is who they say they are.
- **Someone leaves the agency:** *Users → Edit → untick Account active*. They're signed out of every device immediately.
- **Forgotten password:** *Users → Reset password*. Every one of that user's sessions is revoked.
- **Backups:** see the README. Test a restore at least once.

---

## 9. For customers: booking online

1. On the login page, click **Create an account**. Enter your details, driver license and a strong password.
2. **Book a car:** choose your dates, then **Search available cars**. Pick a car and options; the full price and deposit are shown right away.
3. Click **Request booking**. The status is **Pending** until the agency confirms it. Check it under **My reservations**.
4. **Cancel** from the reservation page any time before the pickup time.
5. **At pickup**, bring your driver license and ID. A refundable deposit is taken.
6. After the rental, open the reservation and click **Invoice** to view or print it.
7. Keep your phone number and license details up to date under **My profile**.
