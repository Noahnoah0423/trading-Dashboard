import yfinance as yf

print("Testing yfinance capabilities:")

ticker = yf.Ticker("AAPL")

print("\n--- Insider Transactions ---")
try:
    insider = ticker.insider_transactions
    if insider is not None and not insider.empty:
        print(insider.head())
    else:
        print("No insider data")
except Exception as e:
    print("Error:", e)

print("\n--- Institutional Holders ---")
try:
    inst = ticker.institutional_holders
    if inst is not None and not inst.empty:
        print(inst.head())
    else:
        print("No institutional data")
except Exception as e:
    print("Error:", e)

print("\n--- Major Holders ---")
try:
    major = ticker.major_holders
    if major is not None and not major.empty:
        print(major.head())
    else:
        print("No major holders data")
except Exception as e:
    print("Error:", e)
