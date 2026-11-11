# Design System & User Interface Specification
## Intelligent Workforce Scheduling & Optimization Platform

**Document Version:** 1.0.0  
**Design Baseline:** Enterprise Operational System  
**Lead UI/UX Architect:** AI Front-End Engineering Team  

---

## 1. Design Philosophy & Core Principles

The Workforce Scheduling & Optimization Platform is a high-density, high-criticality operational enterprise system. The UI must facilitate fast cognitive parsing, transparent decision tracking, and effortless navigation between macro-level schedules and micro-level employee constraints.

### Core UX Principles:
1. **Explainability Over Magic:** Every optimization output, gap, and constraint violation must be visually explained with clear indicators and badges.
2. **High-Density, Legible Information Architecture:** Calendars, rosters, and tables prioritize clean grid lines, legible type scales, and status tags over empty decorative space.
3. **Role-Tailored Context:** Employees see personal schedules and immediate action items (leaves, swaps); Managers see coverage heatmaps, approval queues, and team rosters; HR & Admins see enterprise-wide metrics and configuration.
4. **State Transparency:** Immediate visual feedback for pending, approved, conflict, and gap states across all workflows.

---

## 2. Visual Foundation: Color Palette & Typography

### 2.1 Color Tokens (Tailwind CSS Mapping)

| Semantic Role | Hex Code | Tailwind Token | Usage |
| :--- | :--- | :--- | :--- |
| **Primary Brand** | `#0f172a` | `slate-900` | Navigation sidebar, primary headings, core accents |
| **Primary Interactive** | `#2563eb` | `blue-600` | Primary buttons, active tabs, selected dates |
| **Primary Hover** | `#1d4ed8` | `blue-700` | Button hover states |
| **Surface Background** | `#f8fafc` | `slate-50` | Global application canvas background |
| **Card & Panel Background** | `#ffffff` | `white` | Cards, modals, calendar grid cells |
| **Border & Divider** | `#e2e8f0` | `slate-200` | Table borders, card outlines, separators |
| **Text Primary** | `#0f172a` | `slate-900` | High-emphasis body copy, KPI values |
| **Text Secondary** | `#64748b` | `slate-500` | Labels, timestamps, subtle metadata |
| **Success / Optimal** | `#16a34a` | `green-600` | Full coverage, approved status, optimal solver status |
| **Warning / Pending** | `#d97706` | `amber-600` | Pending approvals, high overtime approaching cap |
| **Danger / Anomaly** | `#dc2626` | `red-600` | Coverage shortage, hard constraint breach, anomaly alert |
| **Info / Scheduled** | `#0284c7` | `sky-600` | Standard shift allocation, published roster |

### 2.2 Typography
- **Primary Typeface:** `Inter`, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif.
- **Monospace Typeface (for IDs, timestamps, solver stats):** `JetBrains Mono`, `Fira Code`, monospace.
- **Hierarchy:**
  - Page Title: `text-2xl font-bold tracking-tight text-slate-900`
  - Section Header: `text-lg font-semibold text-slate-800`
  - Body Text: `text-sm font-normal text-slate-700`
  - Small / Metadata: `text-xs font-medium text-slate-500`
  - KPI Stat: `text-3xl font-extrabold tracking-tight text-slate-900`

---

## 3. Component System & Design Patterns

### 3.1 Status Badges
- **Approved / Feasible:** Green pill `bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded-full text-xs font-medium`
- **Pending Approval:** Amber pill `bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full text-xs font-medium`
- **Shortage / Rejected / Anomaly:** Red pill `bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded-full text-xs font-medium`
- **Shift Category (Morning, Afternoon, Night):**
  - Morning: `bg-sky-50 text-sky-700 border-sky-200`
  - Afternoon: `bg-indigo-50 text-indigo-700 border-indigo-200`
  - Night: `bg-purple-50 text-purple-700 border-purple-200`

### 3.2 Modal Dialogs & Drawers
- Dismissible with `Escape` or backdrop click.
- Fixed header with title and close button; scrollable body; sticky footer with secondary cancel and primary action buttons.
- Destructive actions require explicit confirmation dialogs.

### 3.3 Data Tables
- Sticky headers on scroll.
- Responsive pagination, page size selector (10, 25, 50, 100), and search input filter.
- Inline status badges and action menus (View, Edit, Approve, Reject).

---

## 4. Navigation Architecture & Layout

The interface features an enterprise dual-tier navigation:
1. **Collapsible Left Sidebar:**
   - Platform brand header with active role indicator and switcher.
   - Grouped navigation links with icons:
     - **Main:** Dashboard / Overview
     - **Workforce:** Employees, Teams, Skills
     - **Schedules:** Shift Templates, Shift Rostering & Calendar
     - **Workflows:** Leave Requests, Shift Swaps, Attendance & Overtime
     - **Analytics:** Coverage Analysis, Fairness Ratios, Exceptions & Anomalies
     - **Data Engine:** Synthetic Generator, Quality Evaluation, Audit History
2. **Top Header Bar:**
   - Active view breadcrumbs.
   - Active Seed & Simulation Profile indicator (`Seed: 20261022 | Profile: STARTER`).
   - Role Switcher dropdown (`Employee`, `Manager`, `HR Partner`, `Operations`, `Admin`) for seamless live role evaluation.
   - User profile badge with quick sign-out.

---

## 5. Screen Specifications

### 5.1 Shift Scheduling & Interactive Calendar
- **Views:** Day, Week, and Team Matrix grid views.
- **Roster Cells:** Render employee card per shift with assigned skill badge.
- **Coverage Gauge:** Visual bar at the top of each shift column showing `X / Y filled` (Green for 100%, Red for shortage).
- **Run Optimizer Button:** Opens modal configuring planning horizon (start/end date), team filter, objective weights, and timeout; displays real-time execution spinner and solver output statistics (`OPTIMAL`, runtime, shifts assigned).

### 5.2 Leave Management Screen
- **Dual Pane Layout:**
  - Left/Top: Summary KPI cards (Pending requests, Total approved days, Current team on leave).
  - Main: Leave requests table with columns for ID, Employee, Type, Date Range, Duration, Status, and Actions (Approve/Reject).
  - Filter by status (`ALL`, `PENDING`, `APPROVED`, `REJECTED`).
  - "Submit Leave" modal with auto-calculation of working days and balance check.

### 5.3 Shift Swap Screen
- Tabbed interface: "My Swap Requests" vs. "Manager Review Queue".
- Each swap card visualizes:
  - Source: Employee A and their Shift Date/Time/Skill.
  - Target: Employee B and their Shift Date/Time/Skill.
  - Automated Feasibility Checks: Green tick or red warning for Skill Match, Rest Interval, and Max Hours compliance.
  - Action buttons: "Approve & Apply Swap" or "Reject".

### 5.4 Attendance & Overtime Reconciliation
- Daily reconciliation view comparing scheduled shifts with clock-in/out timestamps.
- Discrepancy highlights: Yellow for Late > 15m, Red for Absent or Missed Clock-out.
- Overtime tab: Table and charts showing regular hours, overtime hours, and overtime cap utilization bar.

### 5.5 Fairness Analytics Dashboard
- Multi-dimensional fairness metrics:
  - Hours Deviation Bar Chart: Compares each employee's assigned hours against the team mean.
  - Weekend Shifts Distribution: Visualizes Saturday/Sunday count per employee.
  - Night Shift Rotation: Heatmap ensuring equitable night shift allocations.
  - Composite Fairness Index: Standard deviation score and Gini inequality coefficient.

### 5.6 Synthetic Data & Anomaly Injection Screen
- Profile Selector: `STARTER` (100 emp, 10 teams, 14 days) vs. `FULL` (2,000 emp, 100 teams, 90 days).
- Seed input (default: `20261022`) with "Generate Dataset" button.
- Progress bar and generation step log:
  1. Master Data Generation
  2. Dependent Records Generation
  3. Baseline Validation
  4. Labelled Anomaly Injection (5 categories)
  5. Isolated Ground Truth Compilation
- Export Center: One-click download buttons for CSV zip, JSON, and SQL seed files.
- Reproducibility verification tool: Runs dual execution and displays SHA-256 and row count comparison report.

### 5.7 Evaluation & Benchmark Screen
- One-click "Execute Evaluation".
- Results Dashboard:
  - Overall Data Quality score (PK, FK, Enums, Constraints: 100%).
  - Anomaly Detection Metrics: Confusion Matrix (TP, FP, TN, FN), Precision, Recall, and F1 score for all 5 anomaly types.
  - Detailed classification drill-down table.
  - Downloadable JSON and Markdown Evaluation Report.

