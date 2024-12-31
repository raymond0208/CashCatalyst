import os
#from src import routes
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from typing_extensions import Annotated
from src.models import db, User, Transaction, InitialBalance
from src.forms import LoginForm, RegistrationForm
from src.anthropic_service import FinancialAnalytics
from src.upload_handler import process_upload
from src.utils import calculate_totals
from src.config import Config
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv
import traceback
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import matplotlib.pyplot as plt
import io
import base64
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.dates import MonthLocator, DateFormatter
import matplotlib.ticker as ticker
from datetime import datetime
import calendar

#load Anthropic LLM API key and other variables in .env
load_dotenv

# Ensure instance folder exists
instance_path = os.path.join(os.path.dirname(__file__),'instance')
os.makedirs(instance_path, exist_ok=True)

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all
    
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    #return User.query.get(int(user_id))
    return db.session.get(User, int(user_id))

#All routes in app
@app.route('/',methods=['GET','POST'])
@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    user_status = "Logged In"
    page = request.args.get('page', 1, type=int)
    per_page = 8

    if request.method == 'POST':
        # Handle adding transactions
        new_transaction = Transaction(
            date=request.form.get('date'),
            description=request.form.get('description'),
            amount=float(request.form.get('amount')),
            type=request.form.get('type')
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully', 'success')
        return redirect(url_for('home'))

    paginated_transactions = Transaction.query.order_by(Transaction.date.desc()).paginate(page=page, per_page=per_page)
    all_transactions = Transaction.query.all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

    total_cfo, total_cfi, total_cff = calculate_totals(all_transactions)
    balance = initial_balance + total_cfo + total_cfi + total_cff

    return render_template('home.html', transactions=paginated_transactions, balance=balance, initial_balance=initial_balance,
                           total_cfo=total_cfo, total_cfi=total_cfi, total_cff=total_cff, user=current_user, status=user_status)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=True)
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register',methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user_exists = User.query.filter_by(username=form.username.data).first()
        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if request.method == 'POST':
        transaction.date = request.form['date']
        transaction.description = request.form['description']
        transaction.amount = float(request.form['amount'])
        transaction.type = request.form['type']
        db.session.commit()
        flash('Transaction Updated Successfully', 'success')
        return redirect(url_for('home'))
    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    flash('Your Transaction Deleted!', 'danger')
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_route():
    if request.method == 'GET':
        return render_template('upload.html')
    elif request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        try:
            result = process_upload(file)
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in upload_file: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/set-initial-balance', methods=['POST'])
@login_required
def set_initial_balance():
    initial_balance_value = float(request.form.get('initial_balance'))
    initial_balance_record = InitialBalance.query.first()
    if initial_balance_record:
        initial_balance_record.balance = initial_balance_value
    else:
        initial_balance_record = InitialBalance(balance=initial_balance_value)
        db.session.add(initial_balance_record)
    db.session.commit()
    flash('Initial balance set successfully', 'success')
    return redirect(url_for('home'))

@app.route('/export/<file_type>')
@login_required
def export(file_type):
    transactions = Transaction.query.all()
    data = [{
        'Date': transaction.date,
        'Description': transaction.description,
        'Amount': transaction.amount,
        'Type': transaction.type
    } for transaction in transactions]

    df = pd.DataFrame(data)

    if file_type == 'csv':
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='transactions.csv')
    elif file_type == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Transactions')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                         as_attachment=True, download_name='transactions.xlsx')
    else:
        flash('Invalid file type requested.', 'danger')
        return redirect(url_for('home'))

@app.route('/save_transactions', methods=['POST'])
@login_required
def save_transactions():
    data = request.json
    try:
        for item in data:
            new_transaction = Transaction(
                date=item['date'],
                description=item['description'],
                amount=float(item['amount']),
                type=item['type']
            )
            db.session.add(new_transaction)
        db.session.commit()
        return jsonify({'message': 'Transactions saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

@app.route('/balance-by-date', methods=['POST'])
@login_required
def balance_by_date():
    input_date = request.form.get('date')
    transactions = Transaction.query.filter(Transaction.date <= input_date).all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0
    total_cfo, total_cfi, total_cff = calculate_totals(transactions)
    balance_sum = initial_balance + total_cfo + total_cfi + total_cff
    return jsonify({
        'input_date': input_date,
        'balance_sum': balance_sum
    })
    
@app.route('/forecast', methods=['GET'])
@login_required
def forecast():
    try:
        # Get transaction data
        transactions = Transaction.query.order_by(Transaction.date).all()
        if not transactions:
            return jsonify({'error': 'No transaction data available'}), 400

        initial_balance_record = InitialBalance.query.first()
        initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

        # Calculate current balance and totals
        total_cfo, total_cfi, total_cff = calculate_totals(transactions)
        current_balance = initial_balance + total_cfo + total_cfi + total_cff

        # Format transaction history for analysis
        transaction_history = [
            {
                'date': t.date.strftime('%Y-%m-%d') if isinstance(t.date, datetime) else t.date,
                'amount': float(t.amount),
                'type': t.type
            } for t in transactions
        ]

        # Mock working capital data
        working_capital = {
            'current_assets': current_balance if current_balance > 0 else 0,
            'current_liabilities': abs(current_balance) if current_balance < 0 else 0,
            'cash': current_balance if current_balance > 0 else 0
        }

        # Initialize FinancialAnalytics and generate analysis
        api_key = current_app.config.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({'error': 'API key not configured'}), 500

        analytics = FinancialAnalytics(api_key)
        analysis_result = analytics.generate_advanced_financial_analysis(
            initial_balance=initial_balance,
            current_balance=current_balance,
            transaction_history=transaction_history,
            working_capital=working_capital
        )

        return jsonify(analysis_result)

    except ValueError as ve:
        app.logger.error(f"Configuration error: {str(ve)}")
        return jsonify({'error': str(ve)}), 500
    except Exception as e:
        app.logger.error(f"Failed to generate analysis: {str(e)}")
        app.logger.exception("Detailed traceback:")
        return jsonify({'error': 'Failed to generate analysis'}), 500

@app.route('/generate_cashflow_statement', methods=['GET'])
@login_required
def generate_cashflow_statement_route():
    try:
        transactions = Transaction.query.order_by(Transaction.date).all()
        if not transactions:
            app.logger.warning("No transactions found when generating cash flow statement")
            return jsonify({'error': 'No transactions found'}), 400

        initial_balance_record = InitialBalance.query.first()
        initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

        start_date = transactions[0].date
        end_date = transactions[-1].date

        transaction_data = "\n".join([f"Date: {t.date}, Description: {t.description}, Amount: {t.amount}, Type: {t.type}" for t in transactions])

        app.logger.info(f"Generating cash flow statement for period {start_date} to {end_date}")
        
        statement_data,ending_balance = FinancialAnalytics.generate_cashflow_statement(initial_balance, start_date, end_date, transaction_data)
        
        if not statement_data:
            app.logger.error("generate_cashflow_statement returned None")
            return jsonify({'error': 'Failed to generate statement: No data returned'}), 500

        app.logger.info("Cash flow statement generated sucessfully")
        app.logger.debug(f"Statement data: {statement_data}")

        app.logger.info("Cash flow statement generated successfully")
        app.logger.debug(f"Statement data: {statement_data}")

        # Create a new workbook and select the active sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Cash Flow Statement"

        # Set column widths
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 15

        # Add title
        ws['A1'] = f"Cash Flow Statement - {start_date} to {end_date}"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:B1')

        # Add headers
        headers = ['Category', 'Amount']
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")

        # Helper function to add a row with formatting
        def add_row(row, category, amount, is_total=False, indent=0):
            ws.cell(row=row, column=1, value=category).alignment = Alignment(indent=indent)
            ws.cell(row=row, column=2, value=amount)
            if is_total:
                for col in range(1, 3):
                    ws.cell(row=row, column=col).font = Font(bold=True)

        # Add Beginning Cash Balance
        row = 4
        add_row(row, "Beginning Cash Balance", initial_balance, True)
        row += 2

        # Process and add data for each category
        categories = ['CFO', 'CFI', 'CFF']
        for category in categories:
            ws.cell(row=row, column=1, value=f"Cash Flow from {'Operating' if category == 'CFO' else 'Investing' if category == 'CFI' else 'Financing'} Activities ({category})")
            ws.cell(row=row, column=1).font = Font(bold=True)
            ws.cell(row=row, column=1).fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
            row += 1

            category_total = 0
            for item in statement_data:
                if item['Category'] == category:
                    add_row(row, item['Subcategory'], item['Amount'], indent=1)
                    category_total += item['Amount']
                    row += 1

            add_row(row, f"Net Cash from {'Operating' if category == 'CFO' else 'Investing' if category == 'CFI' else 'Financing'}", category_total, True)
            row += 2

        # Add Total Net Cash Flow
        total_net_cash_flow = sum(item['Amount'] for item in statement_data)
        add_row(row, "Total Net Cash Flow", total_net_cash_flow, True)
        row += 2

        # Add Ending Cash Balance
        ending_balance = initial_balance + total_net_cash_flow
        add_row(row, "Ending Cash Balance", ending_balance, True)

        # Apply currency formatting to amount column
        for row in ws['B4:B' + str(ws.max_row)]:
            for cell in row:
                cell.number_format = '#,##0.00'

        # Apply right alignment to amount column
        for row in ws['B1:B' + str(ws.max_row)]:
            for cell in row:
                cell.alignment = Alignment(horizontal='right')

        # Add borders
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=2):
            for cell in row:
                cell.border = thin_border

        # Save to BytesIO object
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        app.logger.info("Excel file created successfully")
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='cash_flow_statement.xlsx'
        )
    except Exception as e:
        app.logger.error(f"Failed to generate cash flow statement: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Failed to generate cash flow statement: {str(e)}'}), 500
    
# Generate monthly chart function    
def generate_monthly_balance_chart():
    transactions = Transaction.query.order_by(Transaction.date).all()
    initial_balance_record = InitialBalance.query.first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

    monthly_balances = []
    current_balance = initial_balance
    current_month = None

    for transaction in transactions:
        transaction_date = datetime.strptime(transaction.date, '%Y-%m-%d').date()
        
        if current_month != transaction_date.replace(day=1):
            if current_month:
                last_day = calendar.monthrange(current_month.year, current_month.month)[1]
                monthly_balances.append({
                    'date': current_month.replace(day=last_day),
                    'balance': current_balance
                })
            current_month = transaction_date.replace(day=1)

        current_balance += transaction.amount

    # Add the last month's balance
    if current_month:
        last_day = calendar.monthrange(current_month.year, current_month.month)[1]
        monthly_balances.append({
            'date': current_month.replace(day=last_day),
            'balance': current_balance
        })

    # Create the chart
    fig = Figure(figsize=(12, 6))
    axis = fig.add_subplot(1, 1, 1)
    dates = [balance['date'] for balance in monthly_balances]
    balances = [balance['balance'] for balance in monthly_balances]
    axis.plot(dates, balances, marker='o')  # Added markers for each data point

    # Improve Y-axis formatting
    def currency_formatter(x, p):
        return f'${x:,.0f}'
    
    axis.yaxis.set_major_formatter(ticker.FuncFormatter(currency_formatter))
    
    # Adjust Y-axis ticks for better readability
    axis.yaxis.set_major_locator(ticker.MaxNLocator(nbins=10, integer=True))
    
    # Format X-axis to show dates nicely
    axis.xaxis.set_major_locator(MonthLocator())
    axis.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))

    axis.set_title('Monthly Balance', fontsize=16, fontweight='bold')
    axis.set_xlabel('Date', fontsize=12)
    axis.set_ylabel('Balance ($)', fontsize=12)
    axis.tick_params(axis='both', which='major', labelsize=10)
    axis.tick_params(axis='x', rotation=45)
    
    # Add gridlines for better readability
    axis.grid(True, linestyle='--', alpha=0.7)
    
    # Add some padding to the y-axis
    ylim = axis.get_ylim()
    axis.set_ylim([ylim[0] - (ylim[1] - ylim[0]) * 0.1, ylim[1] + (ylim[1] - ylim[0]) * 0.1])

    fig.tight_layout()

    # Convert plot to PNG image
    png_image = io.BytesIO()
    FigureCanvas(fig).print_png(png_image)
    
    # Encode PNG image to base64 string
    png_image_b64_string = "data:image/png;base64,"
    png_image_b64_string += base64.b64encode(png_image.getvalue()).decode('utf8')

    return png_image_b64_string

#Map plotting chart
@app.route('/monthly-balances', methods=['GET'])
@login_required
def monthly_balances():
    try:
        app.logger.info("Starting to generate monthly balance chart")
        chart_image = generate_monthly_balance_chart()
        app.logger.info("Chart generated successfully")
        return jsonify({'chart_image': chart_image})
    except Exception as e:
        app.logger.error(f"Error generating monthly balance chart: {str(e)}")
        app.logger.exception("Detailed traceback:")
        return jsonify({'error': 'Failed to generate chart: ' + str(e)}), 500

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)