"""
Account MCP Server Module

MCP server responsible for account-related operations
such as balance updates, account creation, and fund allocation.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class AccountOperation(Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    ALLOCATE = "allocate"
    FREEZE = "freeze"
    UNFREEZE = "unfreeze"


@dataclass
class AccountTransaction:
    """Record of an account transaction."""
    transaction_id: str
    account_id: str
    operation: AccountOperation
    amount: float
    timestamp: str
    reference: str
    balance_after: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "operation": self.operation.value,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "reference": self.reference,
            "balance_after": self.balance_after
        }


class AccountMCPServer:
    """
    MCP Server for account operations.
    
    Capabilities:
    - Update account balances
    - Process fund allocations
    - Handle budget adjustments
    - Manage account freezes
    
    Security:
    - Only accepts requests from enforcement gateway
    - Maintains transaction audit trail
    - Enforces balance constraints
    """
    
    def __init__(self):
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._transaction_log: List[AccountTransaction] = []
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an account operation.
        
        Args:
            request: Execution request from enforcement gateway
            
        Returns:
            Execution result
        """
        decision_id = request.get("decision_id")
        intent = request.get("intent", {})
        constraints = request.get("constraints", {})
        
        if not decision_id:
            return {"error": "Missing decision_id", "executed": False}
        
        # Check if account operations are frozen (handle None)
        constraints = constraints or {}
        if constraints.get("frozen"):
            return {
                "error": "Account operations frozen by policy",
                "executed": False
            }
        
        intent_type = intent.get("intent_type")
        params = intent.get("parameters", {})
        
        if intent_type == "approve_payment":
            return await self._process_debit(intent, params)
        else:
            return {"error": f"Unsupported intent type: {intent_type}", "executed": False}
    
    async def _process_debit(
        self,
        intent: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a debit (payment) from an account."""
        transaction_id = str(uuid.uuid4())
        account_id = params.get("source_account", "default")
        amount = params.get("amount", 0)
        
        # Get or create account
        if account_id not in self._accounts:
            self._accounts[account_id] = {
                "balance": 100000.00,  # Default starting balance
                "frozen": False,
                "created_at": datetime.utcnow().isoformat()
            }
        
        account = self._accounts[account_id]
        
        # Check if account is frozen
        if account.get("frozen"):
            return {
                "error": "Account is frozen",
                "executed": False
            }
        
        # Check sufficient balance
        if account["balance"] < amount:
            return {
                "error": "Insufficient balance",
                "executed": False,
                "available": account["balance"],
                "requested": amount
            }
        
        # Process debit
        account["balance"] -= amount
        
        transaction = AccountTransaction(
            transaction_id=transaction_id,
            account_id=account_id,
            operation=AccountOperation.DEBIT,
            amount=amount,
            timestamp=datetime.utcnow().isoformat(),
            reference=intent.get("target_id", ""),
            balance_after=account["balance"]
        )
        
        self._transaction_log.append(transaction)
        
        return {
            "executed": True,
            "transaction": transaction.to_dict()
        }
    
    async def credit_account(
        self,
        account_id: str,
        amount: float,
        reference: str
    ) -> Dict[str, Any]:
        """Credit an account (add funds)."""
        transaction_id = str(uuid.uuid4())
        
        if account_id not in self._accounts:
            self._accounts[account_id] = {
                "balance": 0.0,
                "frozen": False,
                "created_at": datetime.utcnow().isoformat()
            }
        
        account = self._accounts[account_id]
        account["balance"] += amount
        
        transaction = AccountTransaction(
            transaction_id=transaction_id,
            account_id=account_id,
            operation=AccountOperation.CREDIT,
            amount=amount,
            timestamp=datetime.utcnow().isoformat(),
            reference=reference,
            balance_after=account["balance"]
        )
        
        self._transaction_log.append(transaction)
        
        return {
            "executed": True,
            "transaction": transaction.to_dict()
        }
    
    async def freeze_account(self, account_id: str, reason: str) -> Dict[str, Any]:
        """Freeze an account."""
        if account_id not in self._accounts:
            return {"error": "Account not found", "executed": False}
        
        self._accounts[account_id]["frozen"] = True
        self._accounts[account_id]["freeze_reason"] = reason
        self._accounts[account_id]["frozen_at"] = datetime.utcnow().isoformat()
        
        return {
            "executed": True,
            "account_id": account_id,
            "status": "frozen"
        }
    
    def get_account_balance(self, account_id: str) -> Optional[float]:
        """Get current balance of an account."""
        account = self._accounts.get(account_id)
        return account["balance"] if account else None
    
    def get_transaction_history(
        self, 
        account_id: str
    ) -> List[Dict[str, Any]]:
        """Get transaction history for an account."""
        return [
            t.to_dict() for t in self._transaction_log
            if t.account_id == account_id
        ]
