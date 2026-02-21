# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import pandas as pd
# import re
# import time

# # === Config ===
# driver_path = "/Users/aaravgupta/Documents/chromedriver"
# MAX_SUBJECTS_PER_SESSION = 4  # Restart driver every 4 subjects

# def start_driver():
#     options = Options()
#     # options.add_argument("--headless")  # Uncomment for headless mode
#     service = Service(driver_path)
#     return webdriver.Chrome(service=service, options=options)

# base_url = "https://guide.wisc.edu/courses/"

# # === Get subject links (do this once, outside driver restarts) ===
# driver = start_driver()
# driver.get(base_url)
# try:
#     WebDriverWait(driver, 20).until(
#         EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#atozindex ul li a"))
#     )
# except:
#     print("❌ Failed to load the course list from base page.")
#     driver.quit()
#     exit()

# course_links = driver.find_elements(By.CSS_SELECTOR, "#atozindex ul li a")
# subject_urls = []
# subject_codes = []
# for link in course_links:
#     text = link.text
#     href = link.get_attribute("href")
#     if "(" in text and ")" in text:
#         subject_urls.append(href)
#         raw_code = text.split("(")[-1].split(")")[0].strip().lower().replace(" ", "_").replace("__", "_")
#         subject_codes.append(raw_code)
# driver.quit()  # Done with initial subject list

# # === Regex pattern to parse course info ===
# course_pattern = re.compile(
#     r'(?P<dept>(?:[A-Z0-9&\-/ ]+/)*[A-Z0-9&\-/ ]+)\s+(?P<number>\d{1,3})\s+\u2014\s+(?P<title>.+)'
# )

# courses = []

# # === Loop through subjects, restarting driver every 4 subjects ===
# driver = None
# for idx, (subject_url, subject_code) in enumerate(zip(subject_urls, subject_codes)):
#     if idx % MAX_SUBJECTS_PER_SESSION == 0:
#         if driver:
#             driver.quit()
#         driver = start_driver()
#     print(f"🔍 Visiting: {subject_url}")
#     try:
#         driver.get(subject_url)
#         WebDriverWait(driver, 10).until(
#             EC.presence_of_all_elements_located((By.CLASS_NAME, "courseblock"))
#         )
#     except Exception as e:
#         print(f"⚠️ Skipping {subject_url} — {e}")
#         continue

#     course_blocks = driver.find_elements(By.CLASS_NAME, "courseblock")
#     print(f"✅ Found {len(course_blocks)} course blocks for {subject_url}")

#     for block in course_blocks:
#         try:
#             # Initialize fields
#             level = "N/A"
#             breadth = "N/A"
#             gen_ed = "N/A"
#             last_taught = "N/A"
#             prereqs = "None"
#             description = "N/A"

#             title_el = block.find_element(By.CLASS_NAME, "courseblocktitle")
#             title_text = title_el.text.strip()
#             match = course_pattern.match(title_text)
#             if not match:
#                 continue

#             dept = match.group("dept").strip()
#             number = match.group("number").strip()
#             title = match.group("title").strip()
#             code_cleaned = dept.lower().replace(" ", "_").replace("&", "_").replace("/", "_").replace("-", "_").replace("__", "_")
#             course_code = f"{code_cleaned}_{number}"

#             credits_el = block.find_element(By.CLASS_NAME, "courseblockcredits")
#             credits = credits_el.text.strip().replace("credits", "").strip()

#             # Try to find and click "View details"
#             view_btns = block.find_elements(By.XPATH, ".//*[contains(text(), 'View details')]")
#             if view_btns:
#                 view_btn = view_btns[0]
#                 driver.execute_script("arguments[0].scrollIntoView(true);", view_btn)
#                 driver.execute_script("arguments[0].click();", view_btn)
#                 try:
#                     WebDriverWait(block, 3).until(
#                         EC.visibility_of_element_located((By.CLASS_NAME, "cb-extras"))
#                     )
#                     time.sleep(0.2)
#                 except Exception as e:
#                     print(f"⚠️ cb-extras not visible after clicking: {e}")
#             else:
#                 print("No 'View details' button found for this course block.")

#             # Description
#             try:
#                 desc_el = block.find_element(By.CLASS_NAME, "courseblockdesc")
#                 description = desc_el.text.strip()
#             except:
#                 pass

#             # Extra info
#             try:
#                 extras_div = block.find_element(By.CLASS_NAME, "cb-extras")
#                 rows = extras_div.find_elements(By.CSS_SELECTOR, "p.courseblockextra")
#                 for row in rows:
#                     labels = row.find_elements(By.CSS_SELECTOR, "span.cbextra-label")
#                     datas = row.find_elements(By.CSS_SELECTOR, "span.cbextra-data")
#                     for label, data in zip(labels, datas):
#                         label_text = label.text.strip().lower().rstrip(":")
#                         data_text = data.text.strip()
#                         if "requisite" in label_text:
#                             prereqs = data_text if data_text else "None"
#                         elif "designation" in label_text:
#                             for line in data_text.split("\n"):
#                                 if "level" in line.lower():
#                                     level = line.strip()
#                                 elif "breadth" in line.lower():
#                                     breadth = line.strip()
#                                 elif "gen ed" in line.lower():
#                                     gen_ed = line.strip()
#                         elif "last taught" in label_text:
#                             last_taught = data_text
#             except Exception as e:
#                 print(f"⚠️ Could not extract cb-extras: {e}")

#             courses.append({
#                 "Course ID": number,
#                 "University ID": "UW-Madison",
#                 "Title": title,
#                 "Course Code": course_code,
#                 "Credits": credits,
#                 "Level": level,
#                 "Breadth": breadth,
#                 "Gen Ed": gen_ed,
#                 "Last Taught": last_taught,
#                 "Prerequisites": prereqs,
#                 "Description": description
#             })

#         except Exception as e:
#             print(f"❌ Error parsing course: {e}")
#             continue

# if driver:
#     driver.quit()
# df = pd.DataFrame(courses)
# df.to_csv("uwmadison_courses.csv", index=False)
# print(f"✅ {len(df)} courses saved to uwmadison_courses.csv")
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import pandas as pd
import re, time

# ─────────────────── CONFIG ────────────────────
DRIVER_PATH = "/Users/aaravgupta/Documents/chromedriver"
BASE_URL    = "https://guide.wisc.edu/courses/"
MAX_SUBJECTS_PER_SESSION = 4               # recycle driver

def start_driver():
    opts = Options()
    # opts.add_argument("--headless")       # make visible while debugging
    return webdriver.Chrome(service=Service(DRIVER_PATH), options=opts)

# ────────────────── 1. SUBJECT LIST ──────────────────
drv = start_driver()
drv.get(BASE_URL)
WebDriverWait(drv, 20).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#atozindex ul li a"))
)

subject_urls, subject_codes = [], []
for a in drv.find_elements(By.CSS_SELECTOR, "#atozindex ul li a"):
    t = a.text
    if "(" in t and ")" in t:                    # legitimate subject line
        subject_urls.append(a.get_attribute("href"))
        subject_codes.append(
            re.sub(r"__+", "_", t.split("(")[-1].split(")")[0]
                                   .lower().replace(" ", "_"))
        )
drv.quit()

# ────────── 2. REGEX TO PARSE THE TITLE STRIP ──────────
title_rx = re.compile(
    r'(?P<dept>(?:[A-Z0-9&/\- ]+/)*[A-Z0-9&/\- ]+)\s+'
    r'(?P<number>\d{1,3}[A-Z]?)\s+\u2014\s+(?P<title>.+)'
)

courses, drv = [], None

# ────────────────── 3. SCRAPE PAGES ──────────────────
for i, (sub_url, _code) in enumerate(zip(subject_urls, subject_codes)):
    if i % MAX_SUBJECTS_PER_SESSION == 0:
        if drv:
            drv.quit()
        drv = start_driver()

    print(f"🔍  {sub_url}")
    drv.get(sub_url)
    WebDriverWait(drv, 15).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "courseblock"))
    )

    for blk in drv.find_elements(By.CLASS_NAME, "courseblock"):
        try:
            ttxt = blk.find_element(By.CLASS_NAME, "courseblocktitle").text.strip()
            m    = title_rx.match(ttxt)
            if not m:
                continue

            dept, num, title = m.group("dept").strip(), m.group("number"), m.group("title")
            course_id        = f"{dept} {num}"
            credits = blk.find_element(By.CLASS_NAME, "courseblockcredits").text \
                         .replace("credits", "").strip()

            # ── CLICK “View details” so cb-extras loads ──
            view_btns = blk.find_elements(By.XPATH, ".//*[contains(text(),'View details')]")
            if view_btns:
                drv.execute_script("arguments[0].scrollIntoView(true);", view_btns[0])
                drv.execute_script("arguments[0].click();", view_btns[0])
                # wait for cb-extras to appear
                WebDriverWait(blk, 3).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "cb-extras"))
                )
                time.sleep(0.2)   # small JS settle

            # description
            try:
                description = blk.find_element(By.CLASS_NAME, "courseblockdesc").text.strip()
            except:
                description = "N/A"

            # default extras
            level = breadth = gen_ed = last_taught = "N/A"
            repeatable = "N/A"
            prereqs = "None"

            try:
                extras_div = blk.find_element(By.CLASS_NAME, "cb-extras")
                for row in extras_div.find_elements(By.CSS_SELECTOR, "p.courseblockextra"):
                    lab = row.find_element(By.CSS_SELECTOR, "span.cbextra-label").text.lower()
                    dat = row.find_element(By.CSS_SELECTOR, "span.cbextra-data").text.strip()

                    if "requisite" in lab:
                        prereqs = dat if dat else "None"
                    elif "designation" in lab:
                        for ln in dat.split("\n"):
                            l = ln.lower()
                            if "level"   in l: level   = ln.strip()
                            if "breadth" in l: breadth = ln.strip()
                            if "gen ed"  in l: gen_ed  = ln.strip()
                    elif "last taught" in lab:
                        last_taught = dat
                    elif "repeatable for credit" in lab:
                        repeatable = dat or "Yes"
            except:
                pass        # some courses truly lack extras

            # sanitised code (for filenames etc.)
            code_san = re.sub(r"__+", "_", dept.lower().replace(" ", "_").replace("&","_")
                                                    .replace("/","_").replace("-","_"))
            course_code = f"{code_san}_{num}"

            courses.append({
                "Course ID":               course_id,
                "University":              "UW-Madison",
                "Title":                   title,
                "Credits":                 credits,
                "Level":                   level,
                "Repeatable for Credit":   repeatable,
                "Breadth":                 breadth,
                "Gen Ed":                  gen_ed,
                "Last Taught":             last_taught,
                "Prereqs":                 prereqs,
                "Description":             description
            })

        except StaleElementReferenceException:
            continue

# ────────────────── 4. SAVE CSV ──────────────────
if drv:
    drv.quit()

df = pd.DataFrame(courses)
df.to_csv("uwmadison_courses.csv", index=False)
print(f"✅  {len(df)} rows written to uwmadison_courses.csv")