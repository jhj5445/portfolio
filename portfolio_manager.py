import pandas as pd

class PortfolioManager:
    def __init__(self):
        pass

    def calculate_valuations(self, portfolio_df, prices):
        """
        Input: 
            portfolio_df: DataFrame with 'Ticker', 'Quantity'
            prices: Dictionary {ticker: price}
        Output:
            Updated DataFrame with 'Current_Price', 'Current_Value', 'Current_Weight'
            total_value: Float
        """
        df = portfolio_df.copy()
        
        # Map prices to the dataframe
        df['Current_Price'] = df['Ticker'].map(prices).fillna(0.0)
        
        # Calculate Current Value
        df['Current_Value'] = df['Quantity'] * df['Current_Price']
        
        total_value = df['Current_Value'].sum()
        
        # Calculate Current Weight
        if total_value > 0:
            df['Current_Weight'] = df['Current_Value'] / total_value
        else:
            df['Current_Weight'] = 0.0
            
        return df, total_value

    def calculate_rebalancing(self, portfolio_df, total_value, investment_amount=0):
        """
        Calculates rebalancing needs.
        Input:
            portfolio_df: DataFrame with 'Ticker', 'Current_Price', 'Target_Weight'
            total_value: Current total value of the portfolio
            investment_amount: Additional cash to invest (default 0)
        Output:
            DataFrame with 'Target_Value', 'Difference', 'Action', 'Units_To_Trade'
        """
        df = portfolio_df.copy()
        
        new_total_value = total_value + investment_amount
        
        # Target Value per asset
        df['Target_Value'] = new_total_value * df['Target_Weight']
        
        # Difference (Target - Current)
        # Note: Current value is based on existing holdings. 
        # If we have cash, 'Current_Value' doesn't include it, but 'Target_Value' does distributions of it.
        df['Difference'] = df['Target_Value'] - df['Current_Value']
        
        # Calculate Units to Trade
        # Avoid division by zero
        df['Units_To_Trade'] = df.apply(
            lambda row: row['Difference'] / row['Current_Price'] if row['Current_Price'] > 0 else 0, 
            axis=1
        )
        
        # Action Label
        df['Action'] = df['Units_To_Trade'].apply(lambda x: 'BUY' if x > 0 else ('SELL' if x < 0 else 'HOLD'))
        
        return df

if __name__ == "__main__":
    # Test
    pm = PortfolioManager()
    data = {
        'Ticker': ['A', 'B'],
        'Quantity': [10, 20],
        'Target_Weight': [0.5, 0.5]
    }
    df = pd.DataFrame(data)
    prices = {'A': 100, 'B': 200}
    
    valued_df, total = pm.calculate_valuations(df, prices)
    print("Total:", total)
    print(valued_df)
    
    rebal_df = pm.calculate_rebalancing(valued_df, total, 1000)
    print(rebal_df[['Ticker', 'Action', 'Units_To_Trade']])
