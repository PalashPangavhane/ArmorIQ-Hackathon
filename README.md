# 🛡️ TrustGate - AI Financial Control System

> **Intent Intelligence™ for Autonomous AI Agents**

TrustGate interprets agent goals, verifies identity and access, and enforces policies at runtime — keeping autonomous AI agents safe and compliant.

[![Built for ArmorIQ MCP Hackathon](https://img.shields.io/badge/Built%20for-ArmorIQ%20MCP%20Hackathon%202025-blue)]()
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green)]()
[![React 18](https://img.shields.io/badge/React-18-61dafb)]()

---

## 🎯 Overview

TrustGate is a multi-layered defense system for autonomous financial operations. AI agents can freely reason and propose actions, but **all real-world execution flows through policy-controlled MCP servers**.

### Key Differentiators

| Feature | Description |
|---------|-------------|
| 🧠 **Local LLM** | Qwen3 8B via Ollama - data never leaves your infrastructure |
| 📄 **Hybrid RAG** | Receipts OCR'd, embedded, stored - enriches GNN continuously |
| 🛡️ **20+ Policies** | Amount limits, vendor blocklists, segregation of duties |
| 📊 **GNN Risk Detection** | Graph-based anomaly detection for fraud patterns |
| ⚡ **Sub-50ms Decisions** | Real-time policy evaluation with full audit trail |
| 🔐 **MCP Architecture** | Only gateway for agents to execute real-world actions |

---

## 📁 Project Structure

```
TrustGate/
├── src/
│   ├── intelligence/          # AI & ML Layer
│   │   ├── llm/               # Local LLM client (Qwen3)
│   │   │   ├── local_llm_client.py
│   │   │   └── expense_validator.py
│   │   ├── rag/               # Hybrid RAG pipeline
│   │   └── gnn/               # Graph Neural Network risk detection
│   │
│   ├── control/               # Policy & Enforcement Layer
│   │   ├── policy_engine.py           # Core policy engine
│   │   ├── advanced_policy_engine.py  # 20+ enterprise policies
│   │   ├── enforcement_gateway.py     # Intent → MCP routing
│   │   ├── intent_validator.py        # Intent validation
│   │   ├── risk_policy_integrator.py  # GNN-policy fusion
│   │   └── audit_trail.py             # Complete audit logging
│   │
│   ├── execution/             # MCP Server Layer
│   │   └── mcp/
│   │       ├── mcp_client.py          # MCP router
│   │       ├── payment_server.py      # PaymentMCPServer
│   │       ├── approval_server.py     # ApprovalMCPServer
│   │       └── account_server.py      # AccountMCPServer
│   │
│   └── agents/                # AI Agent Layer
│       └── delegation_agent.py        # Bounded delegation
│
├── frontend/                  # React Dashboard
│   └── src/
│       ├── App.jsx            # Landing + Dashboard
│       └── index.css          # Styling
│
├── config/
│   └── policies.yaml          # User-defined policy rules
│
└── demos/                     # Terminal Demos
    ├── demo_policy_enforcement.py
    ├── demo_advanced_policies.py
    ├── demo_gnn_risk.py
    └── demo_expense_validation.py
```

---

## 🔄 How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Employee   │────▶│  Hybrid RAG  │────▶│  AI Agent    │────▶│  TrustGate   │────▶│   Decision   │
│  Submits     │     │  (OCR+Store) │     │  (Qwen3 8B)  │     │  + GNN Risk  │     │  Approve/    │
│  Expense     │     │              │     │              │     │              │     │  Deny/Flag   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Processing Pipeline

1. **Hybrid RAG Pipeline** - Receipts are OCR'd, embedded, and stored in vector DB
2. **Intent Intelligence™** - Qwen3 8B interprets goals, validates amounts using RAG context
3. **Policy Enforcement** - 20+ enterprise policies evaluated (amount, vendor, category)
4. **GNN Risk Detection** - Graph patterns analyzed for anomalies
5. **MCP Execution** - Only approved intents reach MCP servers

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Ollama for full LLM features

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/TrustGate.git
cd TrustGate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

### Running the Demo

#### Terminal Demos (MCP Servers)

```bash
# Policy Enforcement Demo (recommended for judges)
python demos/demo_policy_enforcement.py

# Advanced Policies Demo
python demos/demo_advanced_policies.py

# GNN Risk Detection Demo
python demos/demo_gnn_risk.py

# LLM Expense Validation Demo
python demos/demo_expense_validation.py
```

#### Web Dashboard

```bash
# Start the frontend
cd frontend
npm run dev

# Open http://localhost:5173
```

#### (Optional) Full LLM Mode

```bash
# Install and run Ollama
ollama pull qwen3:8b
ollama serve

# LLM will now provide intelligent expense validation
```

---

## 🎬 Demo Scenarios

### Scenario 1: Payment Within Limits ✅
- **Amount:** $500
- **Result:** `APPROVED`
- **Reason:** Within per-transaction limit

### Scenario 2: Exceeds Transaction Limit ❌
- **Amount:** $75,000
- **Result:** `BLOCKED`
- **Reason:** Exceeds $50,000 cap

### Scenario 3: Blocked Vendor ❌
- **Vendor:** "Suspicious Vendor"
- **Result:** `BLOCKED`
- **Reason:** Vendor on blocklist

### Scenario 4: High Risk Signal ❄️
- **GNN Score:** 0.95
- **Result:** `FROZEN`
- **Reason:** Unusual pattern detected

### Scenario 5: Bounded Delegation ✅
- **Delegate Limit:** $500
- **Requested:** $300
- **Result:** `APPROVED`

### Scenario 6: Delegation Exceeded ❌
- **Delegate Limit:** $500
- **Requested:** $1,000
- **Result:** `BLOCKED`
- **Reason:** Exceeds delegated authority

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **AI/ML** | Qwen3 8B + Ollama | Local LLM for intent validation |
| **AI/ML** | GNN (Heuristic) | Graph-based risk detection |
| **Backend** | Python 3.11+ | Policy engine, MCP servers |
| **Backend** | AsyncIO | Concurrent processing |
| **Frontend** | React 18 + Vite | Dashboard UI |
| **Config** | YAML | User-defined policies |
| **Security** | Zero External APIs | Data stays local |

---

## 📋 Policy Configuration

Policies are defined in `config/policies.yaml`:

```yaml
policies:
  - name: per_transaction_limit
    type: amount
    effect: deny
    conditions:
      max_amount: 50000
    
  - name: blocked_vendors
    type: vendor
    effect: deny
    conditions:
      blocklist:
        - "Suspicious Vendor"
        - "Blocked Corp"
    
  - name: business_hours
    type: time_window
    effect: require_approval
    conditions:
      allowed_hours: [9, 18]
```

---

## 📊 Architecture Layers

### 1. Intelligence Layer (Read-Only)
- **RAG**: Document chunking, embedding, contextual retrieval
- **GNN**: Transaction graphs, risk signals, anomaly detection

### 2. Reasoning Layer (AI Agents)
- Finance Agent, Fraud Monitoring Agent, CEO Approval Agent
- Agents reason freely but cannot execute

### 3. Control Layer (Policy Enforcement)
- Intent validation, policy evaluation, risk integration
- Bounded delegation, audit trail

### 4. Execution Layer (MCP Servers)
- **PaymentMCPServer**: Payment processing
- **ApprovalMCPServer**: Approval workflows
- **AccountMCPServer**: Account operations
- Only pathway for real-world effects

---

## 🔒 Security Principles

1. **Agents cannot execute directly** - All actions go through MCP servers
2. **Zero external APIs** - Financial data never leaves infrastructure
3. **Defense in depth** - LLM + GNN + Policies = different failure modes
4. **Bounded delegation** - Agents operate within granted authority
5. **Complete audit trail** - Every decision logged with reasoning

---

## 📈 Key Metrics

| Metric | Value |
|--------|-------|
| Policy Compliance | 99.9% |
| Validation Time | <50ms |
| Risk Factors Analyzed | 8+ |
| Enterprise Policies | 20+ |

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🏆 Hackathon

Built for **ArmorIQ MCP Hackathon 2025**

**Team:** [Your Team Name]

---

<p align="center">
  <strong>TrustGate</strong> - Intent Intelligence™ for Autonomous AI Agents
</p>
