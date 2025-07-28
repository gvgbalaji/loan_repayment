from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import math

app = Flask(__name__)

class LoanSchedule:
    def __init__(self, principal, annual_interest_rate, loan_term_years, start_date, part_payments=None, day_count_convention='actual_365'):
        """
        Initialize a loan schedule calculator
        
        Args:
            principal: Loan amount
            annual_interest_rate: Annual interest rate as a percentage
            loan_term_years: Loan term in years
            start_date: Loan start date (YYYY-MM-DD)
            part_payments: List of additional payments with dates and amounts
            day_count_convention: 'actual_365' or '30_360' for interest calculation
        """
        self.principal = float(principal)
        self.annual_interest_rate = float(annual_interest_rate) / 100  # Convert percentage to decimal
        self.loan_term_years = int(loan_term_years)
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        self.part_payments = part_payments or []
        self.day_count_convention = day_count_convention.lower()
        self.schedule = []
        
        if self.day_count_convention not in ['actual_365', '30_360']:
            raise ValueError("day_count_convention must be either 'actual_365' or '30_360'")
        
    def calculate_schedule(self):
        monthly_rate = self.annual_interest_rate / 12
        total_payments = self.loan_term_years * 12
        current_principal = self.principal
        current_date = self.start_date
        
        # Calculate monthly payment using the standard loan payment formula
        if monthly_rate == 0:
            monthly_payment = current_principal / total_payments
        else:
            monthly_payment = (current_principal * monthly_rate * (1 + monthly_rate) ** total_payments) / \
                            ((1 + monthly_rate) ** total_payments - 1)
        
        # Process each payment
        remaining_balance = current_principal
        
        for payment_num in range(1, total_payments + 1):
            # Calculate next payment date first, handling month transitions correctly
            next_month = current_date + relativedelta(months=1)
            # Get the last day of next month
            last_day_of_next_month = (next_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            # Use the minimum of original day or last day of next month
            next_payment_day = min(current_date.day, last_day_of_next_month.day)
            next_payment_date = next_month.replace(day=next_payment_day)
            
            # Check for part payments in this period
            part_payment = 0
            part_payment_date = None
            
            # Find if there's a part payment in this period
            for pp in self.part_payments:
                pp_date = datetime.strptime(pp['date'], '%Y-%m-%d').date()
                
                if current_date <= pp_date < next_payment_date:
                    part_payment += float(pp['amount'])
                    part_payment_date = pp_date
            
            # Calculate interest based on the selected day count convention
            if self.day_count_convention == 'actual_365':
                # Actual/365: Actual days in period / 365 (or 366 for leap years)
                days_in_year = 366 if self._is_leap_year(current_date.year) else 365
                days_in_period = (next_payment_date - current_date).days
                interest = remaining_balance * self.annual_interest_rate * days_in_period / days_in_year
            else:  # 30/360
                # 30/360: Assume 30 days per month, 360 days per year
                # Formula: (360*(Y2-Y1)+30*(M2-M1)+(D2-D1))/360
                y1, m1, d1 = current_date.year, current_date.month, min(current_date.day, 30)
                y2, m2, d2 = next_payment_date.year, next_payment_date.month, min(next_payment_date.day, 30)
                days = max(0, (360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)))  # Ensure non-negative days
                interest = remaining_balance * self.annual_interest_rate * days / 360
            
            # Calculate principal and interest for the period
            
            # Apply part payment if any before calculating principal payment
            if part_payment > 0 and part_payment_date:
                # Apply part payment directly to principal
                remaining_balance = max(remaining_balance - part_payment, 0)
                
                # Add part payment entry
                self.schedule.append({
                    'payment_number': f"Part Payment {len([p for p in self.part_payments if p['date'] == part_payment_date.strftime('%Y-%m-%d')])}",
                    'date': part_payment_date.strftime('%Y-%m-%d'),
                    'payment': part_payment,
                    'principal': part_payment,
                    'interest': 0,
                    'remaining_balance': remaining_balance,
                    'is_part_payment': True
                })
            
            # Calculate principal payment after applying part payment
            # This ensures the principal payment is calculated based on the updated remaining balance
            principal_payment = min(monthly_payment - interest, remaining_balance)
            
            # Calculate final values for the period
            remaining_balance = max(remaining_balance - principal_payment, 0)
            total_payment = principal_payment + interest
            
            # Add to schedule
            self.schedule.append({
                'payment_number': payment_num,
                'date': next_payment_date.strftime('%Y-%m-%d'),
                'payment': total_payment,
                'principal': principal_payment,
                'interest': interest,
                'remaining_balance': max(remaining_balance, 0),
                'is_part_payment': False
            })
            
            # Update current date for next iteration
            current_date = next_payment_date
            
            # If loan is paid off early, break the loop
            if remaining_balance <= 0:
                break
                
        return self.schedule
    
    def _is_leap_year(self, year):
        """Check if a year is a leap year."""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    
    # Extract loan details
    principal = float(data['principal'])
    annual_interest_rate = float(data['interestRate'])
    loan_term_years = int(data['loanTerm'])
    start_date = data['startDate']
    
    # Extract part payments if any
    part_payments = []
    if data.get('hasPartPayment', False):
        part_payments = [{
            'amount': float(data['partPaymentAmount']),
            'date': data['partPaymentDate']
        }]
    
    # Get day count convention (default to 'actual_365' if not specified)
    day_count_convention = data.get('dayCountConvention', 'actual_365')
    
    # Calculate schedule
    try:
        loan = LoanSchedule(
            principal=principal,
            annual_interest_rate=annual_interest_rate,
            loan_term_years=loan_term_years,
            start_date=start_date,
            part_payments=part_payments,
            day_count_convention=day_count_convention
        )
        schedule = loan.calculate_schedule()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    return jsonify({
        'schedule': schedule,
        'summary': {
            'total_interest': sum(p['interest'] for p in schedule if not p.get('is_part_payment', False)),
            'total_payments': sum(p['payment'] for p in schedule if not p.get('is_part_payment', False)) + 
                             sum(p['payment'] for p in schedule if p.get('is_part_payment', False)),
            'loan_term_months': len([p for p in schedule if not p.get('is_part_payment', False)])
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
