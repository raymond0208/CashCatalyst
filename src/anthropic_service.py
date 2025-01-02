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
        
        # Avoid division by zero for runway months
        min_cash_flow = min(cash_flows) if cash_flows else 0
        runway_months = (working_capital['cash'] / abs(min_cash_flow) 
                        if min_cash_flow < 0 else 999.99)
        
        return {
            'liquidity_ratio': float(liquidity_ratio),
            'cash_flow_volatility': float(np.std(cash_flows) if cash_flows else 0),
            'burn_rate': float(sum(cf for cf in cash_flows if cf < 0) / len(cash_flows) if cash_flows else 0),
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
        api_key = current_app.config.get('ANTHROPIC_API_KEY')
        
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in the application configuration")
        
        try:
            anthropic = Anthropic(api_key=api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")

        prompt = f"""As a financial expert, generate a detailed cash flow statement based on the following data:

        Initial Balance: ${initial_balance}
        Start Date: {start_date}
        End Date: {end_date}

        Transaction Data:
        {transaction_data}

        Please follow these strict categorization rules:
        
        Cash Flow from Operations (CFO):
        - Cash from customers
        - Salary and supplier payments
        - Income tax payments
        - Other operating activities

        Cash Flow from Investing (CFI):
        - Purchase/sale of property and equipment
        - Purchase/sale of investments
        - Other investing activities

        Cash Flow from Financing (CFF):
        - Bank loans and repayments
        - Interest payments
        - Share issuance
        - Dividend payments
        - Other financing activities

        Important: Salary and supplier payments MUST be categorized under CFO, not CFF.

        Present the data in a clear, structured format. Use a simple list format with each item on a new line, like this:

        CFO: Cash from customers: 1000
        CFO: Payments to suppliers: -500
        CFI: Purchase of equipment: -2000
        CFF: Bank loan: 5000
        CFF: Interest paid: -200
        ...

        After listing all items, provide the totals and ending balance in the same format:

        Total CFO: 500
        Total CFI: -2000
        Total CFF: 4800
        Overall Net Cash Flow: 3300
        Ending Cash Balance: 4300

        Ensure all calculations are accurate and consistent with the provided transaction data."""

        try:
            message = anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response = message.content[0].text

            # Log the complete API response
            current_app.logger.info(f"Complete API response:\n{response}")

            # Parse the response
            statement_data, totals = parse_response(response)

            if not statement_data:
                current_app.logger.error("Failed to parse API response")
                return {'error': 'Parsing failed', 'raw_response': response}, None

            # Calculate ending balance
            ending_balance = totals.get('Ending Cash Balance')
            if ending_balance is None:
                ending_balance = initial_balance + totals.get('Overall Net Cash Flow', 0)

            current_app.logger.info(f"Cash Flow Statement Calculation: {totals}")
            current_app.logger.info(f"Ending Balance: {ending_balance}")

            return statement_data, ending_balance

        except Exception as e:
            current_app.logger.error(f"Error generating cash flow statement: {str(e)}")
            current_app.logger.error(f"Error details: {type(e).__name__}, {str(e)}")
            raise

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