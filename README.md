# Loan Repayment Calculator with Part Payment

A web-based loan repayment calculator that supports part payments, allowing users to see how making additional payments affects their loan schedule.

## Features

- Calculate monthly loan payments with amortization schedule
- Support for part payments with custom amounts and dates
- Handles broken periods (partial periods due to part payments)
- Visual representation of payment breakdown
- Responsive design that works on desktop and mobile devices

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd loan_repayment
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the Flask development server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

3. Enter your loan details:
   - Loan amount
   - Annual interest rate
   - Loan term in years
   - Start date
   - (Optional) Enable part payment and enter the amount and date

4. Click "Calculate Schedule" to see the detailed repayment plan.

## How Part Payments Work

When you make a part payment:
- The payment is applied directly to the principal on the specified date
- The remaining loan term is recalculated based on the new principal
- The interest for the period is calculated based on the actual number of days between payments
- The amortization schedule is updated to reflect the new payment amounts

## Dependencies

- Python 3.7+
- Flask
- python-dateutil

## License

This project is open source and available under the [MIT License](LICENSE).
