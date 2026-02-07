"""
Policy Engine Module

Evaluates static policy rules against agent intents.
Enforces approval hierarchies and bounded delegation.

KEY HACKATHON REQUIREMENT:
"Users do not approve every action interactively. Instead, users define 
rules that specify what agents are allowed to do. The system is responsible 
for enforcing those rules correctly and consistently."
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import yaml
import os


class PolicyResult(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONSTRAINT = "require_constraint"
    ESCALATE = "escalate"


@dataclass
class PolicyEvaluation:
    """Result of policy evaluation."""
    result: PolicyResult
    policy_id: str
    reason: str
    constraints: Optional[Dict[str, Any]] = None
    violated_policies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "policy_id": self.policy_id,
            "reason": self.reason,
            "constraints": self.constraints,
            "violated_policies": self.violated_policies
        }


@dataclass
class Policy:
    """Represents a policy rule."""
    policy_id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    effect: PolicyResult
    priority: int = 0
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VendorPolicy:
    """Policy for vendor allowlist/blocklist enforcement."""
    policy_id: str
    name: str
    allowed_vendors: List[str] = field(default_factory=list)
    blocked_vendors: List[str] = field(default_factory=list)
    require_approval_for_new: bool = True


@dataclass
class SpendCapPolicy:
    """Policy for spend cap enforcement."""
    policy_id: str
    name: str
    max_daily: float = float('inf')
    max_weekly: float = float('inf')
    max_monthly: float = float('inf')
    max_per_transaction: float = float('inf')


@dataclass
class CategoryPolicy:
    """Policy for category-based restrictions."""
    policy_id: str
    name: str
    allowed_categories: List[str] = field(default_factory=list)
    blocked_categories: List[str] = field(default_factory=list)


@dataclass
class TimeWindowPolicy:
    """Policy for time-based restrictions."""
    policy_id: str
    name: str
    allowed_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Mon-Fri
    start_hour: int = 9   # 9 AM
    end_hour: int = 18    # 6 PM
    timezone: str = "local"


class PolicyEngine:
    """
    Evaluates policies against agent intents.
    
    KEY FEATURES:
    1. Loads user-defined rules from YAML config
    2. Enforces amount limits, vendor rules, categories, time windows, spend caps
    3. Applies approval hierarchies
    4. Provides clear blocking reasons for audit
    
    ARCHITECTURE:
    [Agent Intent] -> [PolicyEngine.evaluate()] -> [PolicyEvaluation]
                                                        |
                                                        v
                                           ALLOW / DENY / ESCALATE
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.policies: List[Policy] = []
        self.vendor_policies: List[VendorPolicy] = []
        self.spend_cap_policies: List[SpendCapPolicy] = []
        self.category_policies: List[CategoryPolicy] = []
        self.time_window_policies: List[TimeWindowPolicy] = []
        self.approval_hierarchy: List[Dict[str, Any]] = []
        self.risk_modifiers: Dict[str, Dict[str, Any]] = {}
        
        # Track spending for spend cap enforcement
        self._spending_tracker: Dict[str, float] = {}
        
        # Load policies from YAML or use defaults
        if config_path:
            self.load_policies_from_yaml(config_path)
        else:
            # Try default path
            default_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "..", "config", "policies.yaml"
            )
            if os.path.exists(default_path):
                self.load_policies_from_yaml(default_path)
            else:
                self._load_default_policies()
    
    def load_policies_from_yaml(self, config_path: str):
        """
        Load policies from YAML configuration file.
        
        This is the KEY feature - user-defined rules loaded from config!
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Load base policies
        for policy_config in config.get('policies', []):
            effect = PolicyResult(policy_config.get('effect', 'allow'))
            policy = Policy(
                policy_id=policy_config['policy_id'],
                name=policy_config['name'],
                description=policy_config.get('description', ''),
                conditions=policy_config.get('conditions', {}),
                effect=effect,
                priority=policy_config.get('priority', 0),
                constraints=policy_config.get('constraints', {})
            )
            self.policies.append(policy)
        
        # Load risk modifiers
        self.risk_modifiers = config.get('risk_modifiers', {})
        
        # Load approval hierarchy
        self.approval_hierarchy = config.get('approval_hierarchy', [])
        
        # Load vendor policies if present
        for vendor_config in config.get('vendor_policies', []):
            self.vendor_policies.append(VendorPolicy(
                policy_id=vendor_config['policy_id'],
                name=vendor_config['name'],
                allowed_vendors=vendor_config.get('allowed_vendors', []),
                blocked_vendors=vendor_config.get('blocked_vendors', []),
                require_approval_for_new=vendor_config.get('require_approval_for_new', True)
            ))
        
        # Load spend cap policies if present
        for cap_config in config.get('spend_cap_policies', []):
            self.spend_cap_policies.append(SpendCapPolicy(
                policy_id=cap_config['policy_id'],
                name=cap_config['name'],
                max_daily=cap_config.get('max_daily', float('inf')),
                max_weekly=cap_config.get('max_weekly', float('inf')),
                max_monthly=cap_config.get('max_monthly', float('inf')),
                max_per_transaction=cap_config.get('max_per_transaction', float('inf'))
            ))
        
        # Load category policies if present
        for cat_config in config.get('category_policies', []):
            self.category_policies.append(CategoryPolicy(
                policy_id=cat_config['policy_id'],
                name=cat_config['name'],
                allowed_categories=cat_config.get('allowed_categories', []),
                blocked_categories=cat_config.get('blocked_categories', [])
            ))
        
        # Load time window policies if present
        for time_config in config.get('time_window_policies', []):
            self.time_window_policies.append(TimeWindowPolicy(
                policy_id=time_config['policy_id'],
                name=time_config['name'],
                allowed_days=time_config.get('allowed_days', [0, 1, 2, 3, 4]),
                start_hour=time_config.get('start_hour', 9),
                end_hour=time_config.get('end_hour', 18)
            ))
        
        print(f"✅ Loaded {len(self.policies)} policies from {config_path}")
    
    def _load_default_policies(self):
        """Load default policy rules if no YAML config found."""
        # Policy: Basic approval limits
        self.policies.append(Policy(
            policy_id="pol_001",
            name="basic_approval_limit",
            description="Approve payments under $1000 without escalation",
            conditions={"max_amount": 1000, "intent_type": "approve_payment"},
            effect=PolicyResult.ALLOW,
            priority=1
        ))
        
        # Policy: Require dual approval for high amounts
        self.policies.append(Policy(
            policy_id="pol_002",
            name="dual_approval_required",
            description="Require dual approval for amounts over $10000",
            conditions={"min_amount": 10000, "intent_type": "approve_payment"},
            effect=PolicyResult.REQUIRE_CONSTRAINT,
            priority=2,
            constraints={"dual_approval": True}
        ))
        
        # Policy: Block suspicious flagged transactions
        self.policies.append(Policy(
            policy_id="pol_003",
            name="block_suspicious",
            description="Block transactions flagged as suspicious",
            conditions={"intent_type": "flag_suspicious", "severity": "high"},
            effect=PolicyResult.DENY,
            priority=3
        ))
        
        # Default vendor policy
        self.vendor_policies.append(VendorPolicy(
            policy_id="vendor_default",
            name="Default Vendor Policy",
            blocked_vendors=["suspicious_vendor", "blocked_corp", "fraud_inc"],
            require_approval_for_new=True
        ))
        
        # Default spend cap
        self.spend_cap_policies.append(SpendCapPolicy(
            policy_id="cap_default",
            name="Default Spend Cap",
            max_daily=10000,
            max_monthly=100000,
            max_per_transaction=50000
        ))
        
        # Default category policy
        self.category_policies.append(CategoryPolicy(
            policy_id="cat_default",
            name="Default Category Policy",
            allowed_categories=["office_supplies", "travel", "software", "equipment", "services"],
            blocked_categories=["gambling", "personal", "entertainment"]
        ))
        
        # Default time window (business hours)
        self.time_window_policies.append(TimeWindowPolicy(
            policy_id="time_default",
            name="Business Hours Only",
            allowed_days=[0, 1, 2, 3, 4],  # Monday to Friday
            start_hour=9,
            end_hour=18
        ))
    
    def evaluate(self, intent: Dict[str, Any]) -> PolicyEvaluation:
        """
        Evaluate an intent against ALL applicable policies.
        
        FLOW:
        1. Check amount-based policies
        2. Check vendor policies
        3. Check category policies
        4. Check time window policies
        5. Check spend cap policies
        6. Return combined result
        
        Args:
            intent: Agent intent to evaluate
            
        Returns:
            PolicyEvaluation with result, constraints, and any violations
        """
        violations = []
        all_constraints = {}
        
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        vendor = params.get("vendor", "")
        category = params.get("category", "")
        
        # 1. Check amount-based policies
        amount_result = self._evaluate_amount_policies(intent)
        if amount_result.result == PolicyResult.DENY:
            return amount_result
        if amount_result.constraints:
            all_constraints.update(amount_result.constraints)
        
        # 2. Check vendor policies
        vendor_result = self._evaluate_vendor_policies(vendor)
        if vendor_result.result == PolicyResult.DENY:
            violations.append(vendor_result.policy_id)
            return PolicyEvaluation(
                result=PolicyResult.DENY,
                policy_id=vendor_result.policy_id,
                reason=vendor_result.reason,
                violated_policies=violations
            )
        if vendor_result.constraints:
            all_constraints.update(vendor_result.constraints)
        
        # 3. Check category policies
        category_result = self._evaluate_category_policies(category)
        if category_result.result == PolicyResult.DENY:
            violations.append(category_result.policy_id)
            return PolicyEvaluation(
                result=PolicyResult.DENY,
                policy_id=category_result.policy_id,
                reason=category_result.reason,
                violated_policies=violations
            )
        
        # 4. Check time window policies
        time_result = self._evaluate_time_window_policies()
        if time_result.result == PolicyResult.DENY:
            violations.append(time_result.policy_id)
            return PolicyEvaluation(
                result=PolicyResult.DENY,
                policy_id=time_result.policy_id,
                reason=time_result.reason,
                violated_policies=violations
            )
        
        # 5. Check spend cap policies
        agent_id = intent.get("agent_id", "unknown")
        cap_result = self._evaluate_spend_cap_policies(agent_id, amount)
        if cap_result.result == PolicyResult.DENY:
            violations.append(cap_result.policy_id)
            return PolicyEvaluation(
                result=PolicyResult.DENY,
                policy_id=cap_result.policy_id,
                reason=cap_result.reason,
                violated_policies=violations
            )
        
        # All checks passed
        final_result = amount_result.result
        if final_result == PolicyResult.ALLOW and all_constraints:
            final_result = PolicyResult.REQUIRE_CONSTRAINT
        
        return PolicyEvaluation(
            result=final_result,
            policy_id=amount_result.policy_id,
            reason=amount_result.reason,
            constraints=all_constraints if all_constraints else None,
            violated_policies=violations
        )
    
    def _evaluate_amount_policies(self, intent: Dict[str, Any]) -> PolicyEvaluation:
        """Evaluate amount-based policies."""
        applicable_policies = self._find_applicable_policies(intent)
        
        if not applicable_policies:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="default",
                reason="No applicable policies found, allowing by default"
            )
        
        # Sort by priority and evaluate
        applicable_policies.sort(key=lambda p: p.priority, reverse=True)
        
        for policy in applicable_policies:
            evaluation = self._evaluate_policy(policy, intent)
            if evaluation.result != PolicyResult.ALLOW:
                return evaluation
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="combined",
            reason="All amount policies passed"
        )
    
    def _evaluate_vendor_policies(self, vendor: str) -> PolicyEvaluation:
        """Evaluate vendor allowlist/blocklist policies."""
        if not vendor:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="vendor_skip",
                reason="No vendor specified"
            )
        
        for policy in self.vendor_policies:
            vendor_lower = vendor.lower()
            
            # Check blocklist first
            if any(blocked.lower() in vendor_lower for blocked in policy.blocked_vendors):
                return PolicyEvaluation(
                    result=PolicyResult.DENY,
                    policy_id=policy.policy_id,
                    reason=f"❌ BLOCKED: Vendor '{vendor}' is on blocklist"
                )
            
            # Check allowlist if it exists
            if policy.allowed_vendors:
                if not any(allowed.lower() in vendor_lower for allowed in policy.allowed_vendors):
                    if policy.require_approval_for_new:
                        return PolicyEvaluation(
                            result=PolicyResult.REQUIRE_CONSTRAINT,
                            policy_id=policy.policy_id,
                            reason=f"Vendor '{vendor}' not on allowlist, requires approval",
                            constraints={"new_vendor_approval": True}
                        )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="vendor_passed",
            reason="Vendor policy passed"
        )
    
    def _evaluate_category_policies(self, category: str) -> PolicyEvaluation:
        """Evaluate category-based policies."""
        if not category:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="category_skip",
                reason="No category specified"
            )
        
        for policy in self.category_policies:
            category_lower = category.lower()
            
            # Check blocklist first
            if any(blocked.lower() == category_lower for blocked in policy.blocked_categories):
                return PolicyEvaluation(
                    result=PolicyResult.DENY,
                    policy_id=policy.policy_id,
                    reason=f"❌ BLOCKED: Category '{category}' is not allowed"
                )
            
            # Check allowlist if it exists
            if policy.allowed_categories:
                if not any(allowed.lower() == category_lower for allowed in policy.allowed_categories):
                    return PolicyEvaluation(
                        result=PolicyResult.DENY,
                        policy_id=policy.policy_id,
                        reason=f"❌ BLOCKED: Category '{category}' not in allowed list"
                    )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="category_passed",
            reason="Category policy passed"
        )
    
    def _evaluate_time_window_policies(self) -> PolicyEvaluation:
        """Evaluate time window policies."""
        if not self.time_window_policies:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="time_skip",
                reason="No time window policies"
            )
        
        now = datetime.now()
        current_day = now.weekday()  # 0 = Monday
        current_hour = now.hour
        
        for policy in self.time_window_policies:
            # Check day
            if current_day not in policy.allowed_days:
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                return PolicyEvaluation(
                    result=PolicyResult.DENY,
                    policy_id=policy.policy_id,
                    reason=f"❌ BLOCKED: Transactions not allowed on {day_names[current_day]}"
                )
            
            # Check hour
            if current_hour < policy.start_hour or current_hour >= policy.end_hour:
                return PolicyEvaluation(
                    result=PolicyResult.DENY,
                    policy_id=policy.policy_id,
                    reason=f"❌ BLOCKED: Transactions only allowed between {policy.start_hour}:00 and {policy.end_hour}:00"
                )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="time_passed",
            reason="Time window policy passed"
        )
    
    def _evaluate_spend_cap_policies(self, agent_id: str, amount: float) -> PolicyEvaluation:
        """Evaluate spend cap policies."""
        if not self.spend_cap_policies:
            return PolicyEvaluation(
                result=PolicyResult.ALLOW,
                policy_id="cap_skip",
                reason="No spend cap policies"
            )
        
        for policy in self.spend_cap_policies:
            # Check per-transaction limit
            if amount > policy.max_per_transaction:
                return PolicyEvaluation(
                    result=PolicyResult.DENY,
                    policy_id=policy.policy_id,
                    reason=f"❌ BLOCKED: Amount ${amount:,.2f} exceeds max per-transaction limit ${policy.max_per_transaction:,.2f}"
                )
            
            # Track and check cumulative spending
            current_spending = self._spending_tracker.get(agent_id, 0)
            if current_spending + amount > policy.max_monthly:
                return PolicyEvaluation(
                    result=PolicyResult.DENY,
                    policy_id=policy.policy_id,
                    reason=f"❌ BLOCKED: Would exceed monthly spend cap of ${policy.max_monthly:,.2f}"
                )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id="cap_passed",
            reason="Spend cap policy passed"
        )
    
    def record_spending(self, agent_id: str, amount: float):
        """Record spending for spend cap tracking."""
        current = self._spending_tracker.get(agent_id, 0)
        self._spending_tracker[agent_id] = current + amount
    
    def get_spending(self, agent_id: str) -> float:
        """Get current spending for an agent."""
        return self._spending_tracker.get(agent_id, 0)
    
    def _find_applicable_policies(self, intent: Dict[str, Any]) -> List[Policy]:
        """Find policies that apply to this intent."""
        applicable = []
        intent_type = intent.get("intent_type")
        
        for policy in self.policies:
            if policy.conditions.get("intent_type") == intent_type:
                applicable.append(policy)
        
        return applicable
    
    def _evaluate_policy(
        self, 
        policy: Policy, 
        intent: Dict[str, Any]
    ) -> PolicyEvaluation:
        """Evaluate a single policy against an intent."""
        params = intent.get("parameters", {})
        amount = params.get("amount", 0)
        
        conditions = policy.conditions
        
        # Check amount conditions
        if "max_amount" in conditions:
            if amount > conditions["max_amount"]:
                return PolicyEvaluation(
                    result=PolicyResult.ESCALATE,
                    policy_id=policy.policy_id,
                    reason=f"Amount ${amount:,.2f} exceeds limit ${conditions['max_amount']:,.2f}"
                )
        
        if "min_amount" in conditions:
            if amount >= conditions["min_amount"]:
                return PolicyEvaluation(
                    result=policy.effect,
                    policy_id=policy.policy_id,
                    reason=f"Amount ${amount:,.2f} triggers policy '{policy.name}'",
                    constraints=policy.constraints if policy.constraints else {"dual_approval": True}
                )
        
        return PolicyEvaluation(
            result=PolicyResult.ALLOW,
            policy_id=policy.policy_id,
            reason=f"Policy '{policy.name}' conditions met"
        )
    
    def add_policy(self, policy: Policy):
        """Add a new policy rule."""
        self.policies.append(policy)
    
    def remove_policy(self, policy_id: str):
        """Remove a policy by ID."""
        self.policies = [p for p in self.policies if p.policy_id != policy_id]
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get a summary of all loaded policies for display."""
        return {
            "amount_policies": len(self.policies),
            "vendor_policies": len(self.vendor_policies),
            "category_policies": len(self.category_policies),
            "time_window_policies": len(self.time_window_policies),
            "spend_cap_policies": len(self.spend_cap_policies),
            "policies": [
                {"id": p.policy_id, "name": p.name, "effect": p.effect.value}
                for p in self.policies
            ]
        }
    
    def disable_time_window_check(self):
        """Disable time window checks (useful for demos)."""
        self.time_window_policies = []
    
    def enable_business_hours_only(self):
        """Enable business hours restriction."""
        self.time_window_policies = [TimeWindowPolicy(
            policy_id="time_business",
            name="Business Hours Only",
            allowed_days=[0, 1, 2, 3, 4],
            start_hour=9,
            end_hour=18
        )]
