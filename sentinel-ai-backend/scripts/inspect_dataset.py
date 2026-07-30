"""Dataset inspection - run once to understand structure before writing CrimeService."""
import sys
import pandas as pd

path = "dataset/coimbatore_crime_dataset.xlsx"
xl = pd.ExcelFile(path)

SEP = "=" * 70
SUB = "-" * 70

print(SEP)
print("FILE : " + path)
print("SHEETS (" + str(len(xl.sheet_names)) + "): " + str(xl.sheet_names))
print(SEP)

for sheet in xl.sheet_names:
    df = pd.read_excel(path, sheet_name=sheet)
    print("\n" + SUB)
    print("SHEET : " + sheet)
    print("SHAPE : " + str(df.shape[0]) + " rows x " + str(df.shape[1]) + " columns")

    print("\nCOLUMNS & DTYPES:")
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        print("  " + repr(col) + "  dtype=" + str(df[col].dtype) + "  nulls=" + str(null_count))

    print("\nFIRST 3 ROWS (transposed for readability):")
    for i, row in df.head(3).iterrows():
        print("  Row " + str(i) + ":")
        for col in df.columns:
            print("    " + str(col) + " = " + repr(row[col]))

    print("\nNUMERIC COLUMNS - basic stats:")
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        print(df[num_cols].describe().to_string())
    else:
        print("  (none)")

    print("\nOBJECT/CATEGORY COLUMNS - unique value counts (top 15 each):")
    for col in df.select_dtypes(include=["object", "category"]).columns:
        unique_count = df[col].nunique(dropna=True)
        print("\n  [" + str(col) + "]  (" + str(unique_count) + " unique values)")
        vc = df[col].value_counts(dropna=False).head(15)
        for val, cnt in vc.items():
            print("    " + repr(str(val)) + "  ->  " + str(cnt))

    print("\nDATE/DATETIME COLUMNS:")
    date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    if date_cols:
        for col in date_cols:
            print("  " + col + "  min=" + str(df[col].min()) + "  max=" + str(df[col].max()))
    else:
        print("  (none detected - check object columns manually)")

print("\n" + SEP)
print("INSPECTION COMPLETE")
print(SEP)
