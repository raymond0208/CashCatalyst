import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from typing_extensions import Annotated
from src.models import db, User, Transaction, InitialBalance, UserPreferences
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
from flask_migrate import Migrate

#load Anthropic LLM API key and other variables in .env
load_dotenv()

# Ensure instance folder exists
instance_path = os.path.join(os.path.dirname(__file__),'instance')
os.makedirs(instance_path, exist_ok=True)

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config.from_object(Config)

db.init_app(app)

migrate = Migrate(app, db)

with app.app_context():
    # Create tables only if they don't exist
    db.create_all()

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
            user_id=current_user.id,
            date=request.form.get('date'),
            description=request.form.get('description'),
            amount=float(request.form.get('amount')),
            type=request.form.get('type')
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully', 'success')
        return redirect(url_for('home'))

    # Filter transactions by current user
    paginated_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).paginate(page=page, per_page=per_page)
    all_transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    # Get initial balance for current user
    initial_balance_record = InitialBalance.query.filter_by(user_id=current_user.id).first()
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
            new_preferences = UserPreferences(user_id=new_user.id)
            db.session.add(new_preferences)
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
    try:
        amount = float(request.form.get('initial_balance'))
        
        # Get or create initial balance record for the user
        initial_balance = InitialBalance.query.filter_by(user_id=current_user.id).first()
        if initial_balance:
            initial_balance.balance = amount
        else:
            initial_balance = InitialBalance(user_id=current_user.id, balance=amount)
            db.session.add(initial_balance)
            
        db.session.commit()
        flash('Initial balance set successfully', 'success')
    except ValueError:
        flash('Please enter a valid number for the initial balance', 'danger')
    except Exception as e:
        flash(f'Error setting initial balance: {str(e)}', 'danger')
        
    return redirect(url_for('cash_overview'))

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
                user_id=current_user.id,
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
    try:
        date_str = request.form.get('date')
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get initial balance
        initial_balance = InitialBalance.query.filter_by(user_id=current_user.id).first()
        initial_amount = initial_balance.balance if initial_balance else 0
        
        # Get all transactions up to the target date
        transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.date <= target_date
        ).all()
        
        # Calculate totals
        total_cfo, total_cfi, total_cff = calculate_totals(transactions)
        balance = initial_amount + total_cfo + total_cfi + total_cff
        
        return jsonify({
            'success': True,
            'balance': balance,
            'date': date_str
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    
@app.route('/forecast', methods=['GET'])
@login_required
def forecast():
    try:
        # Get all transactions for the current user
        transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date).all()
        
        if not transactions:
            return jsonify({
                'error': 'No transactions found. Please add some transactions first.'
            }), 400
            
        # Convert transactions to a format suitable for analysis
        transaction_data = [{
            'date': t.date.strftime('%Y-%m-%d'),
            'amount': t.amount,
            'type': t.type,
            'description': t.description
        } for t in transactions]
        
        # Initialize financial analytics
        analytics = FinancialAnalytics()
        
        # Get analysis results
        analysis_results = analytics.analyze_transactions(transaction_data)
        
        # Calculate risk metrics
        total_inflow = sum(t.amount for t in transactions if t.amount > 0)
        total_outflow = abs(sum(t.amount for t in transactions if t.amount < 0))
        liquidity_ratio = total_inflow / total_outflow if total_outflow != 0 else 0
        
        # Calculate runway (in months) based on average monthly burn rate
        monthly_burn = total_outflow / max(1, (transactions[-1].date - transactions[0].date).days / 30)
        current_balance = sum(t.amount for t in transactions)
        runway_months = current_balance / monthly_burn if monthly_burn != 0 else 0
        
        return jsonify({
            'success': True,
            'ai_analysis': analysis_results.get('insights', 'No insights available'),
            'patterns': {
                'seasonal_pattern': analysis_results.get('seasonal_pattern', [0] * 12)  # 12 months
            },
            'forecasts': {
                '90_days': analysis_results.get('forecast', [0] * 90)  # 90 days forecast
            },
            'risk_metrics': {
                'liquidity_ratio': liquidity_ratio,
                'runway_months': runway_months
            }
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/generate_cashflow_statement')
@login_required
def generate_cashflow_statement():
    try:
        # Get all transactions for the current user
        transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date).all()
        
        if not transactions:
            flash('No transactions found to generate statement', 'warning')
            return redirect(url_for('ai_analysis'))
        
        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Cash Flow Statement"
        
        # Add headers
        headers = ['Date', 'Description', 'Amount', 'Type', 'Category']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        # Add transactions
        for row, t in enumerate(transactions, 2):
            ws.cell(row=row, column=1, value=t.date.strftime('%Y-%m-%d'))
            ws.cell(row=row, column=2, value=t.description)
            ws.cell(row=row, column=3, value=t.amount)
            ws.cell(row=row, column=4, value=t.type)
            
            # Determine category based on type
            if 'cfo' in t.type.lower():
                category = 'Operating'
            elif 'cfi' in t.type.lower():
                category = 'Investing'
            else:
                category = 'Financing'
            ws.cell(row=row, column=5, value=category)
        
        # Add totals
        total_row = len(transactions) + 3
        ws.cell(row=total_row, column=1, value='Totals')
        ws.cell(row=total_row, column=1).font = Font(bold=True)
        
        # Calculate and add category totals
        categories = ['Operating', 'Investing', 'Financing']
        for col, category in enumerate(categories, 3):
            total = sum(t.amount for t in transactions if category.lower() in t.type.lower())
            cell = ws.cell(row=total_row, column=col)
            cell.value = total
            cell.font = Font(bold=True)
        
        # Auto-adjust column widths
        for col in range(1, 6):
            ws.column_dimensions[get_column_letter(col)].auto_size = True
        
        # Save to BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='cash_flow_statement.xlsx'
        )
        
    except Exception as e:
        flash(f'Error generating statement: {str(e)}', 'danger')
        return redirect(url_for('ai_analysis'))

# Generate monthly chart function    
def generate_monthly_balance_chart():
    # Get transactions for the current user
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date).all()
    
    # Get initial balance for the current user
    initial_balance_record = InitialBalance.query.filter_by(user_id=current_user.id).first()
    initial_balance = initial_balance_record.balance if initial_balance_record else 0.0

    monthly_balances = []
    current_balance = initial_balance
    current_month = None

    for transaction in transactions:
        transaction_date = transaction.date if isinstance(transaction.date, datetime) else datetime.strptime(transaction.date, '%Y-%m-%d')
        
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
    
    if monthly_balances:
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
        
        # Add some padding to the y-axis
        ylim = axis.get_ylim()
        axis.set_ylim([ylim[0] - (ylim[1] - ylim[0]) * 0.1, ylim[1] + (ylim[1] - ylim[0]) * 0.1])
    else:
        # If no data, show a message on the chart
        axis.text(0.5, 0.5, 'No transaction data available', 
                 horizontalalignment='center', verticalalignment='center',
                 transform=axis.transAxes, fontsize=14)
        axis.set_xticks([])
        axis.set_yticks([])

    axis.set_title('Monthly Balance', fontsize=16, fontweight='bold')
    axis.set_xlabel('Date', fontsize=12)
    axis.set_ylabel('Balance ($)', fontsize=12)
    axis.tick_params(axis='both', which='major', labelsize=10)
    axis.tick_params(axis='x', rotation=45)
    
    # Add gridlines for better readability
    axis.grid(True, linestyle='--', alpha=0.7)

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
    user_preferences = UserPreferences.query.filter_by(user_id=current_user.id).first()
    return render_template('settings.html', user_preferences=user_preferences)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.username = request.form.get('username')
    current_user.email = request.form.get('email')
    db.session.commit()
    flash('Profile updated successfully', 'success')
    return redirect(url_for('settings'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    if check_password_hash(current_user.password, request.form.get('current_password')):
        if request.form.get('new_password') == request.form.get('confirm_password'):
            current_user.password = generate_password_hash(request.form.get('new_password'))
            db.session.commit()
            flash('Password changed successfully', 'success')
        else:
            flash('New passwords do not match', 'danger')
    else:
        flash('Current password is incorrect', 'danger')
    return redirect(url_for('settings'))

@app.route('/update_modules', methods=['POST'])
@login_required
def update_modules():
    user_preferences = UserPreferences.query.filter_by(user_id=current_user.id).first()
    if not user_preferences:
        user_preferences = UserPreferences(user_id=current_user.id)
        db.session.add(user_preferences)
    user_preferences.modules = request.form.getlist('modules')
    db.session.commit()
    flash('Module preferences updated successfully', 'success')
    return redirect(url_for('settings'))

@app.context_processor
def utility_processor():
    def get_user_preferences():
        if current_user.is_authenticated:
            prefs = UserPreferences.query.filter_by(user_id=current_user.id).first()
            if not prefs:
                prefs = UserPreferences(user_id=current_user.id)
                db.session.add(prefs)
                db.session.commit()
            return prefs
        return None
    return dict(user_preferences=get_user_preferences())

@app.route('/cash-overview')
@login_required
def cash_overview():
    # Get or create initial balance for the current user
    initial_balance = InitialBalance.query.filter_by(user_id=current_user.id).first()
    if not initial_balance:
        initial_balance = InitialBalance(user_id=current_user.id, balance=0)
        db.session.add(initial_balance)
        db.session.commit()

    # Get all transactions for the current user
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    # Calculate totals
    total_cfo, total_cfi, total_cff = calculate_totals(transactions)
    balance = initial_balance.balance + total_cfo + total_cfi + total_cff

    return render_template('cash_overview.html', 
                         initial_balance=initial_balance.balance,
                         total_cfo=total_cfo, 
                         total_cfi=total_cfi, 
                         total_cff=total_cff, 
                         balance=balance)

@app.route('/cash-activities')
@login_required
def cash_activities():
    page = request.args.get('page', 1, type=int)
    per_page = 8
    
    # Get paginated transactions for the current user
    paginated_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('cash_activities.html', transactions=paginated_transactions)

@app.route('/ai-analysis')
@login_required
def ai_analysis():
    return render_template('ai_analysis.html')

@app.route('/create-transaction', methods=['POST'])
@login_required
def create_transaction():
    try:
        new_transaction = Transaction(
            user_id=current_user.id,
            date=request.form.get('date'),
            description=request.form.get('description'),
            amount=float(request.form.get('amount')),
            type=request.form.get('type')
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error adding transaction: ' + str(e), 'danger')
    
    return redirect(url_for('cash_activities'))

if __name__ == '__main__':
    app.run(debug=True)