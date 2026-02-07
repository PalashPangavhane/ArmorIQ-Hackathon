import { useState, useEffect } from 'react'
import './App.css'

// Simulated processing states
const PROCESSING_STATES = {
  SUBMITTED: { label: 'Submitted', color: 'blue', icon: '📤' },
  VALIDATING: { label: 'AI Validating', color: 'purple', icon: '🧠' },
  POLICY_CHECK: { label: 'Policy Check', color: 'cyan', icon: '🔒' },
  RISK_ANALYSIS: { label: 'Risk Analysis', color: 'yellow', icon: '🎯' },
  PENDING_APPROVAL: { label: 'Pending Approval', color: 'orange', icon: '⏳' },
  APPROVED: { label: 'Approved', color: 'green', icon: '✅' },
  REJECTED: { label: 'Rejected', color: 'red', icon: '❌' },
}

// Initial expense requests
const initialRequests = [
  {
    id: 'EXP-001',
    employee: { name: 'Ravi Kumar', id: 'EMP-101', department: 'Engineering' },
    type: 'Cab',
    amount: 850,
    from: 'Hinjewadi IT Park',
    to: 'Pune Airport',
    description: 'Client meeting travel',
    status: 'APPROVED',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    aiValidation: { decision: 'APPROVE', confidence: 0.92, reasoning: 'Amount within expected range for airport trip' },
    policyResult: { result: 'approved', checks: ['Amount ✓', 'Category ✓', 'Vendor ✓'] }
  },
  {
    id: 'EXP-002',
    employee: { name: 'Priya Sharma', id: 'EMP-102', department: 'Sales' },
    type: 'Food',
    amount: 1500,
    from: null,
    to: null,
    description: 'Team lunch - client entertainment',
    status: 'PENDING_APPROVAL',
    timestamp: new Date(Date.now() - 1800000).toISOString(),
    aiValidation: { decision: 'FLAG', confidence: 0.65, reasoning: 'Amount higher than typical team lunch' },
    policyResult: { result: 'require_approval', checks: ['Amount ⚠', 'Category ✓', 'Needs CFO approval'] }
  },
  {
    id: 'EXP-003',
    employee: { name: 'Amit Patel', id: 'EMP-103', department: 'Finance' },
    type: 'Cab',
    amount: 2500,
    from: 'Koramangala',
    to: 'Indiranagar',
    description: 'Office commute',
    status: 'REJECTED',
    timestamp: new Date(Date.now() - 900000).toISOString(),
    aiValidation: { decision: 'REJECT', confidence: 0.88, reasoning: 'Amount too high for 5km local trip' },
    policyResult: { result: 'denied', checks: ['Amount ❌', 'Distance mismatch'] }
  }
]

function App() {
  const [view, setView] = useState('landing') // 'landing', 'employee', or 'ceo'
  const [requests, setRequests] = useState(initialRequests)
  const [formData, setFormData] = useState({
    name: '',
    employeeId: '',
    department: '',
    expenseType: 'Cab',
    amount: '',
    from: '',
    to: '',
    description: ''
  })
  const [submitting, setSubmitting] = useState(false)
  const [currentProcessing, setCurrentProcessing] = useState(null)

  // Simulate request processing
  const processRequest = async (request) => {
    const stages = ['SUBMITTED', 'VALIDATING', 'POLICY_CHECK', 'RISK_ANALYSIS', 'PENDING_APPROVAL']

    for (let i = 0; i < stages.length; i++) {
      setCurrentProcessing({ id: request.id, stage: stages[i] })
      setRequests(prev => prev.map(r =>
        r.id === request.id ? { ...r, status: stages[i] } : r
      ))
      await new Promise(resolve => setTimeout(resolve, 1500))
    }

    const finalStatus = request.amount < 1000 ? 'APPROVED' : 'PENDING_APPROVAL'
    setRequests(prev => prev.map(r =>
      r.id === request.id ? {
        ...r,
        status: finalStatus,
        aiValidation: {
          decision: request.amount < 1000 ? 'APPROVE' : 'FLAG',
          confidence: 0.85,
          reasoning: request.amount < 1000
            ? 'Amount within policy limits'
            : 'Amount exceeds auto-approval threshold'
        },
        policyResult: {
          result: request.amount < 1000 ? 'approved' : 'require_approval',
          checks: request.amount < 1000
            ? ['Amount ✓', 'Category ✓', 'Vendor ✓']
            : ['Amount ⚠', 'Needs manager approval']
        }
      } : r
    ))
    setCurrentProcessing(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)

    const newRequest = {
      id: `EXP-${String(requests.length + 1).padStart(3, '0')}`,
      employee: {
        name: formData.name,
        id: formData.employeeId,
        department: formData.department
      },
      type: formData.expenseType,
      amount: parseFloat(formData.amount),
      from: formData.from || null,
      to: formData.to || null,
      description: formData.description,
      status: 'SUBMITTED',
      timestamp: new Date().toISOString(),
      aiValidation: null,
      policyResult: null
    }

    setRequests(prev => [newRequest, ...prev])
    setFormData({
      name: '',
      employeeId: '',
      department: '',
      expenseType: 'Cab',
      amount: '',
      from: '',
      to: '',
      description: ''
    })
    setSubmitting(false)
    setTimeout(() => processRequest(newRequest), 500)
  }

  const handleCEOAction = (requestId, action) => {
    setRequests(prev => prev.map(r =>
      r.id === requestId ? { ...r, status: action === 'approve' ? 'APPROVED' : 'REJECTED' } : r
    ))
  }

  const stats = {
    total: requests.length,
    approved: requests.filter(r => r.status === 'APPROVED').length,
    pending: requests.filter(r => r.status === 'PENDING_APPROVAL').length,
    rejected: requests.filter(r => r.status === 'REJECTED').length,
    processing: requests.filter(r => !['APPROVED', 'REJECTED', 'PENDING_APPROVAL'].includes(r.status)).length
  }

  if (view === 'landing') {
    return <LandingPage onGetStarted={() => setView('employee')} />
  }

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="header">
        <div className="logo" onClick={() => setView('landing')} style={{ cursor: 'pointer' }}>
          <div className="logo-icon">🛡️</div>
          <span className="logo-text">TrustGate</span>
          <span className="logo-subtitle">
            {view === 'employee' ? 'Employee Portal' : 'CEO Dashboard'}
          </span>
        </div>

        <div className="view-toggle">
          <button
            className={`toggle-btn ${view === 'employee' ? 'active' : ''}`}
            onClick={() => setView('employee')}
          >
            👤 Employee
          </button>
          <button
            className={`toggle-btn ${view === 'ceo' ? 'active' : ''}`}
            onClick={() => setView('ceo')}
          >
            👔 CEO
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {view === 'employee' ? (
          <EmployeeView
            formData={formData}
            setFormData={setFormData}
            onSubmit={handleSubmit}
            submitting={submitting}
            requests={requests}
          />
        ) : (
          <CEOView
            requests={requests}
            stats={stats}
            currentProcessing={currentProcessing}
            onAction={handleCEOAction}
          />
        )}
      </main>
    </div>
  )
}

// Landing Page Component
function LandingPage({ onGetStarted }) {
  return (
    <div className="landing-page">
      {/* Hero Section */}
      <section className="hero">
        <nav className="landing-nav">
          <div className="logo">
            <div className="logo-icon">🛡️</div>
            <span className="logo-text">TrustGate</span>
          </div>
          <div className="nav-links">
            <a href="#how-it-works">How It Works</a>
            <a href="#features">Features</a>
            <a href="#tech">Technology</a>
            <button className="nav-cta" onClick={onGetStarted}>Get Started →</button>
          </div>
        </nav>

        <div className="hero-content">
          <div className="hero-badge">🚀 AI-Powered Financial Control</div>
          <h1 className="hero-title">
            Secure Your AI Agents with
            <span className="gradient-text"> Intent Intelligence™</span>
          </h1>
          <p className="hero-subtitle">
            TrustGate interprets agent goals, verifies identity and access, and enforces policies
            at runtime — keeping autonomous AI agents safe and compliant.
          </p>
          <div className="hero-actions">
            <button className="primary-btn" onClick={onGetStarted}>
              🎯 Try Demo Dashboard
            </button>
            <button className="secondary-btn">
              📄 View Documentation
            </button>
          </div>

          <div className="hero-stats">
            <div className="hero-stat">
              <span className="stat-num">99.9%</span>
              <span className="stat-text">Policy Compliance</span>
            </div>
            <div className="hero-stat">
              <span className="stat-num">&lt;50ms</span>
              <span className="stat-text">Validation Time</span>
            </div>
            <div className="hero-stat">
              <span className="stat-num">8+</span>
              <span className="stat-text">Risk Factors</span>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="section">
        <h2 className="section-title">How TrustGate Works</h2>
        <p className="section-subtitle">
          A multi-layered defense system for autonomous financial operations
        </p>

        <div className="flow-diagram">
          <div className="flow-step">
            <div className="flow-icon">👤</div>
            <div className="flow-label">Employee</div>
            <div className="flow-desc">Submits expense + receipt</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step highlight">
            <div className="flow-icon">📄</div>
            <div className="flow-label">Hybrid RAG</div>
            <div className="flow-desc">Extracts & stores receipt data</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step highlight">
            <div className="flow-icon">🧠</div>
            <div className="flow-label">AI Agent (Qwen3)</div>
            <div className="flow-desc">Interprets intent, validates amount</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step highlight">
            <div className="flow-icon">🛡️</div>
            <div className="flow-label">TrustGate</div>
            <div className="flow-desc">Policy enforcement & GNN risk</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="flow-icon">✅</div>
            <div className="flow-label">Decision</div>
            <div className="flow-desc">Approve / Reject / Escalate</div>
          </div>
        </div>

        <div className="process-cards">
          <div className="process-card">
            <div className="process-num">01</div>
            <h3>Hybrid RAG Pipeline</h3>
            <p>Receipts and bills are processed via OCR, embedded, and stored in vector DB. This data continuously updates the GNN for smarter fraud detection.</p>
          </div>
          <div className="process-card">
            <div className="process-num">02</div>
            <h3>Intent Intelligence™</h3>
            <p>The AI agent (Qwen3 8B) interprets the user's goal and validates if the expense amount is reasonable using RAG-retrieved context.</p>
          </div>
          <div className="process-card">
            <div className="process-num">03</div>
            <h3>Policy Enforcement</h3>
            <p>TrustGate checks against 20+ enterprise policies: amount limits, vendor allowlists, segregation of duties, budget controls, and more.</p>
          </div>
          <div className="process-card">
            <div className="process-num">04</div>
            <h3>GNN Risk Detection</h3>
            <p>Graph Neural Network analyzes transaction patterns enriched by RAG data to detect anomalies that LLMs might miss.</p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="section dark-section">
        <h2 className="section-title">What Makes TrustGate Different</h2>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">📄</div>
            <h3>Hybrid RAG Pipeline</h3>
            <p>Receipts and bills are OCR-processed, embedded, and stored in a vector database. This data enriches the GNN for continuously improving guardrails.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Local LLM Processing</h3>
            <p>No external APIs. Your financial data never leaves your infrastructure. Uses locally-run Qwen3 8B for intelligent validation.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Enterprise Policies</h3>
            <p>Segregation of Duties, Budget Controls, Duplicate Detection, Geographic Restrictions, Velocity Limits — all configurable via YAML.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>GNN Risk Analysis</h3>
            <p>Graph-based anomaly detection catches patterns that rule-based systems miss. Fed by RAG data for defense in depth.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Real-Time Decisions</h3>
            <p>Sub-50ms policy evaluation. Instant feedback on transaction approval status with full audit trail.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📋</div>
            <h3>Complete Audit Trail</h3>
            <p>Every decision is logged with reasoning. Full traceability from intent to execution for compliance and debugging.</p>
          </div>
        </div>
      </section>

      {/* Technology Stack */}
      <section id="tech" className="section">
        <h2 className="section-title">Technology Stack</h2>
        <p className="section-subtitle">Built with modern, production-ready technologies</p>

        <div className="tech-grid">
          <div className="tech-category">
            <h3>🤖 AI & ML</h3>
            <div className="tech-items">
              <div className="tech-item">
                <span className="tech-name">Qwen3 8B</span>
                <span className="tech-desc">Local LLM for intent interpretation</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">Ollama</span>
                <span className="tech-desc">Local model serving infrastructure</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">GNN (Heuristic)</span>
                <span className="tech-desc">Graph-based risk detection</span>
              </div>
            </div>
          </div>

          <div className="tech-category">
            <h3>🔧 Backend</h3>
            <div className="tech-items">
              <div className="tech-item">
                <span className="tech-name">Python 3.11+</span>
                <span className="tech-desc">Core policy engine</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">AsyncIO</span>
                <span className="tech-desc">Concurrent processing</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">PyYAML</span>
                <span className="tech-desc">Policy configuration</span>
              </div>
            </div>
          </div>

          <div className="tech-category">
            <h3>🎨 Frontend</h3>
            <div className="tech-items">
              <div className="tech-item">
                <span className="tech-name">React 18</span>
                <span className="tech-desc">UI framework</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">Vite</span>
                <span className="tech-desc">Build tool & dev server</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">CSS3</span>
                <span className="tech-desc">Glassmorphism & animations</span>
              </div>
            </div>
          </div>

          <div className="tech-category">
            <h3>🔐 Security</h3>
            <div className="tech-items">
              <div className="tech-item">
                <span className="tech-name">Zero External APIs</span>
                <span className="tech-desc">Data stays local</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">RBAC</span>
                <span className="tech-desc">Role-based access control</span>
              </div>
              <div className="tech-item">
                <span className="tech-name">Audit Logging</span>
                <span className="tech-desc">Complete traceability</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <h2>Ready to Secure Your AI Agents?</h2>
        <p>Experience the power of Intent Intelligence™ with our interactive demo.</p>
        <button className="primary-btn large" onClick={onGetStarted}>
          🚀 Launch Demo Dashboard
        </button>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-logo">
            <div className="logo-icon">🛡️</div>
            <span className="logo-text">TrustGate</span>
          </div>
          <p>Built for MCP Hackathon 2025 • AI Financial Control System</p>
        </div>
      </footer>
    </div>
  )
}

// Employee View Component
function EmployeeView({ formData, setFormData, onSubmit, submitting, requests }) {
  return (
    <div className="employee-view">
      <div className="view-grid">
        {/* Expense Submission Form */}
        <div className="card form-card">
          <div className="card-header">
            <div className="card-title">
              <span className="card-title-icon">📝</span>
              Submit Expense
            </div>
          </div>
          <div className="card-body">
            <form onSubmit={onSubmit} className="expense-form">
              <div className="form-section">
                <h3 className="form-section-title">Personal Details</h3>
                <div className="form-row">
                  <div className="form-group">
                    <label>Full Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={e => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g., Ravi Kumar"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Employee ID</label>
                    <input
                      type="text"
                      value={formData.employeeId}
                      onChange={e => setFormData({ ...formData, employeeId: e.target.value })}
                      placeholder="e.g., EMP-101"
                      required
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Department</label>
                  <select
                    value={formData.department}
                    onChange={e => setFormData({ ...formData, department: e.target.value })}
                    required
                  >
                    <option value="">Select Department</option>
                    <option value="Engineering">Engineering</option>
                    <option value="Sales">Sales</option>
                    <option value="Finance">Finance</option>
                    <option value="HR">HR</option>
                    <option value="Marketing">Marketing</option>
                  </select>
                </div>
              </div>

              <div className="form-section">
                <h3 className="form-section-title">Expense Details</h3>
                <div className="form-row">
                  <div className="form-group">
                    <label>Expense Type</label>
                    <select
                      value={formData.expenseType}
                      onChange={e => setFormData({ ...formData, expenseType: e.target.value })}
                    >
                      <option value="Cab">🚕 Cab/Taxi</option>
                      <option value="Food">🍽️ Food/Meals</option>
                      <option value="Hotel">🏨 Hotel</option>
                      <option value="Supplies">📦 Supplies</option>
                      <option value="Other">📋 Other</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Amount (₹)</label>
                    <input
                      type="number"
                      value={formData.amount}
                      onChange={e => setFormData({ ...formData, amount: e.target.value })}
                      placeholder="e.g., 850"
                      min="1"
                      required
                    />
                  </div>
                </div>

                {formData.expenseType === 'Cab' && (
                  <div className="form-row">
                    <div className="form-group">
                      <label>From Location</label>
                      <input
                        type="text"
                        value={formData.from}
                        onChange={e => setFormData({ ...formData, from: e.target.value })}
                        placeholder="e.g., Hinjewadi IT Park"
                      />
                    </div>
                    <div className="form-group">
                      <label>To Location</label>
                      <input
                        type="text"
                        value={formData.to}
                        onChange={e => setFormData({ ...formData, to: e.target.value })}
                        placeholder="e.g., Pune Airport"
                      />
                    </div>
                  </div>
                )}

                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    value={formData.description}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Brief description of the expense..."
                    rows="3"
                    required
                  />
                </div>
              </div>

              <button type="submit" className="submit-btn" disabled={submitting}>
                {submitting ? '⏳ Submitting...' : '📤 Submit Expense'}
              </button>
            </form>
          </div>
        </div>

        {/* Recent Requests */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <span className="card-title-icon">📋</span>
              Recent Requests
            </div>
          </div>
          <div className="card-body scrollable">
            {requests.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📭</div>
                <p>No expenses submitted yet</p>
              </div>
            ) : (
              requests.map(req => (
                <div key={req.id} className="request-item">
                  <div className="request-header">
                    <span className="request-id">{req.id}</span>
                    <span className={`status-badge ${PROCESSING_STATES[req.status]?.color}`}>
                      {PROCESSING_STATES[req.status]?.icon} {PROCESSING_STATES[req.status]?.label}
                    </span>
                  </div>
                  <div className="request-details">
                    <span>{req.type} • {req.employee.name}</span>
                    <span className="request-amount">₹{req.amount.toLocaleString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// CEO View Component
function CEOView({ requests, stats, currentProcessing, onAction }) {
  return (
    <div className="ceo-view">
      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">Total Requests</div>
        </div>
        <div className="stat-card green">
          <div className="stat-number">{stats.approved}</div>
          <div className="stat-label">Approved</div>
        </div>
        <div className="stat-card orange">
          <div className="stat-number">{stats.pending}</div>
          <div className="stat-label">Pending</div>
        </div>
        <div className="stat-card red">
          <div className="stat-number">{stats.rejected}</div>
          <div className="stat-label">Rejected</div>
        </div>
        <div className="stat-card purple">
          <div className="stat-number">{stats.processing}</div>
          <div className="stat-label">Processing</div>
        </div>
      </div>

      {/* Processing Pipeline */}
      {currentProcessing && (
        <div className="processing-banner">
          <div className="processing-content">
            <span className="processing-icon">🔄</span>
            <span>Processing {currentProcessing.id}: </span>
            <span className="processing-stage">
              {PROCESSING_STATES[currentProcessing.stage]?.icon} {PROCESSING_STATES[currentProcessing.stage]?.label}
            </span>
          </div>
          <div className="processing-bar">
            <div className="processing-fill" style={{
              width: currentProcessing.stage === 'SUBMITTED' ? '20%' :
                currentProcessing.stage === 'VALIDATING' ? '40%' :
                  currentProcessing.stage === 'POLICY_CHECK' ? '60%' :
                    currentProcessing.stage === 'RISK_ANALYSIS' ? '80%' : '95%'
            }}></div>
          </div>
        </div>
      )}

      {/* All Requests */}
      <div className="card full-width">
        <div className="card-header">
          <div className="card-title">
            <span className="card-title-icon">📊</span>
            All Expense Requests
          </div>
          <div className="live-indicator">
            <div className="live-dot"></div>
            LIVE
          </div>
        </div>
        <div className="card-body scrollable">
          {requests.map(req => (
            <div key={req.id} className={`ceo-request-item ${req.status === 'PENDING_APPROVAL' ? 'highlight' : ''}`}>
              <div className="request-main">
                <div className="request-left">
                  <div className="employee-avatar">
                    {req.employee.name.charAt(0)}
                  </div>
                  <div className="request-info">
                    <div className="employee-name">{req.employee.name}</div>
                    <div className="employee-meta">
                      {req.employee.id} • {req.employee.department}
                    </div>
                  </div>
                </div>
                <div className="request-center">
                  <div className="expense-type">{req.type}</div>
                  <div className="expense-desc">{req.description}</div>
                  {req.from && req.to && (
                    <div className="expense-route">{req.from} → {req.to}</div>
                  )}
                </div>
                <div className="request-right">
                  <div className="expense-amount">₹{req.amount.toLocaleString()}</div>
                  <div className={`status-badge ${PROCESSING_STATES[req.status]?.color}`}>
                    {PROCESSING_STATES[req.status]?.icon} {PROCESSING_STATES[req.status]?.label}
                  </div>
                </div>
              </div>

              {req.aiValidation && (
                <div className="request-analysis">
                  <div className="analysis-section">
                    <span className="analysis-label">🧠 AI Validation:</span>
                    <span className={`analysis-value ${req.aiValidation.decision === 'APPROVE' ? 'green' : req.aiValidation.decision === 'FLAG' ? 'yellow' : 'red'}`}>
                      {req.aiValidation.decision} ({(req.aiValidation.confidence * 100).toFixed(0)}%)
                    </span>
                    <span className="analysis-reasoning">{req.aiValidation.reasoning}</span>
                  </div>
                  <div className="analysis-section">
                    <span className="analysis-label">🔒 Policy:</span>
                    <div className="policy-checks">
                      {req.policyResult?.checks.map((check, i) => (
                        <span key={i} className="policy-check">{check}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {req.status === 'PENDING_APPROVAL' && (
                <div className="request-actions">
                  <button
                    className="action-btn approve"
                    onClick={() => onAction(req.id, 'approve')}
                  >
                    ✓ Approve
                  </button>
                  <button
                    className="action-btn reject"
                    onClick={() => onAction(req.id, 'reject')}
                  >
                    ✕ Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default App
