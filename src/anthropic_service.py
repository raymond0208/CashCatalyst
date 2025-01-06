from anthropic import Anthropic
from flask import current_app
import json
import ast
from datetime import datetime,timedelta
import numpy as np
from scipy import stats

class FinancialAnalytics:
    def __init__(self, api_key):
        self.anthropic = Anthropic(api_key=api_key)
        self.seasonal_periods = 12 # Monthly seasonality

    def analyze_patterns(self, transaction_history):
        """Analyze transaction patterns and seasonality"""
        amounts = [t['amount'] for t in transaction_history]
        dates = [datetime.strptime(t['date'], '%Y-%m-%d') for t in transaction_history]

        #Detect seasonality
        if len(amounts) >= self.seasonal_periods * 2:
            seasonal_decomposition = stats.seasonal_decompose(amounts, period=self.seasonal_periods)
            seasonal_pattern = seasonal_decomposition.seasonal.tolist()
        else:
            seasonal_pattern = []

        return {
            'seasonal_pattern': seasonal_pattern,
            'trend': np.polyfit(range(len(amounts)), amounts, 1).tolist(),
            'volatility': np.std(amounts)
        }
    
    def calculate_risk_metrics(self, cash_flows, working_capital):
        """Calculate various risk metrics"""
        # Avoid division by zero for liquidity ratio
        current_liabilities = working_capital['current_liabilities']
        liquidity_ratio = (working_capital['current_assets'] / current_liabilities 
                          if current_liabilities > 0 else 9999.99)
        
        # Calculate burn rate (average of negative cash flows)
        negative_flows = [cf for cf in cash_flows if cf < 0]
        burn_rate = float(abs(sum(negative_flows)) / len(cash_flows)) if negative_flows else 0
        
        # Avoid division by zero for runway months
        min_cash_flow = min(cash_flows) if cash_flows else 0
        runway_months = (working_capital['cash'] / abs(min_cash_flow) 
                        if min_cash_flow < 0 else 999.99)
        
        return {
            'liquidity_ratio': float(liquidity_ratio),
            'cash_flow_volatility': float(np.std(cash_flows) if cash_flows else 0),
            'burn_rate': float(burn_rate),
            'runway_months': float(runway_months)
        }

    def generate_advanced_financial_analysis(self, initial_balance, current_balance, transaction_history, working_capital):
        patterns = self.analyze_patterns(transaction_history)
        risk_metrics = self.calculate_risk_metrics(
            [t['amount'] for t in transaction_history],
            working_capital
        )

        prompt = f"""As a financial analyst, provide a concise analysis of the following financial data:

        Financial Metrics:
        - Initial Balance: ${initial_balance}
        - Current Balance: ${current_balance}
        - Liquidity Ratio: {risk_metrics['liquidity_ratio']:.2f}
        - Cash Runway: {risk_metrics['runway_months']:.2f} months

        Pattern Analysis:
        - Seasonal Pattern: {patterns['seasonal_pattern']}
        - Trend: {patterns['trend']}
        - Volatility: {patterns['volatility']:.2f}

        Please provide a brief, bullet-point analysis covering:
        1. Pattern Recognition Analysis (identify recurring patterns and anomalies)
        2. Risk Assessment (evaluate liquidity and cash flow risks)
        3. Seasonal Trends (analyze monthly/quarterly patterns)
        4. Working Capital Optimization (suggest improvements)
        5. 90-day Forecast (based on historical patterns)

        Format the response with clear sections and actionable insights."""

        try:
            message = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            analysis_result = {
                'ai_analysis': message.content[0].text,
                'patterns': patterns,
                'risk_metrics': risk_metrics,
                'forecasts': self.generate_forecasts(transaction_history, patterns)
            }
            return analysis_result
        except Exception as e:
            current_app.logger.error(f"Analysis failed: {str(e)}")
            raise
    
    def generate_forecasts(self, transaction_history, patterns):
        """Generate detailed forecasts using pattern analysis"""
        recent_transactions = transaction_history[-90:]  # Last 90 days
        trend = patterns['trend']
        seasonal_pattern = patterns['seasonal_pattern']
        
        forecasts = {
            '30_days': [],
            '60_days': [],
            '90_days': []
        }
        
        # Calculate base trend
        slope, intercept = trend
        
        # Generate daily forecasts for next 90 days
        for day in range(90):
            # Calculate trend component
            trend_value = slope * (len(recent_transactions) + day) + intercept
            
            # Add seasonal component if available
            seasonal_value = 0
            if seasonal_pattern:
                seasonal_idx = day % len(seasonal_pattern)
                seasonal_value = seasonal_pattern[seasonal_idx]
            
            # Combine trend and seasonality
            forecast_value = trend_value + seasonal_value
            
            # Add to appropriate forecast period
            if day < 30:
                forecasts['30_days'].append(forecast_value)
            if day < 60:
                forecasts['60_days'].append(forecast_value)
            forecasts['90_days'].append(forecast_value)
        
        return forecasts

    def generate_cashflow_statement(self, initial_balance, start_date, end_date, transaction_data):
        """Generate a cash flow statement with strict categorization and proper financial reporting structure."""
        # Parse transaction data into a structured format
        transactions = []
        for line in transaction_data.split('\n'):
            if line.strip():
                parts = line.split(', ')
                transaction = {}
                for part in parts:
                    key, value = part.split(': ', 1)
                    transaction[key.lower()] = value
                transactions.append(transaction)

        # Define the categorization structure exactly matching utils.py
        categories = {
            'CFO': {
                'types': ["Cash-customer", "Salary-suppliers", "Income-tax", "Other-cfo"],
                'items': []
            },
            'CFI': {
                'types': ["Buy-property-equipments", "Sell-property-equipments", "Buy-investment", "Sell-investment", "Other-cfi"],
                'items': []
            },
            'CFF': {
                'types': ["Issue-shares", "borrowings", "Repay-borrowings", "Pay-dividends", "Interest-paid", "Other-cff"],
                'items': []
            }
        }

        # Categorize transactions strictly by type
        for t in transactions:
            t_type = t['type']
            t_amount = float(t['amount'])
            t_date = t['date']
            t_desc = t['description']

            for category, info in categories.items():
                if t_type in info['types']:
                    info['items'].append({
                        'type': t_type,
                        'amount': t_amount,
                        'date': t_date,
                        'description': t_desc
                    })

        # Calculate totals
        statement_data = []
        category_totals = {'CFO': 0, 'CFI': 0, 'CFF': 0}

        # Process each category
        for category, info in categories.items():
            # Group transactions by type within each category
            type_totals = {}
            for item in info['items']:
                t_type = item['type']
                if t_type not in type_totals:
                    type_totals[t_type] = 0
                type_totals[t_type] += item['amount']

            # Add each type's total to the statement
            for t_type, total in type_totals.items():
                statement_data.append({
                    'Category': category,
                    'Subcategory': t_type,
                    'Amount': total
                })
                category_totals[category] += total

        # Calculate final totals
        total_net_cash_flow = sum(category_totals.values())
        ending_balance = initial_balance + total_net_cash_flow

        return statement_data, ending_balance

def parse_response(response):
    lines = response.strip().split('\n')
    statement_data = []
    totals = {}

    for line in lines:
        try:
            if ':' not in line:
                continue
            
            if line.count(':') == 2:  # This is a transaction line
                category, subcategory_and_amount = line.split(':', 1)
                subcategory, amount_str = subcategory_and_amount.rsplit(':', 1)
                
                category = category.strip()
                subcategory = subcategory.strip()
                amount = parse_amount(amount_str)
                
                statement_data.append({
                    'Category': category,
                    'Subcategory': subcategory,
                    'Amount': amount
                })
            elif line.count(':') == 1:  # This is a total line
                key, value_str = line.split(':')
                key = key.strip()
                value = parse_amount(value_str)
                totals[key] = value
        except Exception as e:
            current_app.logger.warning(f"Error parsing line '{line}': {str(e)}")

    if not statement_data:
        current_app.logger.error("No valid statement data found in response")
    if not totals:
        current_app.logger.error("No valid totals found in response")

    return statement_data, totals

def parse_amount(amount_str):
    try:
        return float(amount_str.replace('$', '').replace(',', '').strip())
    except ValueError:
        current_app.logger.warning(f"Could not parse amount: {amount_str}")
        return 0.0