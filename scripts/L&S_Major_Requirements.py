import csv
import os                     
import re
import time
from typing import List, Set, Tuple, Union

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
SCHOOL_URLS = [
    "https://guide.wisc.edu/undergraduate/letters-science/#degreesmajorscertificatestext",
]
MAX_PROGRAMS_PER_SCHOOL = None  # None → scrape all

FILTER_KEYWORDS: List[str] = ["credit", "course", "from", "complete", ":"]
COURSE_ID_REGEX = re.compile(r"\b(?:\w*\d+\w*|[A-Z]{4,})\b")
DATA_ROOT = "Requirement_Data"          # NEW: root output directory

# --------------------------------------------------
# Selenium setup
# --------------------------------------------------
options = Options()
# options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

# --------------------------------------------------
# Globals (unchanged)
# --------------------------------------------------
seen_programs: Set[str] = set()
output_rows: List[List[Union[int, str]]] = []
global_group_id: int = 1

# --------------------------------------------------
# Helper utilities (unchanged)
# --------------------------------------------------
def flush_group(courses: List[str], major: str) -> None:
    global global_group_id
    cleaned = [c for c in courses if not any(k in c.lower() for k in FILTER_KEYWORDS)]
    if not cleaned:
        return
    for course in cleaned:
        output_rows.append([global_group_id, major, course])
    global_group_id += 1


def row_to_course(row) -> Tuple[str, bool]:
    links = row.find_elements(By.TAG_NAME, "a")
    credit_cells = row.find_elements(By.CSS_SELECTOR, "td.hourscol")
    credit_text = " ".join(c.text.strip() for c in credit_cells).strip()
    has_credit = bool(credit_text)
    text = " & ".join(l.text.strip() for l in links if l.text.strip()) or row.text.strip()
    if not text or any(k in text.lower() for k in FILTER_KEYWORDS):
        return "", has_credit
    if not COURSE_ID_REGEX.search(text):
        return "", has_credit
    return text, has_credit


def extract_courses_from_table(table, major: str, inside_category: bool) -> None:
    global global_group_id
    rows = table.find_elements(By.CSS_SELECTOR, "tr")
    if not rows:
        return

    def _is_sep(tr):
        cls = tr.get_attribute("class")
        return "areaheader" in cls or "areasubheader" in cls

    # 1️⃣ header / sub-header tables
    if any(_is_sep(r) for r in rows):
        bucket: List[str] = []
        for r in rows:
            if _is_sep(r):
                flush_group(bucket, major); bucket = []; continue
            txt, _ = row_to_course(r)
            if txt:
                bucket.append(txt)
        flush_group(bucket, major)
        return

    # 2️⃣ table inside accordion category
    if inside_category:
        bucket: List[str] = []
        for r in rows:
            txt, _ = row_to_course(r)
            if txt:
                bucket.append(txt)
            else:
                flush_group(bucket, major); bucket = []
        flush_group(bucket, major)
        return

    # 3️⃣ flat table (no wrapper)
    bundle: List[str] = []
    for r in rows:
        txt, credit = row_to_course(r)
        if not txt:
            flush_group(bundle, major); bundle = []; continue
        if credit:
            flush_group(bundle, major); bundle = []
            output_rows.append([global_group_id, major, txt]); global_group_id += 1
        else:
            bundle.append(txt)
    flush_group(bundle, major)


def xpath_literal(s: str) -> str:
    return f"'{s}'" if "'" not in s else "concat('" + "', \"'\", '".join(s.split("'")) + "')"

# --------------------------------------------------
# Scrape loop
# --------------------------------------------------
for school_url in SCHOOL_URLS:
    # NEW: make a directory for this school
    school_slug = re.search(r"/undergraduate/([^/]+)/", school_url).group(1)
    school_dir  = os.path.join(DATA_ROOT, school_slug.replace("-", "_"))
    os.makedirs(school_dir, exist_ok=True)

    driver.get(school_url); time.sleep(2)
    links = driver.find_elements(By.CSS_SELECTOR, "div.visual-sitemap.list ul li a")
    program_links = [(a.text.strip(), a.get_attribute("href")) for a in links if a.get_attribute("href")]

    for title, href in program_links[:MAX_PROGRAMS_PER_SCHOOL]:
        if "certificate" in title.lower():
            continue

        clean = re.sub(r"\s*\(.*?\)\s*$", "", title, flags=re.I).strip()
        base  = re.sub(r",?\s+(BBA|BA|BS|BLS|BFA|AMEP|BM|BSE)$", "", clean, flags=re.I).strip()
        key   = base.lower()
        if key in seen_programs:
            continue
        seen_programs.add(key)

        print(f"\n🔍 Processing: {title}")
        driver.get(href)

        try:
            wait.until(EC.element_to_be_clickable((By.ID, "requirementstexttab"))).click()
            wait.until(EC.presence_of_element_located((By.ID, "requirementstextcontainer")))
        except Exception as e:
            print("⚠️  Cannot open requirements tab:", e); continue

        container = driver.find_element(By.ID, "requirementstextcontainer")

        # --- original xp_list block (unchanged) ---------------------------
        base_lit   = xpath_literal(key)
        prefix     = key.split(":")[0].strip()
        prefix_lit = xpath_literal(prefix)

        xp_list = [
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'requirements for the major')]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'amep program requirements')]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'requirements for the')]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'summary of requirements')]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'major requirements')]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'required courses')]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'bba')]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'curriculum')]",
            f"//h2[translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz') = {base_lit}]",
            f"//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {base_lit})]",
            f"//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {base_lit}) and contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'requirements')]",
            f"//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {prefix_lit})]",
            "//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'amep program requirements')]",
            f"//h2[translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz') = {base_lit}]",
            f"//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {base_lit})]",
            f"//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {base_lit}) and contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'requirements')]",
            f"//h2[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), {prefix_lit})]",
        ]
        # ------------------------------------------------------------------

        header = None
        for xp in xp_list:
            try:
                header = container.find_element(By.XPATH, xp); break
            except Exception:
                continue
        if not header:
            print("⚠️  Requirements header not found; skipped."); continue

        # ---- collect rows for THIS major --------------------------------
        start_idx  = len(output_rows)      # remember where this major starts
        for sib in header.find_elements(By.XPATH, "following-sibling::*"):
            if sib.tag_name == "h2": break
            cls = sib.get_attribute("class")
            if "toggle-group" in cls:
                for wrap in sib.find_elements(By.CSS_SELECTOR,"div.toggle-wrap"):
                    try:
                        hdr = wrap.find_element(By.CSS_SELECTOR,"h3.toggle, h4.toggle")
                        driver.execute_script("arguments[0].scrollIntoView(true);", hdr)
                        hdr.click()
                        wait.until(lambda d: "expanded" in hdr.get_attribute("class"))
                        for tbl in wrap.find_elements(By.CSS_SELECTOR,"div.toggle-content table.sc_courselist"):
                            extract_courses_from_table(tbl, title, True)
                    except Exception as err:
                        print("⚠️  Toggle error:", err)
            elif "sc_courselist" in cls:
                extract_courses_from_table(sib, title, False)

        # ---- write per-major CSV ----------------------------------------
        major_rows = output_rows[start_idx:]
        if major_rows:
            fname = re.sub(r"[^\w\- ]", "", title).replace(" ", "_") + ".csv"
            path  = os.path.join(school_dir, fname)
            with open(path, "w", newline="") as fp:
                csv.writer(fp).writerows([["Group ID", "Major", "Course"], *major_rows])
            print(f"   ✔️  {len(major_rows)} rows → {path}")
        else:
            print("   ⚠️  No course rows found")

driver.quit()
print("\n✅ Finished – all majors saved individually.")