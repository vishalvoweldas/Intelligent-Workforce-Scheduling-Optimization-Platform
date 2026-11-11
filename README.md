# Intelligent Workforce Scheduling & Optimization Platform

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162.0-teal.svg)](https://fastapi.tiangolo.com)
[![OR--Tools](https://img.shields.io/badge/Google_OR--Tools-CP--SAT-red.svg)](https://developers.google.com/optimization)
[![React](https://img.shields.io/badge/React-19.0-cyan.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-sky.svg)](https://tailwindcss.com)

A production-grade, constraint-based workforce management, scheduling optimization, synthetic data simulation, and evaluation platform.

---

## Key Capabilities

1. **Google OR-Tools CP-SAT Scheduling Engine:**
   - Mathematically guaranteed hard constraint enforcement (no double bookings, approved leave protection, skill certification checks, minimum 11-hour rest intervals, maximum weekly hours, 6 consecutive day caps).
   - Multi-objective weighted optimization for workload equality, weekend fairness, night shift rotation, and employee preference satisfaction.
   - Comprehensive infeasibility diagnostics reporting exact coverage gaps and root causes.

2. **Complete Operational Workflows:**
   - **Leave Management:** Submission, manager approval/rejection, balance tracking, and automatic schedule conflict detection.
   - **Shift Swap Management:** Peer-to-peer swap proposals with automated feasibility pre-check (skills, rest, overtime) and atomic manager approval.
   - **Attendance & Overtime Reconciliation:** Digital clock-in/out event matching, absence and late detection, and daily/weekly overtime calculation.

3. **Multi-Dimensional Fairness & Coverage Analytics:**
   - Gini inequality coefficient and standard deviation of scheduled hours.
   - Weekend shift parity index and night shift distribution heatmaps.
   - Team and skill-level coverage fill rates.

4. **Dataset Profile Switcher (STARTER vs. FULL PROFILE VOLUME):**
   - Native frontend dropdown in the header to switch between `STARTER` (100 employees, 10 teams, 14 days) and `FULL PROFILE VOLUME` (2,000 employees, 100 teams, 90 days, 27,000 shifts, 5,000 leaves).
   - Dedicated multi-database session routing (`workforce_starter.db` and `workforce_full.db`) ensuring complete relational isolation and zero cross-profile data leakage.
   - Instantaneous switching ($< 10\text{ ms}$) without destructive data overwriting.
   - Scaled Google OR-Tools CP-SAT optimizer solving 90-day team rosters in 1.43 seconds with OPTIMAL status.

5. **Synthetic Data Engine & Benchmark Evaluation:**
   - Deterministic generator with fixed seed `20261022` for `STARTER` (100 emp) and `FULL` (2,000 emp) profiles.
   - Labelled injection of 5 mandatory edge cases (double booking, leave conflict, missing skill, overtime cap breach, unapproved swap).
   - Strictly isolated ground truth (`ground_truth.csv`, `ground_truth.json`).
   - Comprehensive automated benchmark evaluation computing Confusion Matrices, Precision, Recall, and F1 scores per anomaly type.

---

## Architecture Overview

```
project-root/
│
├── PRD.md                 # Product Requirements Document
├── ARCHITECTURE.md        # Technical System Architecture & Mermaid Diagrams
├── DESIGN.md              # UI/UX Specifications & Component System
├── RULES.md               # Coding Standards & Development Protocols
├── TASKS.md               # Execution Roadmap & Status Tracking
├── SECURITY.md            # Security Model, RBAC Matrix & Audit Logging
├── README.md              # Project Overview & Setup Guide
├── API.md                 # REST API Specifications & Request/Response Schemas
├── DATABASE.md            # Data Dictionary, ER Schema & Indexing
├── TESTING.md             # Test Suite Protocols & Verification Evidence
├── DEPLOYMENT.md          # Production Deployment & Containerization Guide
├── DECISIONS.md           # Architecture Decision Records (ADRs)
│
├── backend/               # FastAPI Backend Service
│   ├── api/               # API Route Handlers (Workforce, Shifts, Leave, Swaps, etc.)
│   ├── models/            # SQLAlchemy 2.0 ORM Domain Models
│   ├── schemas/           # Pydantic v2 Request/Response Schemas
│   ├── services/          # Core Business Services & Workflows
│   ├── scheduling/        # Google OR-Tools CP-SAT Solver & Constraints
│   ├── analytics/         # Coverage & Fairness Metric Engines
│   ├── evaluation/        # Benchmark Evaluator & Confusion Matrix
│   └── security/          # Auth, JWT, Password Hashing & RBAC
│
├── data_engine/           # Synthetic Data Engine
│   ├── generators/        # Deterministic Master & Dependent Generators
│   ├── distributions/     # Realistic Statistical Probability Samplers
│   ├── anomaly_injection/ # 5 Labelled Anomaly Ingestion Scenarios
│   ├── ground_truth/      # Isolated Ground Truth Store
│   ├── validators/        # Data Quality & Integrity Validators
│   └── exporters/         # CSV, JSON, and SQL Seed Exporters
│
├── frontend/              # React 19 + TypeScript + Vite + Tailwind CSS SPA
├── datasets/              # Starter, Full, Anomaly, and Ground Truth datasets
├── tests/                 # Unit, Scheduling, Data Quality & Integration Tests
└── scripts/               # Automation, Seeding & Benchmarking CLI Scripts
```

---

## Quickstart Guide

### Prerequisites
- Python 3.13+ installed
- Node.js 20+ and npm installed

### 1. Backend Setup
```powershell
# Navigate to project root
cd "c:\CandidateWorkspace\Intelligent Workforce Scheduling & Optimization Platform"

# Install backend dependencies
pip install fastapi uvicorn sqlalchemy pydantic ortools pandas numpy scipy scikit-learn pytest httpx

# Initialize database and generate starter dataset
python scripts/init_platform.py

# Run backend development server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

The interactive frontend will be accessible at `http://localhost:5173` and the backend Swagger API documentation at `http://127.0.0.1:8000/docs`.

### 3. Run Automated Test Suite
```powershell
pytest tests/ -v
```

