# CompressorIQ — User Guide

**For the full narrative manual** (screen-by-screen descriptors for managers and technicians), see **[`USER_MANUAL.md`](USER_MANUAL.md)** or open **User manual** in the app sidebar.

This shorter guide summarizes how to use the web application from two perspectives: **service manager** (fleet oversight and dispatch) and **field technician** (executing assigned work). The same login is not required today—the app uses the same navigation for everyone; use the pages that match your role.

---

## Before you start

1. **Backend API** must be running (default: `http://127.0.0.1:8001`).
2. **Web app** must be running (default: `http://localhost:3000` or `http://127.0.0.1:3000`).
3. If your administrator enabled an **API key**, the frontend needs matching `NEXT_PUBLIC_API_KEY` in its environment, or some actions (creating work orders, uploads, assessments) will fail—ask your admin.

**Tip:** Keep the project on a local disk (not synced cloud folders) for faster loading during development.

---

## Navigation (sidebar)

| Page | Typical role |
|------|----------------|
| **Dashboard** | Everyone — fleet overview; deep-dive when a compressor is selected |
| **Service Records** | Manager, planner — browse and search historical work orders / events |
| **Compressors** | Manager — asset list, timelines, issue frequency |
| **Work orders** | **Manager** — create, filter, assign, change status |
| **My work** | **Technician** — jobs assigned to you, step-by-step execution |
| **Notifications** | Everyone — system alerts and assignment notices |
| **Workflows** | Manager, engineer — AI recommendations and linked workflows |
| **Upload Data** | Manager, data admin — import spreadsheets |

---

# Manager view

Use this path when you oversee the fleet, prioritize risk, and assign corrective work.

## Dashboard

- **Fleet overview (default):** KPI-style metrics, recent service events, and **machines needing attention** (elevated recent activity).
- **Compressor selector:** Choose a unit to open the **detail view** for that asset.
- **Per-compressor detail:** Stats, **AI Health Assessment** (Run / Re-assess), alerts, issue frequency, and **recommendations** for that machine.
- **Health assessment:** Combines history and optional AI. For severe alerts, the system may **open system work orders** automatically (see *Automated work orders* below). The UI shows how many were created and links to **Work orders**.

**Manager actions here:** Interpret health and alerts, decide priority, then create or assign work on **Work orders**.

## Compressors (`/machines`)

- Browse all compressors, open **detail**, **timeline** of events, and **issue frequency** analysis.
- Use this for investigations before opening a work order or when answering questions about a unit.

## Service Records (`/service-records`)

- Search and review historical **service events** (orders, categories, notes).
- Use for research, audits, and understanding past repairs—not for assigning new field work (use **Work orders** for that).

## Work orders (`/work-orders`) — primary manager tool

1. **Fleet queue:** Table of work orders with status, source, unit, assignee, and dates.
2. **Filters:** By **status** and **compressor** to focus the list.
3. **New work order**
   - Pick **compressor**, **title**, optional **description**.
   - **Source:** *Predictive*, *System-generated*, or *Ad hoc* (reflects how the job was triggered).
   - Optionally **link a recommendation** (loads steps from that recommendation’s workflow).
   - If you do *not* link a recommendation, provide an **issue category** (or leave blank for a general workflow)—the app generates step-by-step guidance from templates.
   - Optionally **assign a technician** immediately, or leave unassigned and assign later.
4. **Detail panel (selected row):** Change **assignee**, **status** (open → in progress → completed / cancelled), and preview **workflow steps**.

**Best practice:** Triage **system** and **predictive** items the same day; use **ad hoc** for anything that did not come from analytics.

## Notifications (`/notifications`)

- **Fleet-wide:** e.g. when a **system work order** is created from a health assessment.
- **Filter:** Unread vs all; **Mark all read** when caught up.
- Technicians see **broadcast** items plus items **addressed to them** (see Technician view).

## Workflows (`/workflow`)

- Lists **recommendations** across the fleet with confidence and status.
- Open a recommendation to see the **prescriptive workflow** tied to that insight.
- Use with **Work orders** when converting an insight into dispatched work.

## Upload Data (`/upload`)

- Upload maintenance spreadsheets (supported formats shown on the page).
- After processing, master data and events refresh—compressors and history update for the whole team.

---

# Technician view

Use this path when you perform work in the field and need clear instructions.

## My work (`/my-work`)

1. **Who you are:** Select your name in **You are**. The list is stored in the browser (`localStorage`) so the page remembers you next time. If your name is missing, the directory may need data import—ask a manager.
2. **Assigned to me:** Open work orders where **you** are the assignee, excluding completed/cancelled by default.
3. **Open a job:** Read the full **title**, **unit**, and **description**.
4. **Steps:** Each step shows **instructions**, **rationale**, and **evidence** to capture. Check steps off as you complete them.
5. **Mark work order complete** when the job is done from a field perspective (managers may still close or audit in **Work orders**).

**Note:** If nothing appears, no jobs are assigned to you yet—your manager assigns them under **Work orders**, or the system may create jobs from health assessments without an assignee (manager must assign).

## Notifications (`/notifications`)

- Shows **fleet** notifications plus anything **targeted to you** (for example, when a manager assigns you a work order).
- Use **Mark read** / **Mark all read** to clear your list.
- Align **You are** on **My work** with how you filter notifications if your admin uses technician-scoped alerts.

## Dashboard (read-only context)

- Technicians can use the **Dashboard** to see fleet context and run **health assessment** on a selected compressor for awareness.
- Day-to-day execution stays under **My work**.

## Workflows (`/workflow`)

- Useful to **read** recommendation history and workflow text for a machine you are working on; primary execution path is **My work** once a work order exists.

---

# Automated work orders (managers & technicians)

When someone runs **AI Health Assessment** on the **Dashboard** for a compressor:

- Alerts with severity **high** or **critical** (configurable server-side) can automatically create **system** work orders with deduplicated titles per unit.
- **Notifications** inform the team; technicians see assignments only after a manager **assigns** the work order.

---

# Status and source vocabulary

**Work order status**

- **Open** — Not started or not yet accepted in the field.
- **In progress** — At least one step completed or work underway.
- **Completed** — Job finished.
- **Cancelled** — Superseded or not needed.

**Work order source**

- **Predictive** — Tied to analytics / recommendations.
- **System** — Created automatically (e.g. from health assessment).
- **Ad hoc** — Created manually by a manager without a linked recommendation.

---

# Troubleshooting

| Symptom | What to check |
|--------|----------------|
| Page loads forever | API running on port **8001**? Correct `NEXT_PUBLIC_API_URL`? |
| “API error 401” on actions | API key required—frontend key must match backend. |
| Empty technician list | Import service data so technicians appear in the directory. |
| No jobs under **My work** | Manager must assign you on **Work orders**, or create/claim jobs. |
| Slow dev experience | Move project off cloud-synced folders if possible. |

---

# Quick reference

| Goal | Where to go |
|------|-------------|
| See fleet health and alerts | **Dashboard** |
| Assign or create jobs | **Work orders** |
| Do assigned steps in the field | **My work** |
| See system and personal alerts | **Notifications** |
| Import new maintenance data | **Upload Data** |
| Browse AI recommendations | **Workflows** |
| Look up a machine’s history | **Compressors** or **Service Records** |

---

# Appendix: PDF of UI screenshots

In the app, open **User guide (PDF)** in the **left sidebar** (below the main menu). It opens the full guide PDF in a new browser tab (`/CompressorIQ_User_Guide_Screenshots.pdf`).

You can also generate or refresh that PDF for training packs:

1. Start the **frontend** (`npm run dev` in `frontend/`, default `http://127.0.0.1:3000`).
2. From the **project root**, install capture dependencies (once):

   ```bash
   pip install -r scripts/requirements-screenshots.txt
   playwright install chromium
   ```

3. Run the capture script:

   ```bash
   python scripts/capture_screenshots_pdf.py
   ```

4. The script writes **`CompressorIQ_User_Guide_Screenshots.pdf`** at the project root and copies it to **`frontend/public/`** so the sidebar link stays up to date.

Use another base URL if needed, for example:

`set BASE_URL=http://localhost:3000` (Windows) or `BASE_URL=http://localhost:3000 python scripts/capture_screenshots_pdf.py` (Linux/macOS).

The PDF is built with the browser’s **Print to PDF** engine (vector, multi-page per screen), not flat image screenshots.

---

*CompressorIQ — predictive and prescriptive maintenance for compressor fleets.*
