def calculate_totals(transactions):
    cfo_types = ["Cash-customer", "Salary-suppliers", "Income-tax", "Other-cfo"]
    cfi_types = ["Buy-property-equipments", "Sell-property-equipments", "Buy-investment", "Sell-investment", "Other-cfi"]
    cff_types = ["Issue-shares", "borrowings", "Repay-borrowings", "Pay-dividends", "Interest-paid", "Other-cff"]

    total_cfo = sum(t.amount for t in transactions if t.type in cfo_types)
    total_cfi = sum(t.amount for t in transactions if t.type in cfi_types)
    total_cff = sum(t.amount for t in transactions if t.type in cff_types)

    return total_cfo, total_cfi, total_cff

def calculate_burn_rate(transactions, months=3):
    """
    Calculate burn rate based on recent negative cash flows.
    
    Args:
        transactions: List of Transaction objects
        months: Number of months to consider for calculation (default: 3)
    
    Returns:
        burn_rate: Average monthly negative cash flow (as a positive number)
    """
    from datetime import datetime, timedelta
    
    if not transactions:
        return 0
        
    # Sort transactions by date (most recent first)
    sorted_transactions = sorted(transactions, key=lambda t: t.date, reverse=True)
    
    # Get the most recent date
    most_recent_date = sorted_transactions[0].date
    if isinstance(most_recent_date, str):
        most_recent_date = datetime.strptime(most_recent_date, '%Y-%m-%d')
    
    # Calculate cutoff date (3 months prior)
    cutoff_date = most_recent_date - timedelta(days=months*30)
    if isinstance(cutoff_date, datetime):
        cutoff_date = cutoff_date.strftime('%Y-%m-%d')
    
    # Filter transactions within the time period
    recent_transactions = []
    for t in sorted_transactions:
        t_date = t.date
        if isinstance(t_date, str):
            t_date = datetime.strptime(t_date, '%Y-%m-%d')
            if t_date >= datetime.strptime(cutoff_date, '%Y-%m-%d'):
                recent_transactions.append(t)
        else:
            if t_date >= cutoff_date:
                recent_transactions.append(t)
    
    # Calculate total negative cash flow (expenses)
    negative_flows = [t.amount for t in recent_transactions if t.amount < 0]
    
    if negative_flows:
        # Calculate monthly burn rate (average monthly expense)
        burn_rate = abs(sum(negative_flows)) / months
        return burn_rate
    
    # Return 0 if no negative transactions
    return 0

def calculate_runway(current_balance, burn_rate):
    """
    Calculate runway (months remaining) based on current balance and burn rate.
    
    Args:
        current_balance: Current cash balance
        burn_rate: Monthly burn rate (positive number)
    
    Returns:
        runway_months: Number of months until cash runs out
    """
    if burn_rate <= 0:
        return float('inf')  # Infinite runway if no burn
    
    runway_months = current_balance / burn_rate
    return runway_months