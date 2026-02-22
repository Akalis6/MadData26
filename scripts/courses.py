
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
                            if "ethnic st" in l:ethnic = ln.strip()
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
                "Ethnic Studies":          ethnic,
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