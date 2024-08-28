from anthropic import Anthropic
from flask import current_app

def generate_financial_analysis(initial_balance, current_balance, total_cfo, total_cfi, total_cff, transaction_data):
    api_key = current_app.config.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in the application configuration")
    
    if api_key == 'your-fallback-api-key-here':
        raise ValueError("Please replace the fallback API key with your actual Anthropic API key")
    
    try:
        anthropic = Anthropic(api_key=api_key)
    except Exception as e:
        raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")

    prompt = f"""As a financial analyst, provide a concise analysis of the following financial data:

    Initial Balance: ${initial_balance}
    Current Balance: ${current_balance}
    Total CFO: ${total_cfo}
    Total CFI: ${total_cfi}
    Total CFF: ${total_cff}

    Transaction Data:
    {transaction_data}

    Please provide a brief, bullet-point analysis covering:
    - Financial health analysis based on CFO, CFI, and CFF (2-3 points)
    - 30, 60, and 90-day forecast for CFO, CFI, and CFF (compact table format)
    - Projected total balances (compact table format)
    - Key recommendations (2-3 points)

    Limit each bullet point to 20 words or less. Use compact tables where applicable."""

    try:
        message = anthropic.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        current_app.logger.error(f"Error calling Anthropic API: {str(e)}")
        raise