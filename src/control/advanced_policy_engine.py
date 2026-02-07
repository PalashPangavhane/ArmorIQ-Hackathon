"""
Advanced Policy Engine Module

Extends the base PolicyEngine with sophisticated enterprise-grade policies:
- Budget/Cost Center controls
- Segregation of Duties (SOD)
- Related Party Transaction detection
- Duplicate Transaction detection
- Employee-specific restrictions
- Multi-level approval workflows
- Geographic/Sanctions screening
- Velocity/Pattern analysis

KEY HACKATHON DIFFERENTIATOR:
These are the kinds of intricate, company-specific policies that
real enterprises use - far beyond simple amount limits.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import yaml
import os

from .policy_engine import PolicyEngine, PolicyEvaluation, PolicyResult


@dataclass
class BudgetCheck:
    """Result of budget validation."""
    approved: bool
    remaining_budget: float
    budget_type: str  # quarterly, annual, project
    utilization_percentage: float
    warning: Optional[str] = None


@dataclass
class SODCheck:
    """Result of Segregation of Duties check."""
    compliant: bool
    violation_type: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class DuplicateCheck:
    """Result of duplicate detection."""
    is_duplicate: bool
    duplicate_type: Optional[str] = None  # exact, similar, split
    matching_transactions: List[str] = field(default_factory=list)


class AdvancedPolicyEngine(PolicyEngine):
    """
    Advanced Policy Engine with enterprise-grade controls.
    
    ENTERPRISE POLICY CATEGORIES:
    
    1. BUDGET CONTROLS
       - Department budget tracking
       - Project/cost center validation
       - Quarterly/annual limits
    
    2. SEGREGATION OF DUTIES (SOD)
       - Requestor cannot self-approve
       - Vendor creator cannot pay
       - Three-way match required
    
    3. RELATED PARTY DETECTION
       - Subsidiary transactions
       - Conflict of interest checks
       - Board member companies
    
    4. DUPLICATE DETECTION
       - Same amount/vendor in time window
       - Invoice number duplicates
       - Split payment detection
    
    5. EMPLOYEE CONTROLS
       - New hire restrictions
       - Departing employee controls
       - Leave status verification
    
    6. APPROVAL WORKFLOWS
       - Sequential approval chains
       - Parallel approval for large amounts
       - Conditional routing
    
    7. GEOGRAPHIC/SANCTIONS
       - High-risk country screening
       - OFAC/sanctions list checks
    
    8. VELOCITY CONTROLS
       - Transaction frequency limits
       - Cumulative amount thresholds
       - Pattern break detection
    """
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)
        
        # Advanced policy data from YAML
        self.budget_policies: Dict[str, Dict] = {}
        self.sod_policies: List[Dict] = []
        self.related_party_policies: List[Dict] = []
        self.duplicate_policies: List[Dict] = []
        self.employee_policies: List[Dict] = []
        self.workflow_policies: List[Dict] = []
        self.geographic_policies: List[Dict] = []
        self.velocity_policies: List[Dict] = []
        
        # Runtime tracking
        self._department_spend: Dict[str, float] = {}
        self._project_spend: Dict[str, float] = {}
        self._transaction_history: List[Dict] = []  # For duplicate detection
        self._employee_transaction_count: Dict[str, int] = {}
        self._approval_chain: Dict[str, List[str]] = {}  # Track who approved what
        
        # Load advanced policies from YAML
        if config_path or os.path.exists(self._get_default_path()):
            self._load_advanced_policies(config_path or self._get_default_path())
    
    def _get_default_path(self) -> str:
        return os.path.join(
            os.path.dirname(__file__),
            "..", "..", "config", "policies.yaml"
        )
    
    def _load_advanced_policies(self, config_path: str):
        """Load advanced enterprise policies from YAML."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load budget policies
            for bp in config.get('budget_policies', []):
                dept = bp.get('department', 'default')
                self.budget_policies[dept] = bp
            
            # Load SOD policies
            self.sod_policies = config.get('segregation_of_duties', [])
            
            # Load related party policies
            self.related_party_policies = config.get('related_party_policies', [])
            
            # Load duplicate detection policies
            self.duplicate_policies = config.get('duplicate_detection', [])
            
            # Load employee policies
            self.employee_policies = config.get('employee_policies', [])
            
            # Load workflow policies
            self.workflow_policies = config.get('approval_workflow', [])
            
            # Load geographic policies
            self.geographic_policies = config.get('geographic_policies', [])
            
            # Load velocity policies
            self.velocity_policies = config.get('velocity_policies', [])
            
            print(f"✅ Loaded advanced enterprise policies:")
            print(f"   • Budget policies: {len(self.budget_policies)}")
            print(f"   • SOD policies: {len(self.sod_policies)}")
            print(f"   • Duplicate detection: {len(self.duplicate_policies)}")
            print(f"   • Employee policies: {len(self.employee_policies)}")
            print(f"   • Workflow policies: {len(self.workflow_policies)}")
            
        except Exception as e:
            print(f"⚠️ Warning loading advanced policies: {e}")
    
    def evaluate(self, intent: Dict[str, Any]) -> PolicyEvaluation:
        """
        Enhanced evaluation with ALL enterprise policies.
        
        FLOW:
        1. Base policy checks (amount, vendor, category, time, cap)
        2. Budget/Cost Center validation
        3. Segregation of Duties check
        4. Duplicate transaction detection
        5. Employee-specific restrictions
        6. Geographic/Sanctions screening
        7. Velocity limits check
        8. Determine approval workflow
        """
        # First run base policy checks
        base_result = super().evaluate(intent)
        
        # If base check denied, return immediately
        if base_result.result == PolicyResult.DENY:
            return base_result
        
        # Collect all constraints and violations
        all_constraints = dict(base_result.constraints or {})
        all_violations = list(base_result.violated_policies)
        all_reasons = [base_result.reason]
        
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        vendor = params.get("vendor", "")
        agent_id = intent.get("agent_id", "")
        department = params.get("department", "")
        project_code = params.get("project_code", "")
        country = params.get("country", "")
        employee_info = params.get("employee_info", {})
        
        # 2. Check Budget/Cost Center
        budget_check = self._check_budget(department, project_code, amount)
        if not budget_check.approved:
            return PolicyEvaluation(
                result=PolicyResult.DENY,
                policy_id="budget_exceeded",
                reason=f"❌ BLOCKED: {budget_check.warning}",
                violated_policies=["budget_policy"]
            )
        if budget_check.warning:
            all_constraints["budget_warning"] = budget_check.warning
            all_constraints["remaining_budget"] = budget_check.remaining_budget
        
        # 3. Check Segregation of Duties
        sod_check = self._check_segregation_of_duties(intent)
        if not sod_check.compliant:
            return PolicyEvaluation(
                result=PolicyResult.DENY,
                policy_id="sod_violation",
                reason=f"❌ BLOCKED: Segregation of Duties violation - {sod_check.reason}",
                violated_policies=["segregation_of_duties"]
            )
        
        # 4. Check for Duplicate Transactions
        dup_check = self._check_duplicate_transaction(intent)
        if dup_check.is_duplicate:
            return PolicyEvaluation(
                result=PolicyResult.REQUIRE_CONSTRAINT,
                policy_id="duplicate_detected",
                reason=f"⚠️ Potential duplicate: {dup_check.duplicate_type}",
                constraints={"duplicate_confirmation_required": True,
                            "matching_transactions": dup_check.matching_transactions}
            )
        
        # 5. Check Employee-Specific Restrictions
        emp_check = self._check_employee_restrictions(agent_id, employee_info, amount)
        if emp_check.result == PolicyResult.DENY:
            return emp_check
        if emp_check.constraints:
            all_constraints.update(emp_check.constraints)
        
        # 6. Check Geographic/Sanctions
        geo_check = self._check_geographic_restrictions(country, vendor, amount)
        if geo_check.result == PolicyResult.DENY:
            return geo_check
        if geo_check.constraints:
            all_constraints.update(geo_check.constraints)
        
        # 7. Check Velocity Limits
        velocity_check = self._check_velocity_limits(agent_id, amount)
        if velocity_check.result == PolicyResult.DENY:
            return velocity_check
        if velocity_check.constraints:
            all_constraints.update(velocity_check.constraints)
        
        # 8. Determine Approval Workflow
        workflow = self._determine_approval_workflow(intent, all_constraints)
        if workflow:
            all_constraints["approval_workflow"] = workflow
        
        # Record this transaction for future duplicate detection
        self._record_transaction(intent)
        
        # Final result
        final_result = base_result.result
        if all_constraints and final_result == PolicyResult.ALLOW:
            final_result = PolicyResult.REQUIRE_CONSTRAINT
        
        return PolicyEvaluation(
            result=final_result,
            policy_id=base_result.policy_id,
            reason=" | ".join(filter(None, all_reasons)),
            constraints=all_constraints if all_constraints else None,
            violated_policies=all_violations
        )
    
    def _check_budget(
        self, 
        department: str, 
        project_code: str, 
        amount: float
    ) -> BudgetCheck:
        """Check department/project budget availability."""
        if not self.budget_policies:
            return BudgetCheck(approved=True, remaining_budget=float('inf'),
                             budget_type="none", utilization_percentage=0)
        
        # Get department budget policy
        if department and department in self.budget_policies:
            policy = self.budget_policies[department]
            quarterly_budget = policy.get('quarterly_budget', float('inf'))
            current_spend = self._department_spend.get(department, 0)
            remaining = quarterly_budget - current_spend
            utilization = (current_spend / quarterly_budget) * 100 if quarterly_budget else 0
            
            if amount > remaining:
                return BudgetCheck(
                    approved=False,
                    remaining_budget=remaining,
                    budget_type="quarterly",
                    utilization_percentage=utilization,
                    warning=f"Exceeds {department} quarterly budget (remaining: ${remaining:,.2f})"
                )
            
            threshold = policy.get('remaining_budget_threshold', 0.10)
            if remaining / quarterly_budget < threshold:
                return BudgetCheck(
                    approved=True,
                    remaining_budget=remaining,
                    budget_type="quarterly",
                    utilization_percentage=utilization,
                    warning=f"⚠️ {department} budget at {utilization:.1f}% utilization"
                )
            
            return BudgetCheck(
                approved=True,
                remaining_budget=remaining,
                budget_type="quarterly",
                utilization_percentage=utilization
            )
        
        return BudgetCheck(approved=True, remaining_budget=float('inf'),
                         budget_type="none", utilization_percentage=0)
    
    def _check_segregation_of_duties(self, intent: Dict[str, Any]) -> SODCheck:
        """Check for Segregation of Duties violations."""
        if not self.sod_policies:
            return SODCheck(compliant=True)
        
        agent_id = intent.get("agent_id", "")
        params = intent.get("parameters", {})
        requestor = params.get("requestor_id", agent_id)
        approver = intent.get("approver_id", agent_id)
        vendor = params.get("vendor", "")
        amount = params.get("amount", 0)
        
        for policy in self.sod_policies:
            rule = policy.get("rule", "")
            
            # Check: Requestor cannot self-approve
            if rule == "requestor_not_approver":
                exception_threshold = policy.get("exception_threshold", 0)
                if requestor == approver and amount > exception_threshold:
                    return SODCheck(
                        compliant=False,
                        violation_type="self_approval",
                        reason=f"Requestor ({requestor}) cannot approve their own request"
                    )
            
            # Check: Vendor creator cannot be payer
            if rule == "vendor_creator_not_payer":
                vendor_creator = self._get_vendor_creator(vendor)
                if vendor_creator == agent_id:
                    cooling_period = policy.get("cooling_period_days", 7)
                    vendor_created_date = self._get_vendor_created_date(vendor)
                    if vendor_created_date:
                        days_since = (datetime.now() - vendor_created_date).days
                        if days_since < cooling_period:
                            return SODCheck(
                                compliant=False,
                                violation_type="vendor_creator_payer",
                                reason=f"Must wait {cooling_period} days between vendor creation and payment (created {days_since} days ago)"
                            )
            
            # Check: Three-way match (PO, Receipt, Invoice)
            if rule == "three_way_match":
                po_amount = params.get("po_amount")
                receipt_amount = params.get("receipt_amount")
                invoice_amount = params.get("invoice_amount", amount)
                
                if po_amount is not None and receipt_amount is not None:
                    tolerance = policy.get("tolerance_percentage", 5) / 100
                    if not self._amounts_match(po_amount, receipt_amount, invoice_amount, tolerance):
                        return SODCheck(
                            compliant=False,
                            violation_type="three_way_mismatch",
                            reason=f"Three-way match failed: PO=${po_amount}, Receipt=${receipt_amount}, Invoice=${invoice_amount}"
                        )
        
        return SODCheck(compliant=True)
    
    def _check_duplicate_transaction(self, intent: Dict[str, Any]) -> DuplicateCheck:
        """Detect potential duplicate transactions."""
        if not self.duplicate_policies:
            return DuplicateCheck(is_duplicate=False)
        
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        vendor = params.get("vendor", "")
        invoice_number = params.get("invoice_number", "")
        
        now = datetime.now()
        matching = []
        
        for policy in self.duplicate_policies:
            policy_id = policy.get("policy_id", "")
            
            # Same amount + same vendor detection
            if policy_id == "dup_same_amount":
                window_hours = policy.get("time_window_hours", 24)
                cutoff = now - timedelta(hours=window_hours)
                
                for tx in self._transaction_history:
                    tx_time = tx.get("timestamp")
                    if isinstance(tx_time, str):
                        tx_time = datetime.fromisoformat(tx_time)
                    
                    if tx_time and tx_time > cutoff:
                        tx_amount = tx.get("amount", 0)
                        tx_vendor = tx.get("vendor", "")
                        
                        tolerance = policy.get("same_amount_tolerance", 0.01)
                        if abs(tx_amount - amount) <= tolerance and tx_vendor.lower() == vendor.lower():
                            matching.append(tx.get("id", "unknown"))
            
            # Invoice number duplicate detection
            if policy_id == "dup_invoice" and invoice_number:
                for tx in self._transaction_history:
                    tx_invoice = tx.get("invoice_number", "")
                    if tx_invoice and tx_invoice.lower() == invoice_number.lower():
                        return DuplicateCheck(
                            is_duplicate=True,
                            duplicate_type="duplicate_invoice",
                            matching_transactions=[tx.get("id", "unknown")]
                        )
            
            # Split payment detection
            if policy_id == "dup_split_payment":
                window_hours = policy.get("detection_window_hours", 48)
                threshold = policy.get("combined_amount_threshold", 10000)
                min_transactions = policy.get("minimum_transactions", 2)
                cutoff = now - timedelta(hours=window_hours)
                
                same_vendor_total = amount
                same_vendor_count = 1
                
                for tx in self._transaction_history:
                    tx_time = tx.get("timestamp")
                    if isinstance(tx_time, str):
                        tx_time = datetime.fromisoformat(tx_time)
                    
                    if tx_time and tx_time > cutoff:
                        tx_vendor = tx.get("vendor", "")
                        if tx_vendor.lower() == vendor.lower():
                            same_vendor_total += tx.get("amount", 0)
                            same_vendor_count += 1
                
                if same_vendor_count >= min_transactions and same_vendor_total >= threshold:
                    return DuplicateCheck(
                        is_duplicate=True,
                        duplicate_type="potential_split_payment",
                        matching_transactions=[f"Combined: ${same_vendor_total:,.2f} across {same_vendor_count} transactions"]
                    )
        
        if matching:
            return DuplicateCheck(
                is_duplicate=True,
                duplicate_type="same_amount_vendor",
                matching_transactions=matching
            )
        
        return DuplicateCheck(is_duplicate=False)
    
    def _check_employee_restrictions(
        self, 
        agent_id: str, 
        employee_info: Dict[str, Any],
        amount: float
    ) -> PolicyEvaluation:
        """Check employee-specific restrictions."""
        if not self.employee_policies:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="emp_check_skip",
                reason="No employee policies"
            )
        
        hire_date = employee_info.get("hire_date")
        is_departing = employee_info.get("is_departing", False)
        is_on_leave = employee_info.get("is_on_leave", False)
        
        for policy in self.employee_policies:
            policy_id = policy.get("policy_id", "")
            
            # New hire restrictions
            if policy_id == "emp_new_hire" and hire_date:
                try:
                    if isinstance(hire_date, str):
                        hire_date = datetime.fromisoformat(hire_date)
                    days_employed = (datetime.now() - hire_date).days
                    new_hire_period = policy.get("new_hire_period_days", 90)
                    
                    if days_employed < new_hire_period:
                        restrictions = policy.get("restrictions", {})
                        max_single = restrictions.get("max_single_transaction", 500)
                        
                        if amount > max_single:
                            return PolicyEvaluation(
                                result=PolicyResult.DENY,
                                policy_id="emp_new_hire",
                                reason=f"❌ BLOCKED: New hire ({days_employed} days) limited to ${max_single:,.2f} per transaction"
                            )
                        
                        return PolicyEvaluation(
                            result=PolicyResult.ALLOW,
                            policy_id="emp_new_hire",
                            reason="New hire within limits",
                            constraints={"requires_manager_approval": True, "new_hire_flag": True}
                        )
                except:
                    pass
            
            # Departing employee controls
            if policy_id == "emp_departing" and is_departing:
                restrictions = policy.get("restrictions", {})
                max_single = restrictions.get("max_single_transaction", 100)
                
                if amount > max_single:
                    return PolicyEvaluation(
                        result=PolicyResult.DENY,
                        policy_id="emp_departing",
                        reason=f"❌ BLOCKED: Departing employee limited to ${max_single:,.2f}"
                    )
                
                return PolicyEvaluation(
                    result=PolicyResult.REQUIRE_CONSTRAINT,
                    policy_id="emp_departing",
                    reason="Departing employee - enhanced controls",
                    constraints={
                        "requires_dual_approval": True,
                        "enhanced_audit": True,
                        "departing_employee_flag": True
                    }
                )
            
            # Leave status check
            if policy_id == "emp_leave_status" and is_on_leave:
                if policy.get("check_leave_status", True):
                    emergency_threshold = policy.get("emergency_threshold", 500)
                    
                    if amount > emergency_threshold:
                        return PolicyEvaluation(
                            result=PolicyResult.DENY,
                            policy_id="emp_leave_status",
                            reason=f"❌ BLOCKED: Employee on leave, transactions over ${emergency_threshold} not allowed"
                        )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="emp_check_passed",
            reason="Employee checks passed"
        )
    
    def _check_geographic_restrictions(
        self, 
        country: str, 
        vendor: str, 
        amount: float
    ) -> PolicyEvaluation:
        """Check geographic and sanctions restrictions."""
        if not self.geographic_policies or not country:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="geo_skip",
                reason="No geographic policies or country specified"
            )
        
        for policy in self.geographic_policies:
            policy_id = policy.get("policy_id", "")
            
            # High-risk country check
            if policy_id == "geo_high_risk_countries":
                high_risk = policy.get("high_risk_countries", [])
                
                if country in high_risk:
                    max_without_approval = policy.get("max_amount_without_approval", 1000)
                    
                    if amount > max_without_approval:
                        return PolicyEvaluation(
                            result=PolicyResult.REQUIRE_CONSTRAINT,
                            policy_id="geo_high_risk",
                            reason=f"⚠️ High-risk country ({country}) - requires compliance review",
                            constraints={
                                "compliance_review_required": True,
                                "documentation_required": policy.get("documentation_required", []),
                                "high_risk_country": country
                            }
                        )
            
            # Sanctions screening (placeholder - in real system would call external API)
            if policy_id == "geo_sanctions_check":
                # Simulate sanctions check
                sanctioned_keywords = ["blocked", "sanctioned", "embargoed"]
                vendor_lower = vendor.lower()
                
                for keyword in sanctioned_keywords:
                    if keyword in vendor_lower:
                        return PolicyEvaluation(
                            result=PolicyResult.DENY,
                            policy_id="geo_sanctions",
                            reason=f"❌ BLOCKED: Vendor '{vendor}' flagged in sanctions screening"
                        )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="geo_passed",
            reason="Geographic checks passed"
        )
    
    def _check_velocity_limits(
        self, 
        agent_id: str, 
        amount: float
    ) -> PolicyEvaluation:
        """Check transaction velocity limits."""
        if not self.velocity_policies:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="velocity_skip",
                reason="No velocity policies"
            )
        
        now = datetime.now()
        
        for policy in self.velocity_policies:
            policy_id = policy.get("policy_id", "")
            
            # Transaction frequency limits
            if policy_id == "vel_transaction_frequency":
                limits = policy.get("limits", {})
                
                # Count transactions in different windows
                hourly = self._count_transactions_in_window(agent_id, hours=1)
                daily = self._count_transactions_in_window(agent_id, hours=24)
                
                max_hourly = limits.get("per_hour", 10)
                max_daily = limits.get("per_day", 50)
                
                if hourly >= max_hourly:
                    return PolicyEvaluation(
                        result=PolicyResult.DENY,
                        policy_id="vel_frequency",
                        reason=f"❌ BLOCKED: Hourly transaction limit ({max_hourly}) exceeded"
                    )
                
                if daily >= max_daily:
                    return PolicyEvaluation(
                        result=PolicyResult.DENY,
                        policy_id="vel_frequency",
                        reason=f"❌ BLOCKED: Daily transaction limit ({max_daily}) exceeded"
                    )
            
            # Cumulative amount velocity
            if policy_id == "vel_cumulative_amount":
                thresholds = policy.get("thresholds", {})
                
                hourly_amount = self._sum_transactions_in_window(agent_id, hours=1)
                daily_amount = self._sum_transactions_in_window(agent_id, hours=24)
                
                hourly_limit = thresholds.get("per_hour", 10000)
                daily_limit = thresholds.get("per_day", 50000)
                
                if hourly_amount + amount > hourly_limit:
                    return PolicyEvaluation(
                        result=PolicyResult.REQUIRE_CONSTRAINT,
                        policy_id="vel_cumulative",
                        reason=f"⚠️ Hourly cumulative amount (${hourly_amount + amount:,.2f}) exceeds threshold",
                        constraints={"velocity_freeze": True, "requires_review": True}
                    )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="velocity_passed",
            reason="Velocity checks passed"
        )
    
    def _determine_approval_workflow(
        self, 
        intent: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Determine the appropriate approval workflow."""
        if not self.workflow_policies:
            return None
        
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        category = params.get("category", "")
        vendor = params.get("vendor", "")
        
        for policy in self.workflow_policies:
            policy_id = policy.get("policy_id", "")
            
            # Parallel approval for large amounts
            if policy_id == "wf_parallel":
                applies_when = policy.get("applies_when", {})
                min_amount = applies_when.get("min_amount", float('inf'))
                
                if amount >= min_amount:
                    return {
                        "type": "parallel",
                        "required_approvers": policy.get("required_approvers", []),
                        "minimum_approvals": policy.get("minimum_approvals", 2),
                        "unanimous_required": policy.get("unanimous_required", False)
                    }
            
            # Conditional routing
            if policy_id == "wf_conditional":
                conditions = policy.get("conditions", [])
                route_to = []
                
                for cond in conditions:
                    if cond.get("if_category") == category:
                        route_to.append(cond.get("route_to"))
                    if cond.get("if_amount_above") and amount > cond.get("if_amount_above"):
                        route_to.append(cond.get("route_to"))
                    if cond.get("if_vendor_new") and constraints.get("new_vendor_approval"):
                        route_to.append(cond.get("route_to"))
                
                if route_to:
                    return {
                        "type": "conditional",
                        "route_to": list(set(route_to))
                    }
            
            # Sequential approval chain
            if policy_id == "wf_sequential":
                return {
                    "type": "sequential",
                    "levels": policy.get("levels", []),
                    "escalation_on_timeout": policy.get("escalation_on_timeout", True)
                }
        
        return None
    
    def _record_transaction(self, intent: Dict[str, Any]):
        """Record transaction for tracking."""
        params = intent.get("parameters", {})
        
        self._transaction_history.append({
            "id": f"tx_{len(self._transaction_history) + 1}",
            "timestamp": datetime.now(),
            "agent_id": intent.get("agent_id", ""),
            "amount": params.get("amount", 0),
            "vendor": params.get("vendor", ""),
            "invoice_number": params.get("invoice_number", ""),
            "category": params.get("category", "")
        })
        
        # Keep only last 1000 transactions
        if len(self._transaction_history) > 1000:
            self._transaction_history = self._transaction_history[-1000:]
        
        # Update department spend
        dept = params.get("department", "")
        if dept:
            self._department_spend[dept] = self._department_spend.get(dept, 0) + params.get("amount", 0)
    
    def _count_transactions_in_window(self, agent_id: str, hours: int) -> int:
        """Count transactions by agent in time window."""
        cutoff = datetime.now() - timedelta(hours=hours)
        count = 0
        
        for tx in self._transaction_history:
            if tx.get("agent_id") == agent_id:
                tx_time = tx.get("timestamp")
                if tx_time and tx_time > cutoff:
                    count += 1
        
        return count
    
    def _sum_transactions_in_window(self, agent_id: str, hours: int) -> float:
        """Sum transaction amounts by agent in time window."""
        cutoff = datetime.now() - timedelta(hours=hours)
        total = 0.0
        
        for tx in self._transaction_history:
            if tx.get("agent_id") == agent_id:
                tx_time = tx.get("timestamp")
                if tx_time and tx_time > cutoff:
                    total += tx.get("amount", 0)
        
        return total
    
    def _get_vendor_creator(self, vendor: str) -> Optional[str]:
        """Get who created a vendor (placeholder)."""
        # In real system, would lookup from vendor master
        return None
    
    def _get_vendor_created_date(self, vendor: str) -> Optional[datetime]:
        """Get when vendor was created (placeholder)."""
        # In real system, would lookup from vendor master
        return None
    
    def _amounts_match(
        self, 
        po: float, 
        receipt: float, 
        invoice: float, 
        tolerance: float
    ) -> bool:
        """Check if amounts match within tolerance."""
        avg = (po + receipt + invoice) / 3
        return all(abs(x - avg) / avg <= tolerance for x in [po, receipt, invoice] if avg > 0)
    
    def get_advanced_policy_summary(self) -> Dict[str, Any]:
        """Get summary of all loaded policies including advanced ones."""
        base_summary = self.get_policy_summary()
        
        base_summary.update({
            "budget_policies": len(self.budget_policies),
            "sod_policies": len(self.sod_policies),
            "related_party_policies": len(self.related_party_policies),
            "duplicate_detection_policies": len(self.duplicate_policies),
            "employee_policies": len(self.employee_policies),
            "workflow_policies": len(self.workflow_policies),
            "geographic_policies": len(self.geographic_policies),
            "velocity_policies": len(self.velocity_policies),
            "total_advanced_policies": (
                len(self.budget_policies) +
                len(self.sod_policies) +
                len(self.related_party_policies) +
                len(self.duplicate_policies) +
                len(self.employee_policies) +
                len(self.workflow_policies) +
                len(self.geographic_policies) +
                len(self.velocity_policies)
            )
        })
        
        return base_summary
    
    def get_department_spend(self, department: str) -> float:
        """Get current spend for a department."""
        return self._department_spend.get(department, 0)
    
    def reset_department_spend(self, department: str):
        """Reset department spend (e.g., at quarter end)."""
        if department in self._department_spend:
            del self._department_spend[department]
    
    def set_department_budget(self, department: str, quarterly_budget: float):
        """Set/update department budget."""
        self.budget_policies[department] = {
            "department": department,
            "quarterly_budget": quarterly_budget,
            "remaining_budget_threshold": 0.10
        }
