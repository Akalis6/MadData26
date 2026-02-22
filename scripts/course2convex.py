import csv
import os
import glob
from convex import ConvexClient
import pandas as pd
import json


folder_path = "../backend/data/modified/"

client = ConvexClient("http://127.0.0.1:3210")
tasks = client.query("tasks:getUniversity")
uni_id = str(tasks[0]['_id'])

csv_files = glob.glob(os.path.join(folder_path, "*.csv"))



majors = []

for filepath in csv_files:
    #df = pd.read_csv(filepath)
    major_name = filepath.split("\\")[-1].split("_B")[0]
    majors.append({
        "majorName": major_name,
        "degreeType": "BS",
        "University": uni_id
    })
    majors.append({
        "majorName": major_name,
        "degreeType": "BA",
        "University": uni_id
    })

#print(csv_files, "\n")
output_file = "majors_list.json"

with open(output_file, "w") as f:
    json.dump(majors, f, indent=4)
