# PharmaAudit OS — Complete System & Workflow Documentation

Welcome to **PharmaAudit OS**, an enterprise pharmaceutical inventory management, FEFO dispensing, EOQ/ROP optimization, and audit compliance system built for hospital and clinical pharmacies.

---

## 📌 Executive Summary & Key Workflows

### What Happens When You Click "+ Draft PO" or "+ Auto PO"?
When you click **"+ Draft PO"** on an ROP Alert card (on the Dashboard) or **"+ Auto PO"** (in the Stock Catalog):
1. **Automated Trigger**: The system checks if the medication has a configured supplier.
2. **EOQ Calculation**: It retrieves the drug's calculated **Economic Order Quantity (EOQ)** recommendation ($EOQ = \sqrt{\frac{2DS}{H}}$).
3. **PO Creation**: A new **Purchase Order (PO)** is automatically generated in `DRAFT` status and assigned to the medication's primary supplier, with the order quantity set to the recommended EOQ.
4. **Audit Logging**: An immutable audit record (`PO_CREATE`) is written to the cryptographic audit trail.
5. **Real-Time Broadcast**: A real-time notification (`Draft PO Generated`) is broadcast to all users via the Notification Bell and toast widget.
6. **Approval Workflow**: The Draft PO appears in **Purchase Orders (EOQ)** (`/orders/`). Users with the **Inventory Manager** or **Administrator** role can review the PO and click **"Approve PO"**, which transitions the order status to `APPROVED` and notifies the team.

---

## 🧭 Navigation & Sidebar Modules

The left sidebar navigation is divided into core clinical and operational modules:

### 1. 📊 Dashboard (`/`)
* **Stock Status Counters**: Live overview of SKUs categorized into:
  * **Adequate Stock**: Operating above Reorder Point (ROP).
  * **At Reorder Point (ROP)**: Stock has dropped to or below the safety threshold.
  * **Below Minimum Level**: Safety stock is compromised.
  * **Out of Stock**: Stock level is 0.
* **FR4 ROP Alert Engine**: Displays drug items needing attention with an instant **"+ Draft PO"** button.
* **FR6 ABC Classification Summary**: Overview of inventory distribution across Category A (Top 75% value), Category B (15%), and Category C (10%).
* **FR7 Expiry Warning Module**: Displays batches expiring within 30 days or already expired, with a one-click **"Quarantine"** button.
* **FR2 Cryptographic Audit Trail Feed**: Real-time table of recent user actions signed with SHA-256 hash chains.

---

### 2. 💊 Stock Catalog (EOQ/ROP) (`/medications/`)
* **Drug Catalog**: Search and filter medications by SKU, drug name, or pharmacy section.
* **Unit of Measure (UOM)**: Built-in dropdown selection supporting 18 standard pharmaceutical formulations (Tablets, Capsules, Vials, Ampoules, Bottles, Blisters, Syringes, Sachets, Boxes, Tubes, Packs, Drops, Inhalers, Suppositories, Ointments, Suspension, Solution, IV Bags).
* **Currency**: All monetary values, unit costs, and ordering parameters are styled in Nigerian Naira (`₦`).
* **Core Optimization Formulas**:
  * **Reorder Point (ROP)**:
    $$ROP = (\text{Daily Usage} \times \text{Lead Time Days}) + \text{Safety Stock}$$
  * **Economic Order Quantity (EOQ)**:
    $$EOQ = \sqrt{\frac{2 \times D \times S}{H}}$$
    *(Where $D$ = Annual Demand, $S$ = Ordering Cost per PO, $H$ = Annual Holding Cost per unit)*.

---

### 3. 🏢 Pharmacy Sections (`/sections/`)
* **Department Configuration**: Manage physical pharmacy locations and departments.
* **Pre-seeded Sections**:
  * *Main Central Pharmacy* (`SEC-MAIN`)
  * *Inpatient Ward Dispensary* (`SEC-INP`)
  * *Outpatient Pharmacy* (`SEC-OUTP`)
  * *Accident & Emergency (A&E) Pharmacy* (`SEC-EMERG`)
  * *Pediatric & Neonatal Pharmacy* (`SEC-PED`)
  * *ICU & Critical Care Pharmacy* (`SEC-ICU`)
* **Form**: Register new sections with unique codes and location notes.

---

### 4. 🏭 Suppliers Directory (`/suppliers/`)
* **Manufacturer & Vendor Management**: Maintain contact details for drug suppliers.
* **Pre-seeded Nigerian Manufacturers**:
  1. *Fidson Healthcare Plc*
  2. *May & Baker Nigeria Plc*
  3. *Emzor Pharmaceutical Industries*
  4. *Swiss Pharma Nigeria Limited (Swipha)*
  5. *GlaxoSmithKline Consumer Nigeria*
* **Form**: Register company names, contact persons, emails, phones, and physical addresses.

---

### 5. 📦 Goods Receipt Intake (`/inventory/receive/`)
* **Stock Intake Workflow**: Register incoming medication shipments from suppliers.
* **Batch Details**: Input Batch Number, Initial Quantity, Manufacture Date, and Expiry Date.
* **Validation**: Enforces strict date checks (Expiry Date must be after Manufacture Date).
* **Automated Actions**:
  * Creates a new `MedicationBatch`.
  * Increases total stock in the catalog.
  * Records a cryptographic audit ledger entry (`GOODS_RECEIPT`).
  * Triggers a real-time broadcast notification to all team members.

---

### 6. ⚡ FEFO Auto Dispense (`/inventory/dispense-fefo/`)
* **First-Expired, First-Out (FEFO) Protocol**: Automatically dispenses medications from batches with the **earliest expiration date** first to prevent drug expiration waste.
* **Multi-Batch Deduction**: If the requested quantity exceeds a single batch, the system sequentially depletes the earliest expiring batches.
* **Alert Triggers**: If stock falls to or below ROP or reaches 0, the system automatically fires a real-time ROP Breach or Out-of-Stock alert.

---

### 7. ⚖️ Physical Stock Audit (`/inventory/adjust/`)
* **Stock Reconciliation**: Conduct physical counts and compare them against system records.
* **Variance Calculation**:
  $$\text{Variance} = \text{Physical Count} - \text{System Stock}$$
* **Audit Trail**: Logs the discrepancy reason, before/after values, user ID, and IP address into the immutable ledger.

---

### 8. 📝 Purchase Orders (EOQ) (`/orders/`)
* **Manual & Automated PO Generation**: View, create, and manage purchase orders.
* **Approval Hierarchy**:
  * **Pharmacist**: Can initiate draft POs or trigger automated ROP draft POs.
  * **Inventory Manager / Admin**: Has exclusive authority to click **"Approve PO"**, changing status from `DRAFT` to `APPROVED`.

---

### 9. 📈 ABC Classification Console (`/analytics/abc/`)
* **Pareto Financial Analysis**: Categorizes inventory by **Annual Consumption Value** ($\text{Annual Demand} \times \text{Unit Cost}$):
  * **Category A (Top 75% Value)**: High-value drugs requiring strict daily cycle counts and tight lead times.
  * **Category B (Next 15% Value)**: Moderate-value items with periodic reviews.
  * **Category C (Remaining 10% Value)**: High-volume, low-value items managed with bulk ordering.

---

### 10. ⚠️ FEFO Expiry Alerts (`/inventory/expiries/`)
* **Expiration Monitoring Tiers**:
  * **EXPIRED**: Past expiration date. Includes a **"Quarantine"** button that sets batch quantity to 0, isolates the stock, and logs an audit trail entry.
  * **URGENT ($\le 30$ Days)**: Nearing expiration within 30 days.
  * **WARNING ($\le 90$ Days)**: Nearing expiration within 90 days.

---

### 11. 🛡️ Immutable Audit Ledger (`/audit/ledger/`)
* **Cryptographic Hash Chain**: Uses SHA-256 hashing to guarantee record integrity.
* **Tamper-Evident Signatures**: Each entry calculates:
  $$\text{Hash} = \text{SHA256}(\text{previous\_hash} + \text{timestamp} + \text{user} + \text{action} + \text{entity} + \text{data})$$
* Ensures full regulatory compliance for pharmaceutical inspections.

---

### 12. 📑 Generate Reports & CSV (`/reports/`)
* **On-Demand Exports**: View live reports for Stock Status, ABC Classification, Expiries, and Audit Logs.
* **One-Click Export**: Click **"Export Current Report (CSV)"** to download clean spreadsheet files for offline record-keeping.

---

### 🔔 Real-Time Notification System
* **Header Notification Bell**: Displays a live badge counter (`#notificationBadge`) of unread alerts.
* **Dropdown Preview**: Click the bell to view recent alerts (PO created/approved, stock intake, ROP breaches).
* **Toast Alerts**: Non-intrusive floating toasts pop up in real time whenever an inventory threshold is breached or a PO is processed.
