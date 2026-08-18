#!/usr/bin/env python3
"""Serializable repair plans and precondition validation."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


REPAIR_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RepairStep:
    step_id: str
    summary: str
    reversible: bool
    disruptive: bool = False
    requires_privilege: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.step_id,
            "summary": self.summary,
            "reversible": self.reversible,
            "disruptive": self.disruptive,
            "requires_privilege": self.requires_privilege,
        }


@dataclass(frozen=True)
class RepairPlan:
    plan_id: str
    generated_at: str
    target_type: str
    target: str
    precondition_hash: str
    applicable: bool
    blockers: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    steps: List[RepairStep] = field(default_factory=list)
    schema_version: int = REPAIR_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "generated_at": self.generated_at,
            "target_type": self.target_type,
            "target": self.target,
            "precondition_hash": self.precondition_hash,
            "applicable": self.applicable,
            "blockers": self.blockers,
            "issues": self.issues,
            "requires_privilege": any(step.requires_privilege for step in self.steps),
            "disruptive": any(step.disruptive for step in self.steps),
            "steps": [step.to_dict() for step in self.steps],
        }


class RemediationService:
    """Build and revalidate plans while UserManager performs the mutation."""

    def __init__(self, user_manager, now=None):
        self.user_manager = user_manager
        self._now = now or (lambda: datetime.now(timezone.utc))

    def plan_user(self, username: str) -> RepairPlan:
        diagnosis = self.user_manager.diagnose_user(username)
        fingerprint = self._fingerprint(diagnosis)
        blockers = []
        if not diagnosis.get("exists"):
            blockers.append("System account does not exist")
        elif not diagnosis.get("managed"):
            blockers.append("Account is not managed by RDP Session Manager")
        if diagnosis.get("active"):
            blockers.append("Disconnect the user before applying this plan")

        issues = [
            issue for issue in diagnosis.get("issues", [])
            if issue != "User has active processes"
        ]
        steps = []
        if diagnosis.get("exists") and diagnosis.get("managed"):
            steps.append(RepairStep(
                "restore-managed-profile",
                "Validate and rewrite connection profiles and the session dispatcher",
                reversible=True,
            ))
            if diagnosis.get("session_type") == "winege-remoteapp":
                steps.append(RepairStep(
                    "restore-windows-runtime",
                    "Validate and provision the configured Windows application runtime",
                    reversible=False,
                ))
            steps.append(RepairStep(
                "reset-rdp-password",
                "Set and validate a new RDP account password",
                reversible=False,
            ))
        return RepairPlan(
            plan_id=str(uuid.uuid4()),
            generated_at=self._now().isoformat(),
            target_type="user",
            target=username,
            precondition_hash=fingerprint,
            applicable=not blockers,
            blockers=blockers,
            issues=issues,
            steps=steps,
        )

    def validate_user_plan(self, plan: RepairPlan) -> tuple[bool, str]:
        if plan.schema_version != REPAIR_SCHEMA_VERSION:
            return False, "Unsupported repair plan schema"
        if plan.target_type != "user":
            return False, "Repair plan target is not a user"
        if not plan.applicable:
            return False, "; ".join(plan.blockers) or "Repair plan is not applicable"
        diagnosis = self.user_manager.diagnose_user(plan.target)
        if self._fingerprint(diagnosis) != plan.precondition_hash:
            return False, "The account changed after the plan was generated; diagnose it again"
        return True, ""

    @staticmethod
    def _fingerprint(diagnosis: Dict[str, Any]) -> str:
        relevant = {
            "exists": bool(diagnosis.get("exists")),
            "managed": bool(diagnosis.get("managed")),
            "active": bool(diagnosis.get("active")),
            "session_type": diagnosis.get("session_type", ""),
            "app_command": diagnosis.get("app_command", ""),
            "issues": sorted(str(item) for item in diagnosis.get("issues", [])),
        }
        encoded = json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()
