"""Export the labelling sample to Excel (existing labels are kept)."""
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

SRC = "data/processed/label_sample.csv"
OUT = "data/processed/label_sheet.xlsx"

df = pd.read_csv(SRC).fillna("")
df["description"] = df["description"].str.slice(0, 2500)
df[["job_id", "true_skills", "description"]].to_excel(OUT, index=False)

wb = load_workbook(OUT)
ws = wb.active
ws.column_dimensions["A"].width = 14
ws.column_dimensions["B"].width = 45
ws.column_dimensions["C"].width = 140
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="305496")
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    row[1].fill = PatternFill("solid", fgColor="FFF2CC")  # type your labels here
ws.freeze_panes = "A2"
wb.save(OUT)
print("Saved", OUT)
