from convex import ConvexClient
import pandas as pd

client = ConvexClient("http://127.0.0.1:3210")
tasks = client.query("tasks:getUniversity")
uni_id = str(tasks[0]['_id'])

filepath = "../backend/data/uwmadison_courses2.csv"


df = pd.read_csv(filepath)

#rename existing columns that should be formatted correctly
df = df.rename(columns={
    'Course ID': 'courseID',
    'Title': 'name',
})

#make new columns
df['level'] = df['Level'].apply( lambda x: str(x) if pd.notnull(x) else "")
df['generalEd'] = df['Gen Ed'].apply( lambda x: str(x) if pd.notnull(x) else "")
df['description'] = df['Description'].apply( lambda x: str(x) if pd.notnull(x) else "")

df['repeatable'] = df['Repeatable for Credit'].apply( lambda x: "yes" in str(x).lower() )

df['credits'] = df["Credits"].apply(lambda x: int(str(x)[0]) if pd.notnull(x) else 0)

df['prerequirements'] = None

df['university'] = uni_id


def parse_breadth(val):
    breadth_str = str(val).lower()
    categories = []
    if "humanities" in breadth_str: categories.append("humanities")
    if "social science" in breadth_str: categories.append("social science")
    if "literature" in breadth_str: categories.append("literature")
    if "physical sci" in breadth_str: categories.append("physical science")
    if "biological sci" in breadth_str: categories.append("biological science")
    return categories

df['breadth'] = df['Breadth'].apply(parse_breadth)
df['ethnicstudies'] = df["Ethnic Studies"].apply(lambda x: True if pd.notnull(x) else False)

#remove old columns
df = df.drop(columns=['University', 'Credits', 'Repeatable for Credit', 'Breadth', 'Last Taught', 'Prereqs', 'Ethnic Studies', "Level", "Gen Ed", "Description"])
df.to_json('uwmadison_courses.json', orient='records', indent=4)

