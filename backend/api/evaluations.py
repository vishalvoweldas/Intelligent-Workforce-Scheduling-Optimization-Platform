"""Evaluation Framework & Benchmark Execution Endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json
from backend.models.database import get_db
from backend.models.entities import (
    Employee, Shift, ShiftAssignment, LeaveRequest, SwapRequest, EmployeeSkill, CoverageRequirement, EvaluationRun
)
from backend.evaluation.detector import AnomalyDetector
from backend.evaluation.evaluator import BenchmarkEvaluator
from data_engine.ground_truth.vault import GroundTruthVault
from backend.security.rbac import get_current_user, require_role, resolve_current_user, CurrentUser, ROLE_OPERATIONS, ROLE_ADMIN, status

router = APIRouter(prefix="/evaluations", tags=["Evaluation Framework"])

@router.post("/run")
def run_evaluation(
    current_user: CurrentUser = Depends(require_role(ROLE_OPERATIONS, ROLE_ADMIN)),
    db: Session = Depends(get_db)
):
    """Scans current operational state, benchmarks against isolated ground truth, computes Confusion Matrix and F1."""
    current_user = resolve_current_user(current_user, db)
    if current_user.role not in (ROLE_OPERATIONS, ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Operations and Administrators can run evaluations."
        )
    # 1. Collect operational data from database
    operational_data = {
        "employees": [
            {"employee_id": e.employee_id, "contracted_weekly_hours": e.contracted_weekly_hours, "overtime_cap_hours": e.overtime_cap_hours}
            for e in db.query(Employee).all()
        ],
        "shifts": [
            {"shift_id": s.shift_id, "team_id": s.team_id, "template_id": s.template_id, "shift_date": s.shift_date.isoformat(), "start_datetime": s.start_datetime.isoformat(), "end_datetime": s.end_datetime.isoformat()}
            for s in db.query(Shift).all()
        ],
        "shift_assignments": [
            {"assignment_id": a.assignment_id, "shift_id": a.shift_id, "employee_id": a.employee_id}
            for a in db.query(ShiftAssignment).all()
        ],
        "leave_requests": [
            {"leave_id": l.leave_id, "employee_id": l.employee_id, "start_date": l.start_date.isoformat(), "end_date": l.end_date.isoformat(), "approval_status": l.approval_status}
            for l in db.query(LeaveRequest).all()
        ],
        "swap_requests": [
            {"swap_id": sw.swap_id, "requesting_employee_id": sw.requesting_employee_id, "receiving_employee_id": sw.receiving_employee_id, "status": sw.status, "manager_approver_id": sw.manager_approver_id}
            for sw in db.query(SwapRequest).all()
        ],
        "employee_skills": [
            {"employee_id": es.employee_id, "skill_id": es.skill_id, "is_certified": es.is_certified}
            for es in db.query(EmployeeSkill).all()
        ],
        "coverage_requirements": [
            {"team_id": cr.team_id, "template_id": cr.template_id, "skill_id": cr.skill_id}
            for cr in db.query(CoverageRequirement).all()
        ]
    }

    # 2. Run Anomaly Detector (Operational Logic)
    detector = AnomalyDetector()
    predicted_anomalies = detector.detect_all(operational_data)

    # 3. Read Isolated Ground Truth (Evaluation Only)
    from backend.models.profile_manager import get_active_profile
    import os
    active_prof = get_active_profile()
    gt_dir = "datasets/full" if active_prof == "FULL" and os.path.exists("datasets/full/ground_truth.json") else "datasets/ground_truth"
    vault = GroundTruthVault(base_dir=gt_dir)
    ground_truth = vault.load_ground_truth()

    # 4. Compute Benchmark Metrics
    evaluator = BenchmarkEvaluator()
    eval_result = evaluator.evaluate(
        predicted_anomalies=predicted_anomalies,
        ground_truth_records=ground_truth,
        total_records_evaluated=len(operational_data["shift_assignments"]) + len(operational_data["swap_requests"])
    )

    # 5. Persist Evaluation Run Record
    eval_id = f"EVAL-20261111-{db.query(EvaluationRun).count() + 1:04d}"
    eval_record = EvaluationRun(
        eval_id=eval_id,
        confusion_matrix_json=json.dumps(eval_result["confusion_matrix"]),
        precision=eval_result["overall_metrics"]["precision"],
        recall=eval_result["overall_metrics"]["recall"],
        f1_score=eval_result["overall_metrics"]["f1_score"],
        metrics_by_category_json=json.dumps(eval_result["by_category"])
    )
    db.add(eval_record)
    db.commit()

    return {
        "evaluation_id": eval_id,
        "confusion_matrix": eval_result["confusion_matrix"],
        "overall_metrics": eval_result["overall_metrics"],
        "by_category": eval_result["by_category"],
        "detected_anomalies": predicted_anomalies
    }

@router.get("/history")
def get_evaluation_history(db: Session = Depends(get_db)):
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(20).all()
    return [
        {
            "eval_id": r.eval_id,
            "precision": r.precision,
            "recall": r.recall,
            "f1_score": r.f1_score,
            "confusion_matrix": json.loads(r.confusion_matrix_json),
            "created_at": r.created_at.isoformat()
        }
        for r in runs
    ]

