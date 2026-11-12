import pandas as pd

df = pd.read_json("data/records.json")

print("Total records:", len(df))

top = df["channel"].value_counts()
print(f"Fact 1: the most common channel is '{top.index[0]}' with {top.iloc[0]} records")

text = df["how_it_works"] + " " + df["precautions"]
otp = text.str.contains("OTP", case=False).sum()
print(f"Fact 2: {otp} of {len(df)} records mention OTP")

lengths = df["precautions"].str.len()
longest = df.loc[lengths.idxmax()]
print(f"Fact 3: '{longest['fraud_name']}' has the longest precautions "
      f"({lengths.max()} characters, average {lengths.mean():.0f})")