# Security Architecture, Controls & Compliance Specification
## Intelligent Workforce Scheduling & Optimization Platform

**Document Version:** 1.0.0  
**Security Classification:** Enterprise Internal Sensitive  
**Lead Security Engineer:** AI Cybersecurity & Governance Architecture Team  

---

## 1. Threat Model & Security Posture

The Workforce Scheduling & Optimization Platform handles employee operational records, shift availability, medical/vacation leaves, biometric attendance, and workforce planning algorithms. The threat model accounts for:
1. **Unauthorized Access & Privilege Escalation:** Non-managers attempting to approve their own leaves or swaps, or unauthenticated users accessing employee PII.
2. **Schedule Tampering & Malicious Overrides:** Unauthorized modification of published shift assignments or historical records.
3. **Evaluation & Ground-Truth Integrity Compromise:** Leaking ground-truth anomaly labels into scheduling algorithms or standard user endpoints, invalidating evaluation benchmarks.
4. **Data Injection & Query Exploitation:** SQL injection, command execution, or malformed JSON payloads crashing the solver.
5. **Denial of Service (DoS):** Triggering unconstrained solver runs or massive dataset generations that exhaust server memory or CPU resources.

---

## 2. Authentication & Session Management

- **Protocol:** Stateless JSON Web Token (JWT) over TLS 1.3.
- **Token Signing:** HMAC-SHA256 (`HS256`) using a cryptographically secure 256-bit secret stored in environment variables (`JWT_SECRET_KEY`).
- **Token Lifetime:** Short-lived access tokens (60 minutes).
- **Token Claims Payload:**
  ```json
  {
    "sub": "EMP-000001",
    "email": "alex.miller@workforce.internal",
    "role": "MANAGER",
    "team_ids": ["TEAM-001", "TEAM-002"],
    "iat": 1794300000,
    "exp": 1794303600
  }
  ```
- **Password Hashing:** Passwords hashed with `bcrypt` (work factor 12) with unique per-user cryptographic salts. Plaintext passwords are never logged or stored.

---

## 3. Role-Based Access Control (RBAC) Matrix

Every API endpoint is protected by backend role dependency guards:

| Domain / Resource | Endpoint Pattern | EMPLOYEE | MANAGER | HR_PARTNER | OPERATIONS | ADMIN |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Own Profile & Shifts** | `GET /api/employees/me/shifts` | Read | Read | Read | Read | Read |
| **Team Rosters** | `GET /api/shifts/team/{id}` | Read (Own Team) | Read (Own Teams) | Read (All) | Read (All) | Read (All) |
| **Run Scheduling Solver** | `POST /api/schedules/run` | Denied | Execute (Own Team) | Denied | Execute (All) | Execute (All) |
| **Submit Leave Request** | `POST /api/leave/request` | Submit (Self) | Submit (Self) | Submit (Self) | Submit (Self) | Submit (Any) |
| **Approve / Reject Leave** | `POST /api/leave/{id}/decide` | Denied | Approve (Team) | Approve (All) | Denied | Approve (All) |
| **Request Shift Swap** | `POST /api/swaps/request` | Submit (Self) | Submit (Self) | Denied | Denied | Submit (Any) |
| **Approve Shift Swap** | `POST /api/swaps/{id}/decide` | Denied | Approve (Team) | Denied | Denied | Approve (All) |
| **Record Attendance** | `POST /api/attendance/event` | Ingest (Self) | Ingest (Team) | Ingest (All) | Ingest (All) | Ingest (All) |
| **Attendance Reconciliation**| `GET /api/attendance/recon` | Read (Self) | Read (Team) | Read (All) | Read (All) | Read (All) |
| **Fairness & Coverage** | `GET /api/analytics/*` | Read (Own Stats)| Read (Team) | Read (All) | Read (All) | Read (All) |
| **Synthetic Data Engine** | `POST /api/datasets/generate` | Denied | Denied | Denied | Execute | Execute |
| **Ground Truth Access** | `GET /api/evaluation/ground-truth`| **Strict Denied**| **Strict Denied** | **Strict Denied** | Read | Read |
| **System Audit Logs** | `GET /api/admin/audit-logs` | Denied | Denied | Read (Audit) | Read (Audit) | Full Admin |

### 3.1 Dynamic Impersonation & Identity Evaluation Security
For development, staging, and administrative impersonation:
- **Header Precedence:** The `X-User-Id` header takes precedence for explicit identity impersonation, followed by the Authorization Bearer JWT token (`jwt_token_for_<id>`).
- **Role Enforcement:** The `X-Role` header must match canonical roles (`EMPLOYEE`, `MANAGER`, `HR_PARTNER`, `OPERATIONS`, `ADMIN`). If omitted, the persisted database role is strictly enforced.
- **Data Scoping:** All downstream SQL queries strictly scope returned entities (`schedules/my`, `leave-requests`, `swaps`, `attendance/events`, `attendance/reconciliation`) to the verified `CurrentUser.employee_id`, preventing data leakage across impersonation sessions.

---

## 4. Ground-Truth Data Isolation & Anti-Leakage Protocol

To preserve scientific rigor and prevent benchmark contamination:
1. **Physical File Separation:** Ground-truth records are generated in a dedicated, isolated storage path (`datasets/ground_truth/`).
2. **Zero Ingestion in Solver:** The OR-Tools scheduling solver, constraint formulations, and daily operational services never import or reference ground-truth data models.
3. **No Flag in Operational DB:** Active shift assignments, leave records, and swaps in the database do not contain an `is_anomaly` column.
4. **Isolated Evaluation Harness:** Only the specialized evaluation module reads both the current operational state and the ground-truth vault to compute evaluation metrics.

---

## 5. Input Validation, Injection Prevention & Sanitization

1. **Strict Pydantic Validation:** All incoming request bodies are validated against strongly typed schemas (Pydantic v2). Extraneous fields are stripped (`extra = 'forbid'`).
2. **SQL Injection Prevention:** 100% of database interactions utilize SQLAlchemy ORM with parameterized queries and prepared statements. String concatenation in queries is strictly prohibited.
3. **Cross-Site Scripting (XSS) Prevention:** React safely escapes all dynamically rendered text by default. User-entered comments in leave or swap requests are strictly sanitized.
4. **Solver Resource Limits (DoS Prevention):**
   - Solver execution timeouts are capped at 60 seconds.
   - Max scheduling horizon is capped at 90 days.
   - Max teams per run is restricted by tier.

---

## 6. Audit Logging & Non-Repudiation

All state-altering actions generate an immutable audit log entry in the `audit_logs` table:
```json
{
  "log_id": "AUD-20261111-000492",
  "actor_id": "EMP-000042",
  "actor_role": "MANAGER",
  "action": "APPROVE_SHIFT_SWAP",
  "entity_type": "SWAP_REQUEST",
  "entity_id": "SWP-2026-000018",
  "details": {
    "shift_a": "SHIFT-2026-01-05-A",
    "emp_a": "EMP-000010",
    "shift_b": "SHIFT-2026-01-06-B",
    "emp_b": "EMP-000015"
  },
  "ip_address": "192.168.1.104",
  "timestamp": "2026-11-11T06:15:30.120Z"
}
```
Audit logs are append-only. No `UPDATE` or `DELETE` permissions are granted on the audit table.

---

## 7. Production Security Checklist

- [x] Passwords hashed using bcrypt (cost 12).
- [x] JWT secrets stored outside code in `.env`.
- [x] Role authorization enforced on backend API endpoints.
- [x] Ground-truth files isolated from application runtime.
- [x] Cross-Origin Resource Sharing (CORS) restricted to authorized origins.
- [x] Database connections parameterized via SQLAlchemy ORM.
- [x] Immutable audit trail for all approvals, overrides, and runs.
- [x] Solver compute bounded by explicit CPU timeouts.

