import csv
import os
import glob
from convex import ConvexClient


folder_path = "../backend/data/modified/"


client = ConvexClient("http://127.0.0.1:3210")

csv_files = glob.glob(os.path.join(folder_path, "*.csv"))

print(csv_files, "\n")
print("\n", len(csv_files))