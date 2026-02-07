"""
Sample Data Generator

Generates synthetic financial data for testing the RAG pipeline.
Creates realistic budget documents, expense policies, vendor records, etc.
"""

import os
import json
import csv
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any


class SampleDataGenerator:
    """Generates synthetic financial documents for RAG testing."""
    
    def __init__(self, output_dir: str = "./data/documents"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Sample data pools
        self.departments = [
            "Engineering", "Marketing", "Sales", "HR", "Finance", 
            "Operations", "Legal", "Product", "Customer Success", "IT"
        ]
        
        self.expense_categories = [
            "Travel", "Software", "Hardware", "Office Supplies", 
            "Training", "Meals", "Client Entertainment", "Equipment",
            "Professional Services", "Subscriptions"
        ]
        
        self.vendors = [
            {"id": "V001", "name": "Amazon Business", "category": "General"},
            {"id": "V002", "name": "Delta Airlines", "category": "Travel"},
            {"id": "V003", "name": "Microsoft", "category": "Software"},
            {"id": "V004", "name": "Google Cloud", "category": "Software"},
            {"id": "V005", "name": "Staples", "category": "Office Supplies"},
            {"id": "V006", "name": "Uber Business", "category": "Travel"},
            {"id": "V007", "name": "AWS", "category": "Software"},
            {"id": "V008", "name": "Hilton Hotels", "category": "Travel"},
            {"id": "V009", "name": "LinkedIn", "category": "Subscriptions"},
            {"id": "V010", "name": "Zoom", "category": "Software"},
            {"id": "V011", "name": "WeWork", "category": "Office"},
            {"id": "V012", "name": "Catering Co", "category": "Meals"},
            {"id": "V013", "name": "TechSupplies Inc", "category": "Hardware"},
            {"id": "V014", "name": "CloudHost Pro", "category": "Software"},
            {"id": "V015", "name": "Office Depot", "category": "Office Supplies"}
        ]
        
        self.employees = [
            {"id": "E001", "name": "John Smith", "department": "Engineering", "role": "Senior Engineer"},
            {"id": "E002", "name": "Sarah Johnson", "department": "Marketing", "role": "Marketing Manager"},
            {"id": "E003", "name": "Mike Chen", "department": "Sales", "role": "Sales Representative"},
            {"id": "E004", "name": "Emily Davis", "department": "HR", "role": "HR Specialist"},
            {"id": "E005", "name": "Robert Wilson", "department": "Finance", "role": "Financial Analyst"},
            {"id": "E006", "name": "Lisa Anderson", "department": "Engineering", "role": "Tech Lead"},
            {"id": "E007", "name": "David Brown", "department": "Product", "role": "Product Manager"},
            {"id": "E008", "name": "Jennifer Taylor", "department": "Operations", "role": "Operations Manager"},
            {"id": "E009", "name": "James Martinez", "department": "IT", "role": "IT Administrator"},
            {"id": "E010", "name": "Amanda White", "department": "Legal", "role": "Legal Counsel"}
        ]
    
    def generate_all(self) -> Dict[str, str]:
        """Generate all sample data files."""
        files = {}
        
        # Generate different types of documents
        files["budgets"] = self.generate_budget_documents()
        files["policies"] = self.generate_expense_policies()
        files["vendors"] = self.generate_vendor_records()
        files["expenses"] = self.generate_expense_history()
        files["employees"] = self.generate_employee_data()
        
        print(f"\nGenerated {len(files)} document types in {self.output_dir}")
        return files
    
    def generate_budget_documents(self) -> str:
        """Generate department budget documents."""
        budget_dir = self.output_dir / "budgets"
        budget_dir.mkdir(exist_ok=True)
        
        fiscal_year = "FY2026"
        
        # Generate budget for each department
        for dept in self.departments:
            annual_budget = random.randint(100000, 2000000)
            q1_spent = random.randint(10000, annual_budget // 4)
            q2_spent = random.randint(10000, annual_budget // 4)
            q3_spent = random.randint(10000, annual_budget // 4)
            total_spent = q1_spent + q2_spent + q3_spent
            remaining = annual_budget - total_spent
            
            budget_doc = f"""
DEPARTMENT BUDGET REPORT
========================

Department: {dept}
Fiscal Year: {fiscal_year}
Report Generated: {datetime.now().strftime("%Y-%m-%d")}

BUDGET SUMMARY
--------------
Annual Budget Allocation: ${annual_budget:,}
Total Spent YTD: ${total_spent:,}
Remaining Budget: ${remaining:,}
Budget Utilization: {(total_spent/annual_budget)*100:.1f}%

QUARTERLY BREAKDOWN
-------------------
Q1 Spending: ${q1_spent:,}
Q2 Spending: ${q2_spent:,}
Q3 Spending: ${q3_spent:,}
Q4 Projected: ${annual_budget - total_spent:,}

CATEGORY ALLOCATIONS
--------------------
"""
            # Add category breakdown
            categories_budget = {}
            remaining_to_allocate = annual_budget
            for i, cat in enumerate(self.expense_categories[:-1]):
                if i < len(self.expense_categories) - 1:
                    cat_budget = random.randint(5000, remaining_to_allocate // (len(self.expense_categories) - i))
                    categories_budget[cat] = cat_budget
                    remaining_to_allocate -= cat_budget
                    budget_doc += f"- {cat}: ${cat_budget:,}\n"
            
            # Last category gets remaining
            categories_budget[self.expense_categories[-1]] = remaining_to_allocate
            budget_doc += f"- {self.expense_categories[-1]}: ${remaining_to_allocate:,}\n"
            
            budget_doc += f"""
APPROVAL THRESHOLDS
-------------------
- Under $1,000: Auto-approved
- $1,000 - $5,000: Manager approval required
- $5,000 - $25,000: Director approval required  
- Over $25,000: VP/Executive approval required

NOTES
-----
- All purchases must comply with company procurement policy
- Budget transfers between categories require Finance approval
- Unused budget does not roll over to next fiscal year
"""
            
            # Save as text file
            file_path = budget_dir / f"{dept.lower()}_budget_{fiscal_year}.txt"
            with open(file_path, 'w') as f:
                f.write(budget_doc)
        
        return str(budget_dir)
    
    def generate_expense_policies(self) -> str:
        """Generate expense and reimbursement policy documents."""
        policy_dir = self.output_dir / "policies"
        policy_dir.mkdir(exist_ok=True)
        
        # Main expense policy
        expense_policy = """
COMPANY EXPENSE AND REIMBURSEMENT POLICY
=========================================

Effective Date: January 1, 2026
Last Updated: February 1, 2026
Policy Version: 3.2

1. PURPOSE
----------
This policy establishes guidelines for business expenses and reimbursements
to ensure consistent, fair, and compliant expense management across the organization.

2. SCOPE
--------
This policy applies to all employees, contractors, and authorized representatives
who incur business expenses on behalf of the company.

3. GENERAL GUIDELINES
---------------------
- All expenses must have a valid business purpose
- Original receipts required for expenses over $25
- Expense reports must be submitted within 30 days
- Approvals must be obtained BEFORE incurring expenses over $500

4. EXPENSE CATEGORIES AND LIMITS
---------------------------------

4.1 TRAVEL EXPENSES
- Airfare: Economy class for flights under 6 hours; Business class requires VP approval
- Hotels: Maximum $250/night domestic, $350/night international
- Car Rental: Compact or intermediate class; upgrades require approval
- Mileage: $0.67 per mile for personal vehicle use
- Per Diem: $75/day domestic, $100/day international

4.2 MEALS AND ENTERTAINMENT
- Individual meals: Maximum $50 per meal
- Team meals: Maximum $75 per person
- Client entertainment: Maximum $150 per person; requires client names
- Alcohol: Limited to reasonable amounts; not reimbursable without meals

4.3 SOFTWARE AND SUBSCRIPTIONS
- Annual subscriptions under $500: Manager approval
- Annual subscriptions $500-$5,000: Director approval
- Annual subscriptions over $5,000: IT and Finance approval required

4.4 OFFICE SUPPLIES AND EQUIPMENT
- Standard supplies: Order through approved vendor portal
- Equipment under $1,000: Manager approval
- Equipment over $1,000: IT approval required
- Personal equipment purchases not reimbursable

5. APPROVAL THRESHOLDS
-----------------------
| Amount          | Required Approver     |
|-----------------|----------------------|
| $0 - $500       | Self-approval        |
| $501 - $2,500   | Direct Manager       |
| $2,501 - $10,000| Department Director  |
| $10,001 - $50,000| VP Level            |
| Over $50,000    | CFO/CEO             |

6. PROHIBITED EXPENSES
-----------------------
The following expenses are NOT reimbursable:
- Personal items or services
- Fines, penalties, or late fees
- Political contributions
- Gifts over $100 value
- First-class airfare without pre-approval
- Spa services or personal grooming
- Traffic or parking violations

7. SUBMISSION PROCESS
---------------------
1. Collect all receipts and documentation
2. Complete expense report in expense management system
3. Attach clear images of all receipts
4. Submit for approval within 30 days of expense
5. Reimbursement processed within 14 business days of approval

8. FRAUD AND COMPLIANCE
-----------------------
- Falsifying expense reports is grounds for termination
- Random audits conducted quarterly
- Suspicious patterns flagged for review
- All expenses subject to verification

9. EXCEPTIONS
-------------
Exceptions to this policy require written approval from:
- Department VP for amounts up to $25,000
- CFO for amounts over $25,000
- CEO for policy exceptions affecting multiple departments

For questions, contact: expenses@company.com
"""
        
        with open(policy_dir / "expense_policy.txt", 'w') as f:
            f.write(expense_policy)
        
        # Travel policy
        travel_policy = """
CORPORATE TRAVEL POLICY
========================

1. BOOKING REQUIREMENTS
-----------------------
- All travel must be booked through approved travel portal
- Book flights at least 14 days in advance when possible
- Choose cost-effective options; lowest logical fare required

2. AIRFARE GUIDELINES
---------------------
- Economy class: Standard for all domestic flights
- Premium economy: Allowed for flights over 6 hours
- Business class: Requires VP pre-approval; allowed for flights over 10 hours
- First class: Not permitted without CEO exception

3. LODGING STANDARDS
--------------------
- Use preferred hotel partners when available
- Standard room rate limits:
  * Tier 1 cities (NYC, SF, LA): $300/night
  * Tier 2 cities: $250/night
  * Other locations: $200/night
- Extended stays (5+ nights): Negotiate corporate rate

4. GROUND TRANSPORTATION
------------------------
- Ride-share (Uber/Lyft) preferred for airport transfers
- Rental cars: Compact/intermediate class
- Public transit encouraged when practical
- Limousine service not permitted

5. INTERNATIONAL TRAVEL
-----------------------
- Requires Director approval minimum
- Register trip with Global Security
- Ensure valid passport and visas
- International per diem rates apply
"""
        
        with open(policy_dir / "travel_policy.txt", 'w') as f:
            f.write(travel_policy)
        
        return str(policy_dir)
    
    def generate_vendor_records(self) -> str:
        """Generate vendor database records."""
        vendor_dir = self.output_dir / "vendors"
        vendor_dir.mkdir(exist_ok=True)
        
        vendor_records = []
        
        for vendor in self.vendors:
            # Generate random vendor details
            years_active = random.randint(1, 10)
            total_transactions = random.randint(50, 500)
            total_spend = random.randint(10000, 500000)
            avg_transaction = total_spend // total_transactions
            
            # Vendor risk assessment
            risk_scores = ["Low", "Low", "Low", "Medium", "High"]
            risk_score = random.choice(risk_scores)
            
            vendor_record = {
                "vendor_id": vendor["id"],
                "vendor_name": vendor["name"],
                "category": vendor["category"],
                "status": "Active",
                "years_active": years_active,
                "contract_expiry": (datetime.now() + timedelta(days=random.randint(30, 730))).strftime("%Y-%m-%d"),
                "total_transactions": total_transactions,
                "total_spend": total_spend,
                "average_transaction": avg_transaction,
                "risk_assessment": risk_score,
                "payment_terms": random.choice(["Net 30", "Net 45", "Net 60", "Due on Receipt"]),
                "last_audit_date": (datetime.now() - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
                "compliance_status": "Compliant",
                "preferred_vendor": random.choice([True, False]),
                "notes": f"Approved vendor for {vendor['category']} purchases."
            }
            vendor_records.append(vendor_record)
        
        # Save as JSON
        with open(vendor_dir / "vendor_database.json", 'w') as f:
            json.dump(vendor_records, f, indent=2)
        
        # Also create a text version for each vendor
        for vendor in vendor_records:
            vendor_text = f"""
VENDOR INFORMATION
==================

Vendor ID: {vendor['vendor_id']}
Vendor Name: {vendor['vendor_name']}
Category: {vendor['category']}
Status: {vendor['status']}

RELATIONSHIP SUMMARY
--------------------
Years Active: {vendor['years_active']}
Contract Expiry: {vendor['contract_expiry']}
Payment Terms: {vendor['payment_terms']}
Preferred Vendor: {'Yes' if vendor['preferred_vendor'] else 'No'}

TRANSACTION HISTORY
-------------------
Total Transactions: {vendor['total_transactions']}
Total Spend: ${vendor['total_spend']:,}
Average Transaction: ${vendor['average_transaction']:,}

COMPLIANCE & RISK
-----------------
Risk Assessment: {vendor['risk_assessment']}
Compliance Status: {vendor['compliance_status']}
Last Audit: {vendor['last_audit_date']}

NOTES
-----
{vendor['notes']}
"""
            file_path = vendor_dir / f"{vendor['vendor_id'].lower()}_{vendor['vendor_name'].lower().replace(' ', '_')}.txt"
            with open(file_path, 'w') as f:
                f.write(vendor_text)
        
        return str(vendor_dir)
    
    def generate_expense_history(self) -> str:
        """Generate historical expense data."""
        expense_dir = self.output_dir / "expenses"
        expense_dir.mkdir(exist_ok=True)
        
        expenses = []
        
        # Generate 200 sample expenses
        for i in range(200):
            employee = random.choice(self.employees)
            vendor = random.choice(self.vendors)
            category = random.choice(self.expense_categories)
            
            # Generate realistic amounts based on category
            amount_ranges = {
                "Travel": (100, 5000),
                "Software": (50, 2000),
                "Hardware": (100, 3000),
                "Office Supplies": (20, 500),
                "Training": (200, 5000),
                "Meals": (15, 200),
                "Client Entertainment": (50, 500),
                "Equipment": (100, 5000),
                "Professional Services": (500, 10000),
                "Subscriptions": (20, 1000)
            }
            
            min_amt, max_amt = amount_ranges.get(category, (50, 1000))
            amount = round(random.uniform(min_amt, max_amt), 2)
            
            # Random date in last 6 months
            days_ago = random.randint(0, 180)
            expense_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            # Status based on amount
            if amount < 500:
                status = random.choice(["Approved", "Approved", "Approved", "Pending"])
            elif amount < 5000:
                status = random.choice(["Approved", "Approved", "Pending", "Under Review"])
            else:
                status = random.choice(["Approved", "Pending", "Under Review", "Escalated"])
            
            expense = {
                "expense_id": f"EXP{i+1:05d}",
                "employee_id": employee["id"],
                "employee_name": employee["name"],
                "department": employee["department"],
                "vendor_id": vendor["id"],
                "vendor_name": vendor["name"],
                "category": category,
                "amount": amount,
                "date": expense_date,
                "status": status,
                "description": f"{category} expense - {vendor['name']}",
                "receipt_attached": random.choice([True, True, True, False])
            }
            expenses.append(expense)
        
        # Save as CSV
        csv_path = expense_dir / "expense_history.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=expenses[0].keys())
            writer.writeheader()
            writer.writerows(expenses)
        
        # Also create summary reports per employee
        for employee in self.employees:
            emp_expenses = [e for e in expenses if e["employee_id"] == employee["id"]]
            if emp_expenses:
                total = sum(e["amount"] for e in emp_expenses)
                avg = total / len(emp_expenses)
                
                summary = f"""
EMPLOYEE EXPENSE SUMMARY
========================

Employee: {employee['name']} ({employee['id']})
Department: {employee['department']}
Role: {employee['role']}

EXPENSE OVERVIEW (Last 6 Months)
---------------------------------
Total Expenses: {len(emp_expenses)}
Total Amount: ${total:,.2f}
Average Expense: ${avg:,.2f}

BREAKDOWN BY CATEGORY
---------------------
"""
                # Category breakdown
                categories = {}
                for e in emp_expenses:
                    cat = e["category"]
                    if cat not in categories:
                        categories[cat] = {"count": 0, "amount": 0}
                    categories[cat]["count"] += 1
                    categories[cat]["amount"] += e["amount"]
                
                for cat, data in sorted(categories.items(), key=lambda x: x[1]["amount"], reverse=True):
                    summary += f"- {cat}: {data['count']} expenses, ${data['amount']:,.2f}\n"
                
                summary += f"""
RECENT EXPENSES
---------------
"""
                # List recent expenses
                for e in sorted(emp_expenses, key=lambda x: x["date"], reverse=True)[:5]:
                    summary += f"- {e['date']}: ${e['amount']:,.2f} - {e['description']} ({e['status']})\n"
                
                file_path = expense_dir / f"{employee['id'].lower()}_expense_summary.txt"
                with open(file_path, 'w') as f:
                    f.write(summary)
        
        return str(expense_dir)
    
    def generate_employee_data(self) -> str:
        """Generate employee directory data."""
        employee_dir = self.output_dir / "employees"
        employee_dir.mkdir(exist_ok=True)
        
        # Employee directory JSON
        employee_data = []
        for emp in self.employees:
            emp_record = {
                **emp,
                "email": f"{emp['name'].lower().replace(' ', '.')}@company.com",
                "start_date": (datetime.now() - timedelta(days=random.randint(180, 2000))).strftime("%Y-%m-%d"),
                "expense_limit": random.choice([1000, 2500, 5000, 10000]),
                "manager_id": random.choice([e["id"] for e in self.employees if e["id"] != emp["id"]]),
                "approval_authority": random.choice([500, 1000, 2500, 5000, 10000])
            }
            employee_data.append(emp_record)
        
        with open(employee_dir / "employee_directory.json", 'w') as f:
            json.dump(employee_data, f, indent=2)
        
        return str(employee_dir)


def generate_sample_data():
    """Convenience function to generate all sample data."""
    generator = SampleDataGenerator()
    return generator.generate_all()


if __name__ == "__main__":
    generate_sample_data()
