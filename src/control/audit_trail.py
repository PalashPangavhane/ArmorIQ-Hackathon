"""
Audit Trail System

Comprehensive traceability from agent plans to executed actions.
This is a KEY requirement for the hackathon:
"Traceability from agent plans to executed actions"
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class AuditEventType(Enum):
    """Types of auditable events."""
    AGENT_REASONING = "agent_reasoning"       # Agent analyzed and reasoned
    INTENT_PROPOSED = "intent_proposed"       # Agent proposed an intent
    VALIDATION_CHECK = "validation_check"     # Intent validated
    POLICY_EVALUATION = "policy_evaluation"   # Policy rules checked
    RISK_ASSESSMENT = "risk_assessment"       # Risk signal evaluated
    DECISION_MADE = "decision_made"           # Gateway made decision
    DELEGATION_CHECK = "delegation_check"     # Delegation authority checked
    EXECUTION_ATTEMPT = "execution_attempt"   # MCP execution attempted
    EXECUTION_BLOCKED = "execution_blocked"   # Execution was blocked
    EXECUTION_SUCCESS = "execution_success"   # Execution completed


@dataclass
class AuditEvent:
    """A single auditable event in the system."""
    event_id: str
    event_type: AuditEventType
    timestamp: str
    agent_id: str
    session_id: str
    details: Dict[str, Any]
    parent_event_id: Optional[str] = None  # For tracing event chains
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "details": self.details,
            "parent_event_id": self.parent_event_id
        }


@dataclass
class AuditTrace:
    """Complete trace from agent reasoning to execution."""
    trace_id: str
    session_id: str
    started_at: str
    completed_at: Optional[str] = None
    request: Dict[str, Any] = field(default_factory=dict)
    events: List[AuditEvent] = field(default_factory=list)
    outcome: str = "pending"  # pending, approved, blocked, executed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "request": self.request,
            "events": [e.to_dict() for e in self.events],
            "outcome": self.outcome
        }


class AuditTrailSystem:
    """
    Centralized audit trail for the entire system.
    
    Tracks the complete flow:
    
    REQUEST → AGENT REASONING → INTENT → POLICY CHECK → 
    → GATEWAY DECISION → MCP EXECUTION → RESULT
    
    Every step is logged with full context for traceability.
    """
    
    def __init__(self):
        self._events: List[AuditEvent] = []
        self._traces: Dict[str, AuditTrace] = {}
        self._event_counter = 0
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        self._event_counter += 1
        return f"evt_{self._event_counter:06d}"
    
    def start_trace(
        self,
        session_id: str,
        request: Dict[str, Any]
    ) -> str:
        """Start a new audit trace for a request."""
        import uuid
        trace_id = str(uuid.uuid4())
        
        trace = AuditTrace(
            trace_id=trace_id,
            session_id=session_id,
            started_at=datetime.utcnow().isoformat(),
            request=request
        )
        self._traces[trace_id] = trace
        
        return trace_id
    
    def log_event(
        self,
        trace_id: str,
        event_type: AuditEventType,
        agent_id: str,
        details: Dict[str, Any],
        parent_event_id: Optional[str] = None
    ) -> str:
        """Log an audit event."""
        event_id = self._generate_event_id()
        
        if trace_id not in self._traces:
            raise ValueError(f"Unknown trace_id: {trace_id}")
        
        trace = self._traces[trace_id]
        
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            agent_id=agent_id,
            session_id=trace.session_id,
            details=details,
            parent_event_id=parent_event_id
        )
        
        trace.events.append(event)
        self._events.append(event)
        
        return event_id
    
    def complete_trace(
        self,
        trace_id: str,
        outcome: str
    ):
        """Mark a trace as complete."""
        if trace_id in self._traces:
            trace = self._traces[trace_id]
            trace.completed_at = datetime.utcnow().isoformat()
            trace.outcome = outcome
    
    def get_trace(self, trace_id: str) -> Optional[AuditTrace]:
        """Get a specific trace."""
        return self._traces.get(trace_id)
    
    def get_all_traces(self) -> List[Dict[str, Any]]:
        """Get all traces."""
        return [t.to_dict() for t in self._traces.values()]
    
    def get_blocked_traces(self) -> List[Dict[str, Any]]:
        """Get all traces that were blocked."""
        return [
            t.to_dict() for t in self._traces.values()
            if t.outcome == "blocked"
        ]
    
    def print_trace(self, trace_id: str):
        """Print a formatted trace for debugging."""
        trace = self._traces.get(trace_id)
        if not trace:
            print(f"Trace {trace_id} not found")
            return
        
        print("\n" + "="*70)
        print(f"📋 AUDIT TRACE: {trace_id[:8]}...")
        print("="*70)
        print(f"Session: {trace.session_id}")
        print(f"Started: {trace.started_at}")
        print(f"Completed: {trace.completed_at or 'In Progress'}")
        print(f"Outcome: {trace.outcome.upper()}")
        print(f"\nRequest: {json.dumps(trace.request, indent=2)}")
        
        print(f"\n{'─'*70}")
        print("EVENT TIMELINE:")
        print(f"{'─'*70}")
        
        for i, event in enumerate(trace.events, 1):
            icon = self._get_event_icon(event.event_type)
            print(f"\n{i}. {icon} {event.event_type.value.upper()}")
            print(f"   Time: {event.timestamp}")
            print(f"   Agent: {event.agent_id}")
            if event.parent_event_id:
                print(f"   Follows: {event.parent_event_id}")
            
            # Print key details
            for key, value in event.details.items():
                if isinstance(value, dict):
                    print(f"   {key}: {json.dumps(value, indent=6)}")
                else:
                    print(f"   {key}: {value}")
        
        print(f"\n{'='*70}\n")
    
    def _get_event_icon(self, event_type: AuditEventType) -> str:
        """Get icon for event type."""
        icons = {
            AuditEventType.AGENT_REASONING: "🧠",
            AuditEventType.INTENT_PROPOSED: "📝",
            AuditEventType.VALIDATION_CHECK: "✅",
            AuditEventType.POLICY_EVALUATION: "📋",
            AuditEventType.RISK_ASSESSMENT: "⚠️",
            AuditEventType.DECISION_MADE: "⚖️",
            AuditEventType.DELEGATION_CHECK: "🔑",
            AuditEventType.EXECUTION_ATTEMPT: "▶️",
            AuditEventType.EXECUTION_BLOCKED: "🚫",
            AuditEventType.EXECUTION_SUCCESS: "✅",
        }
        return icons.get(event_type, "•")
    
    def print_summary(self):
        """Print summary of all traces."""
        print("\n" + "="*70)
        print("📊 AUDIT TRAIL SUMMARY")
        print("="*70)
        
        total = len(self._traces)
        blocked = len([t for t in self._traces.values() if t.outcome == "blocked"])
        executed = len([t for t in self._traces.values() if t.outcome == "executed"])
        approved = len([t for t in self._traces.values() if t.outcome == "approved"])
        
        print(f"\nTotal Traces: {total}")
        print(f"  ✅ Executed: {executed}")
        print(f"  ☑️ Approved: {approved}")
        print(f"  🚫 Blocked: {blocked}")
        
        if blocked > 0:
            print(f"\n{'─'*70}")
            print("BLOCKED REQUESTS:")
            for trace in self._traces.values():
                if trace.outcome == "blocked":
                    # Find the blocking reason
                    for event in reversed(trace.events):
                        if event.event_type in [AuditEventType.EXECUTION_BLOCKED, AuditEventType.DECISION_MADE]:
                            reason = event.details.get("reason", "Unknown")
                            print(f"  • {trace.trace_id[:8]}... - {reason}")
                            break
        
        print("="*70 + "\n")
    
    def export_json(self, filepath: str):
        """Export audit trail to JSON file."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_events": len(self._events),
            "total_traces": len(self._traces),
            "traces": [t.to_dict() for t in self._traces.values()]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Audit trail exported to {filepath}")


# Global audit system instance
_audit_system: Optional[AuditTrailSystem] = None


def get_audit_system() -> AuditTrailSystem:
    """Get the global audit system instance."""
    global _audit_system
    if _audit_system is None:
        _audit_system = AuditTrailSystem()
    return _audit_system
