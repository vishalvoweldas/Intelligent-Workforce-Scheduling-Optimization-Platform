# Intelligent Workforce Scheduling & Optimization Platform

[![Author](https://img.shields.io/badge/Author-Vishal%20Voweldas-blue.svg)](https://github.com/vishalvoweldas)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-181717.svg?logo=github)](https://github.com/vishalvoweldas/Intelligent-Workforce-Scheduling-Optimization-Platform)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162.0-teal.svg)](https://fastapi.tiangolo.com)
[![OR--Tools](https://img.shields.io/badge/Google_OR--Tools-CP--SAT-red.svg)](https://developers.google.com/optimization)
[![React](https://img.shields.io/badge/React-19.0-cyan.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-sky.svg)](https://tailwindcss.com)
[![Tests](https://img.shields.io/badge/Tests-36%20Passed-emerald.svg)](tests/)

A production-grade, constraint-based workforce management, scheduling optimization, synthetic data simulation, and evaluation platform powered by **Google OR-Tools CP-SAT**, **FastAPI**, and **React 19**.

**Author:** Vishal Voweldas  
**Repository:** [https://github.com/vishalvoweldas/Intelligent-Workforce-Scheduling-Optimization-Platform](https://github.com/vishalvoweldas/Intelligent-Workforce-Scheduling-Optimization-Platform)

---

## Key Capabilities

### 1. Google OR-Tools CP-SAT Scheduling Engine
- **Mathematically Guaranteed Hard Constraints:**
  - **No Double-Booking:** An employee is assigned to at most one shift per calendar day.
  - **Mandatory Rest Periods:** Enforces minimum 11-hour consecutive rest between shift intervals.
  - **Skill Certification:** Hard validation that employees hold all required skills for their assigned shift template.
  - **Maximum Weekly Hours:** Guarantees total weekly hours do not exceed statutory and contractual limits (48h hard cap).
  - **Approved Leave Protection:** Pre-assigned and approved leaves immediately reserve availability, preventing overlapping shift assignments.
  - **Consecutive Work Days:** Enforces a maximum of 6 consecutive working days before mandatory rest.
- **Multi-Objective Weighted Optimization:**
  - Optimizes workload equity (hours distribution), weekend shift fairness, night shift rotation, and employee preference satisfaction.
- **Team-Scoped Solver Scalability:**
  - Linear scaling optimizer solves 14-day starter rosters in $< 0.5\text{s}$ and full 90-day team rosters in $1.43\text{s}$ with **OPTIMAL** status.

### 2. Dual Dataset Profile Switcher (STARTER vs. FULL PROFILE VOLUME)
- **Seamless Profile Switching:** Switch between development and enterprise-scale datasets directly from the header navigation dropdown without application restarts.
- **Dual SQLite Database Architecture:**
  - **`STARTER` Profile (`workforce_starter.db`):** 100 Employees, 11 Teams, 14-day planning horizon, 420 Shifts, 251 Leave requests, 348 Attendance punches.
  - **`FULL PROFILE` (`workforce_full.db`):** 2,000 Employees, 101 Teams, 90-day planning horizon, 27,000 Shifts, 5,000 Leave requests, 53,474 Attendance punches.
  - **Relational Isolation:** Dedicated database connections eliminate cross-profile data leakage and guarantee zero foreign key violations.

### 3. Five Canonical User Personas & Role-Based Dashboards
The platform provides five distinct role dashboards, each strictly tailored with role-based access control (RBAC):
1. **`EMPLOYEE` — Employee Self-Service Portal:**
   - Personal shift schedule calendar, biometric clock-in/out, leave request submission, and peer shift swap initiation.
2. **`MANAGER` — Manager Operational Control:**
   - Team headcount management, pending leave approvals, shift swap reviews, and local team-scoped CP-SAT solver runs.
3. **`HR_PARTNER` — HR Dashboard:**
   - Enterprise headcount analytics, labor compliance monitoring, overtime cap watchlist, and Gini coefficient equity tracking.
4. **`OPERATIONS` — Operations Dashboard:**
   - Global CP-SAT solver execution, synthetic data pipelines, benchmark scoring, and telemetry monitoring.
5. **`ADMIN` — Administration Dashboard:**
   - System governance, policy configuration, security audit logs, and cross-team administrative controls.

### 4. Complete Operational Workflows
- **Leave Management:** Submission, manager approval/rejection, balance tracking, and automatic schedule conflict resolution.
- **Shift Swap Management:** 7-stage lifecycle with automated feasibility pre-checks (skills, rest interval, overtime) and atomic database updates upon manager sign-off.
- **Attendance & Overtime Reconciliation:** Digital clock-in/out event matching, absence and late detection, and daily/weekly overtime calculation against contractual limits.

### 5. Synthetic Data Engine & Benchmark Evaluation
- **Deterministic Generation:** Fixed seed `20261022` producing bit-for-bit identical datasets across repeated executions.
- **Labelled Anomaly Scenarios:** Five canonical edge cases (`DOUBLE_BOOKING`, `LEAVE_CONFLICT`, `MISSING_SKILL`, `OVERTIME_EXCEEDED`, `UNAPPROVED_SWAP`).
- **Isolated Ground Truth Vault:** Separated ground truth store (`datasets/ground_truth/ground_truth.csv`, `ground_truth.json`) strictly isolated from solver pipelines.
- **Automated Benchmark:** Computes Confusion Matrices, Precision, Recall, and F1 scores per anomaly type.

---

## Architecture Overview

```
project-root/
│
├── PRD.md                 # Product Requirements Document
├── ARCHITECTURE.md        # Technical System Architecture & Mermaid Diagrams
├── DESIGN.md              # UI/UX Specifications & Component System
├── RULES.md               # Coding Standards & Development Protocols
├── TASKS.md               # Execution Roadmap & Status Tracking (v2.2.0)
├── SECURITY.md            # Security Model, RBAC Matrix & Audit Logging
├── README.md              # Project Overview & Quickstart Guide
├── API.md                 # REST API Specifications & Request/Response Schemas
├── DATABASE.md            # Data Dictionary, ER Schema & Indexing
├── TESTING.md             # Test Suite Protocols & Verification Evidence
├── DEPLOYMENT.md          # Production Deployment & Containerization Guide
├── DECISIONS.md           # Architecture Decision Records (ADRs)
│
├── backend/               # FastAPI Backend Service
│   ├── api/               # API Route Handlers (Workforce, Shifts, Leave, Swaps, etc.)
│   ├── models/            # SQLAlchemy 2.0 ORM Domain Models & Dynamic Database Proxy
│   ├── schemas/           # Pydantic v2 Request/Response Schemas
│   ├── services/          # Core Business Services & ID Generators
│   ├── scheduling/        # Google OR-Tools CP-SAT Solver & Constraints
│   ├── analytics/         # Coverage & Fairness Metric Engines
│   ├── evaluation/        # Benchmark Evaluator & Confusion Matrix
│   └── security/          # Auth, Identity Impersonation & Granular RBAC Guards
│
├── data_engine/           # Synthetic Data Engine
│   ├── generators/        # Deterministic Master & Dependent Data Generators
│   ├── distributions/     # Realistic Statistical Probability Samplers
│   ├── anomaly_injection/ # 5 Labelled Anomaly Ingestion Scenarios
│   ├── ground_truth/      # Isolated Ground Truth Store
│   ├── validators/        # Data Quality & Integrity Validators
│   └── exporters/         # CSV, JSON, and SQL Seed Exporters
│
├── frontend/              # React 19 + TypeScript + Vite + Tailwind CSS SPA
│   ├── src/               # Application Source (App.tsx, api.ts, types.ts)
│   ├── dist/              # Pre-Compiled Production Build
│   └── package.json       # Frontend Dependencies
│
├── datasets/              # Starter, Full, and Ground Truth Dataset Packages
├── tests/                 # Unit, Scheduling, Data Quality & Integration Tests (36 Tests)
└── scripts/               # Platform Initialization & Seeding CLI Scripts
```

---

## Quickstart Guide

### Prerequisites
- **Python:** 3.13+ installed
- **Node.js:** 20+ and npm installed
- **Git:** Installed and configured

### 1. Clone the Repository
```powershell
git clone https://github.com/vishalvoweldas/Intelligent-Workforce-Scheduling-Optimization-Platform.git
cd Intelligent-Workforce-Scheduling-Optimization-Platform
```

### 2. Backend Setup
```powershell
# Install backend dependencies
pip install fastapi uvicorn sqlalchemy pydantic ortools pandas numpy scipy scikit-learn pytest httpx

# (Optional) Initialize databases and synthetic datasets if not already present
python scripts/init_platform.py

# Start the FastAPI backend server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
- **API Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`
- **Alternative Redoc Documentation:** `http://127.0.0.1:8000/redoc`
- **Health Check Endpoint:** `http://127.0.0.1:8000/api/v1/health`

### 3. Frontend Setup
```powershell
# Navigate to the frontend directory
cd frontend

# Install frontend dependencies
npm install

# Option A: Start development server
npm run dev

# Option B: Preview pre-compiled production build
npm run preview
```
- **Interactive UI Portal:** `http://localhost:5173`

### 4. Run Automated Test Suite
```powershell
# Run all 36 automated pytest tests across unit, security, scheduling, and integration suites
python -m pytest tests/ -v
```

### 5. Compile Frontend Production Bundle
```powershell
# Build production bundle with Vite and TypeScript compiler verification
cd frontend
npm run build
```

---

## Verification & Compliance Status

- **Automated Tests:** **36 / 36 passed (100%)** in `~7.5s`
- **TypeScript & Build:** **0 errors, 0 warnings** (TypeScript strict mode validated with `tsc --noEmit`)
- **Foreign Key Constraints:** **0 violations** across all SQLite databases
- **Ground Truth Isolation:** Bit-for-bit reproducibility with seed `20261022`
- **Final Verdict:** **READY FOR SUBMISSION**

---

## License

This project is developed and maintained by **Vishal Voweldas** as part of the Intelligent Workforce Scheduling & Optimization Platform initiative. All rights reserved.
