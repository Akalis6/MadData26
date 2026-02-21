from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

# Setup
driver_path = "/Users/aaravgupta/Documents/chromedriver"  # ✅ Update this if needed
options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # Optional: run in background
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=options)

# Go to the majors page
url = "https://www.wisc.edu/academics/majors/"
driver.get(url)

# Wait for the table to load
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.ID, "programs-results-table"))
)

# Scrape rows
rows = driver.find_elements(By.CSS_SELECTOR, "tr.uw-program")
results = []
university_id = "UW-Madison"
id_counter = 1

for row in rows:
    cells = row.find_elements(By.TAG_NAME, "td")
    if len(cells) < 2:
        continue

    major = cells[0].text.strip()
    degree_types = [a.text.strip() for a in cells[1].find_elements(By.TAG_NAME, "a")]

    for degree in degree_types:
        if "certificate" not in degree.lower():
            results.append({
                "id": id_counter,
                "university_id": university_id,
                "major_name": major,
                "degree_type": degree
            })
            id_counter += 1

driver.quit()

# Save to CSV
df = pd.DataFrame(results)
print(df.head())
df.to_csv("uwmadison_majors.csv", index=False)
print("✅ Saved as uwmadison_majors.csv")