# Autonomous Payment Security & Approval Agent System

## Overview

This project implements a secure, autonomous payment and financial approval system built around **agentic reasoning with strict execution guarantees**.

The system is designed for high-risk domains such as company payments, reimbursements, and expense approvals, where AI autonomy must be balanced with security, governance, and user control.

AI agents are allowed to freely reason, analyze financial data, and propose actions. However, **no agent is ever allowed to directly execute real-world actions**. All payments, approvals, and account updates are enforced through policy-controlled execution servers.

To support informed and safe decision-making, the system combines:

- A **RAG (Retrieval-Augmented Generation) pipeline** for grounding agent reasoning in company financial data
- A **GNN-based fraud and risk detection system** used as a fallback mechanism that constrains or freezes execution under uncertainty
- A **policy and intent enforcement layer** that guarantees bounded delegation and least-privilege execution
- **MCP servers** as the only gateway to real-world effects

This architecture enables autonomy **without loss of control**, supports graceful degradation under risk, and provides full traceability from intent to execution.

---

## Core Objectives

- Safely automate financial workflows
- Prevent unauthorized, excessive, or anomalous payments
- Enforce approval hierarchies and bounded delegation
- Use internal financial data for grounded reasoning
- Degrade autonomy under risk instead of escalating trust
- Provide auditability and execution guarantees by design

---

## System Architecture

The system is structured into four logical layers:

1. **Intelligence Layer** (RAG + GNN, read-only)
2. **Reasoning Layer** (AI agents)
3. **Control Layer** (Intent & Policy Enforcement)
4. **Execution Layer** (MCP Servers)

The Intelligence Layer may run on a single server for efficiency but is logically isolated into two services:
- RAG for contextual knowledge
- GNN for fraud and risk assessment

Neither component has execution authority.

---

## High-Level End-to-End Flow

1. Financial documents, expense logs, and transaction data are ingested
2. RAG processes documents into embeddings and indexes them
3. Transaction graphs are updated for GNN-based risk analysis
4. An employee submits a reimbursement or payment request
5. Finance Agent queries RAG for budget, history, and vendor context
6. Finance Agent proposes a structured intent
7. Static policy rules are evaluated
8. GNN produces a fraud/risk signal
9. Risk-based constraints are applied to policy
10. If allowed, the MCP server executes the action
11. All decisions and actions are logged for audit

---

## AI Agent Layer (Reasoning Only)

Agents are responsible for **analysis, planning, and coordination**, never execution.

### Example Agents

**Finance Agent**
- Reviews reimbursement requests
- Analyzes budget availability and spending trends
- Proposes approval or escalation intents

**Fraud Monitoring Agent**
- Consumes risk signals
- Flags anomalies and suspicious patterns
- Never approves or blocks directly

**CEO Approval Agent**
- Holds delegated authority for higher-value transactions
- Operates within strictly defined limits

Agents may collaborate and query intelligence services, but cannot mutate system state.

---

## Intelligence Layer: RAG + GNN (Read-Only)

### RAG Knowledge System

The RAG system ingests structured and unstructured financial data such as:

- Financial reports (PDFs)
- Expense ledgers (CSV)
- Vendor records
- Budget documents
- Audit summaries

Processing pipeline:
- Document chunking
- Embedding generation
- Vector database storage
- Contextual retrieval at query time

Used to answer questions like:
- Remaining department budget
- Historical reimbursement averages
- Vendor legitimacy
- Spending patterns

---

### GNN-Based Fraud & Risk Detection (Fallback Mechanism)

All payment and reimbursement activity is modeled as a graph:

- Nodes: employees, vendors, accounts, departments
- Edges: transactions, approvals, reimbursements
- Attributes: amount, time, frequency, category

The GNN produces **risk signals**, not decisions.

Example output:
```json
{
  "risk_level": "LOW | MEDIUM | HIGH",
  "risk_score": 0.0 - 1.0,
  "risk_reasons": ["new_vendor", "amount_spike"]
}
