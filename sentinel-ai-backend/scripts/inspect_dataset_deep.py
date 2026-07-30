"""Deep-dive inspection of the crime dataset."""
import pandas as pd

path = "dataset/coimbatore_crime_dataset.xlsx"
df = pd.read_excel(path, sheet_name="Sheet1")

print("ALL 70 AREAS:")
for i, area in enumerate(df["Area"].tolist(), 1):
    print(f"  {i:3d}. {area}")

print("\nRISK LEVEL BREAKDOWN:")
for level in ["Low", "Medium", "High"]:
    subset = df[df["Risk Level"] == level]
    print(f"\n  {level} ({len(subset)} areas):")
    print(f"    Crime Index range : {subset['Crime Index'].min()} - {subset['Crime Index'].max()}")
    print(f"    Theft range       : {subset['Theft'].min()} - {subset['Theft'].max()}")
    print(f"    Robbery range     : {subset['Robbery'].min()} - {subset['Robbery'].max()}")
    print(f"    Assault range     : {subset['Assault'].min()} - {subset['Assault'].max()}")
    print(f"    Harassment range  : {subset['Harassment'].min()} - {subset['Harassment'].max()}")
    print(f"    Vehicle Theft range: {subset['Vehicle Theft'].min()} - {subset['Vehicle Theft'].max()}")

print("\nCRIME TYPE TOTALS ACROSS ALL AREAS:")
crime_cols = ["Theft", "Robbery", "Assault", "Harassment", "Vehicle Theft"]
for col in crime_cols:
    print(f"  {col:20s}: total={df[col].sum()}  mean={df[col].mean():.1f}  max={df[col].max()}")

print("\nCRIME INDEX THRESHOLDS (inferred from Risk Level):")
print(f"  Low    Crime Index: {df[df['Risk Level']=='Low']['Crime Index'].min()} - {df[df['Risk Level']=='Low']['Crime Index'].max()}")
print(f"  Medium Crime Index: {df[df['Risk Level']=='Medium']['Crime Index'].min()} - {df[df['Risk Level']=='Medium']['Crime Index'].max()}")
print(f"  High   Crime Index: {df[df['Risk Level']=='High']['Crime Index'].min()} - {df[df['Risk Level']=='High']['Crime Index'].max()}")

print("\nTOP 10 HIGHEST CRIME INDEX AREAS:")
top10 = df.nlargest(10, "Crime Index")[["Area", "Crime Index", "Risk Level", "Theft", "Robbery", "Assault"]]
print(top10.to_string(index=False))

print("\nBOTTOM 10 LOWEST CRIME INDEX AREAS:")
bot10 = df.nsmallest(10, "Crime Index")[["Area", "Crime Index", "Risk Level", "Theft", "Robbery", "Assault"]]
print(bot10.to_string(index=False))
