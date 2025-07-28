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
            
            # Initialize variables for period calculation
            period_interest = 0
            current_period_start = current_date
            temp_balance = remaining_balance
            
            # Get all part payments in this period, including those on the next payment date
            period_part_payments = []
            for pp in self.part_payments:
                pp_date = datetime.strptime(pp['date'], '%Y-%m-%d').date()
                if current_date <= pp_date <= next_payment_date:
                    period_part_payments.append({
                        'date': pp_date,
                        'amount': float(pp['amount']),
                        'original_index': len([p for p in self.part_payments if p['date'] == pp['date'] and 
                                            datetime.strptime(p['date'], '%Y-%m-%d').date() < pp_date]) + 1
                    })
            
            # Sort part payments by date
            period_part_payments.sort(key=lambda x: (x['date'], x.get('original_index', 0)))
            
            # Add the end of period as a marker
            period_part_payments.append({'date': next_payment_date, 'amount': 0})
            
            # Calculate interest for each sub-period
            for i, pp in enumerate(period_part_payments):
                end_date = pp['date']
                
                # Skip if this is the same as the start date (shouldn't happen with sorted list)
                if end_date <= current_period_start:
                    continue
                
                # Calculate days in sub-period
                if self.day_count_convention == 'actual_365':
                    days_in_year = 366 if self._is_leap_year(current_period_start.year) else 365
                    days_in_subperiod = (end_date - current_period_start).days
                    subperiod_interest = temp_balance * self.annual_interest_rate * days_in_subperiod / days_in_year
                else:  # 30/360
                    y1, m1, d1 = current_period_start.year, current_period_start.month, min(current_period_start.day, 30)
                    y2, m2, d2 = end_date.year, end_date.month, min(end_date.day, 30)
                    days = max(0, (360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)))
                    subperiod_interest = temp_balance * self.annual_interest_rate * days / 360
                
                period_interest += subperiod_interest
                
                # Apply part payment to temp balance for next sub-period
                if pp['amount'] > 0:
                    # Add part payment entry
                    payment_number = pp.get('original_index', 1)
                    self.schedule.append({
                        'payment_number': f"Part Payment {payment_number}",
                        'date': end_date.strftime('%Y-%m-%d'),
                        'payment': pp['amount'],
                        'principal': pp['amount'],
                        'interest': 0,
                        'remaining_balance': temp_balance - pp['amount'],
                        'is_part_payment': True
                    })
                    # Update balance after part payment
                    temp_balance = max(temp_balance - pp['amount'], 0)
                
                current_period_start = end_date
            
            # Update the actual remaining balance after all part payments
            remaining_balance = temp_balance
            interest = period_interest
            
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
    for pp in data.get('partPayments', []):
        try:
            part_payments.append({
                'amount': float(pp['amount']),
                'date': pp['date']
            })
        except (ValueError, KeyError):
            # Skip invalid part payments
            continue
    
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
