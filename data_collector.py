import FinanceDataReader as fdr
import pandas as pd

class DataCollector:
    def __init__(self):
        pass

    def get_current_price(self, ticker):
        """
        Fetches the latest price for a single ticker.
        Tries to determine if it's a KRX stock or a US stock/ETF.
        """
        try:
            # Remove any whitespace
            ticker = str(ticker).strip()
            
            # Simple heuristic: If it's all digits, it's likely KRX (e.g., '005930')
            # If it has letters, it's likely US (e.g., 'AAPL', 'SPY') or requires exchange prefix
            
            # fdr.DataReader handles '005930' as KRX automatically.
            # For US stocks, just passing 'AAPL' works.
            
            df = fdr.DataReader(ticker)
            if df.empty:
                print(f"Warning: No data found for {ticker}")
                return None
            
            # Return the latest 'Close' price
            return df['Close'].iloc[-1]
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None

    def fetch_prices_for_portfolio(self, portfolio_df):
        """
        Fetches prices for all tickers in the portfolio DataFrame.
        Returns a dictionary {ticker: price}.
        """
        prices = {}
        tickers = portfolio_df['Ticker'].unique()
        
        print(f"Fetching prices for {len(tickers)} assets...")
        
        for ticker in tickers:
            price = self.get_current_price(ticker)
            if price is not None:
                prices[ticker] = price
            else:
                # Fallback or error handling
                prices[ticker] = 0.0 # Or use previous close if available in DB
        
        return prices

# Simple test
if __name__ == "__main__":
    dc = DataCollector()
    # Test with the dummy data tickers
    test_tickers = ['005930', 'SPY', '360750'] 
    for t in test_tickers:
        print(f"{t}: {dc.get_current_price(t)}")
