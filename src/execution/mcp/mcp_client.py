"""
MCP Client Module

Client for communicating with MCP servers.
Used by the enforcement gateway to forward approved intents.
"""

from typing import Dict, Any, Optional
from enum import Enum

from .payment_server import PaymentMCPServer
from .approval_server import ApprovalMCPServer
from .account_server import AccountMCPServer


class MCPServerType(Enum):
    PAYMENT = "payment"
    APPROVAL = "approval"
    ACCOUNT = "account"


class MCPClient:
    """
    Client for MCP server communication.
    
    Routes execution requests to appropriate MCP servers.
    Provides unified interface for the enforcement gateway.
    """
    
    def __init__(self):
        self._servers: Dict[MCPServerType, Any] = {}
        self._initialize_servers()
    
    def _initialize_servers(self):
        """Initialize MCP servers."""
        self._servers[MCPServerType.PAYMENT] = PaymentMCPServer()
        self._servers[MCPServerType.APPROVAL] = ApprovalMCPServer()
        self._servers[MCPServerType.ACCOUNT] = AccountMCPServer()
    
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a request by routing to appropriate MCP server.
        
        Args:
            request: Execution request containing:
                - decision_id: ID from enforcement gateway
                - intent: Original intent
                - constraints: Applied constraints
                
        Returns:
            Combined execution results
        """
        intent = request.get("intent", {})
        intent_type = intent.get("intent_type")
        
        # Route based on intent type
        server = self._get_server_for_intent(intent_type)
        
        if server is None:
            return {
                "error": f"No server available for intent type: {intent_type}",
                "executed": False
            }
        
        # Execute on appropriate server
        result = await server.execute(request)
        
        # For payment approvals, also update account
        if intent_type == "approve_payment" and result.get("executed"):
            account_result = await self._servers[MCPServerType.ACCOUNT].execute(request)
            result["account_update"] = account_result
        
        # Always record approval status
        if intent_type in ["approve_payment", "reject_payment", "escalate", "flag_suspicious"]:
            approval_result = await self._servers[MCPServerType.APPROVAL].execute(request)
            result["approval_record"] = approval_result
        
        return result
    
    def _get_server_for_intent(self, intent_type: str) -> Optional[Any]:
        """Get the appropriate MCP server for an intent type."""
        if intent_type in ["approve_payment", "reject_payment"]:
            return self._servers[MCPServerType.PAYMENT]
        elif intent_type in ["escalate", "flag_suspicious"]:
            return self._servers[MCPServerType.APPROVAL]
        return None
    
    def get_payment_server(self) -> PaymentMCPServer:
        """Get the payment MCP server."""
        return self._servers[MCPServerType.PAYMENT]
    
    def get_approval_server(self) -> ApprovalMCPServer:
        """Get the approval MCP server."""
        return self._servers[MCPServerType.APPROVAL]
    
    def get_account_server(self) -> AccountMCPServer:
        """Get the account MCP server."""
        return self._servers[MCPServerType.ACCOUNT]
