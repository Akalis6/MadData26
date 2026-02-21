import React, { useMemo, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker?url";

GlobalWorkerOptions.workerSrc = pdfWorker;

type TermStatus = "completed" | "in_progress" | "cart";
type CourseFlag = "in_progress" | "waitlisted" | "not_offered" | "no_longer_offered";

type Course = {
  id: string; // "COMP SCI 564"
  title: string;
  credits: number;
  grade?: string; // "A", "BC", "INP", etc
  status: TermStatus;
  flag?: CourseFlag;
};

type Term = {
  name: string; // "Fall 2024"
  totalCredits: number;
  completedCount: number;
  inProgressCount: number;
  cartCount: number;
  courses: Course[];
};

type PlannerYear = {
  academicYearLabel: string; // "2024-2025"
  classYearLabel: string; // "Freshman", ...
  terms: Term[]; // [Fall, Spring, Summer]
};

type ParsedCourse = {
  termCode: "FA" | "SP" | "SU";
  year: number; // 2022 etc
  subject: string; // "COMP SCI"
  number: string; // "564"
  credits: number;
  grade: string; // "A", "BC", "INP", "T", etc
  title: string;
};

function classNames(...xs: Array<string | false | undefined | null>) {
  return xs.filter(Boolean).join(" ");
}

function Icon({
  name,
}: {
  name: "pdf" | "plus" | "calendar" | "info" | "gear" | "chev" | "check" | "warn" | "ban" | "slash";
}) {
  const common = "inline-block align-middle";
  switch (name) {
    case "pdf":
      return (
        <span className={classNames(common, "text-[12px] font-bold px-2 py-1 rounded bg-gray-100 border")}>PDF</span>
      );
    case "plus":
      return <span className={classNames(common, "text-lg font-bold")}>＋</span>;
    case "calendar":
      return <span className={common}>📅</span>;
    case "info":
      return <span className={common}>❔</span>;
    case "gear":
      return <span className={common}>⚙️</span>;
    case "chev":
      return <span className={common}>▾</span>;
    case "check":
      return <span className={common}>✅</span>;
    case "warn":
      return <span className={common}>⚠️</span>;
    case "ban":
      return <span className={common}>⛔</span>;
    case "slash":
      return <span className={common}>🚫</span>;
    default:
      return null;
  }
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border bg-white px-2 py-0.5 text-xs font-medium text-gray-700">
      {children}
    </span>
  );
}

function CourseFlagIcon({ flag }: { flag?: CourseFlag }) {
  if (!flag) return null;
  const map: Record<CourseFlag, { icon: React.ReactNode; label: string }> = {
    in_progress: { icon: <Icon name="check" />, label: "Course is in progress" },
    waitlisted: { icon: <Icon name="warn" />, label: "Course is waitlisted" },
    not_offered: { icon: <Icon name="ban" />, label: "Course is not offered in term" },
    no_longer_offered: { icon: <Icon name="slash" />, label: "Course is no longer offered" },
  };

  return (
    <span className="ml-2" title={map[flag].label}>
      {map[flag].icon}
    </span>
  );
}

function Divider() {
  return <div className="h-px w-full bg-gray-200" />;
}

function AccordionRow({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border bg-white">
      <button className="flex w-full items-center justify-between px-4 py-3 text-left" onClick={onToggle} type="button">
        <span className="text-sm font-medium text-gray-900">{title}</span>
        <span className={classNames("transition-transform", open && "rotate-180")}>
          <Icon name="chev" />
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4">
          <Divider />
          <div className="pt-3">{children}</div>
        </div>
      )}
    </div>
  );
}

function TermCard({ term, showGrades }: { term: Term; showGrades: boolean }) {
  const tabs = useMemo(
    () => [
      { key: "completed" as const, label: `Completed (${term.completedCount})` },
      { key: "in_progress" as const, label: `In Progress (${term.inProgressCount})` },
      { key: "cart" as const, label: `Cart (${term.cartCount})` },
    ],
    [term.completedCount, term.inProgressCount, term.cartCount]
  );

  const [activeTab, setActiveTab] = useState<TermStatus>("completed");
  const courses = term.courses.filter((c) => c.status === activeTab);

  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="text-sm font-semibold text-gray-900">{term.name}</div>

        <div className="text-sm text-gray-700">
          <span className="font-medium">{term.totalCredits.toFixed(2)}</span> credits{" "}
          <button className="ml-2 inline-flex h-7 w-7 items-center justify-center rounded border bg-white hover:bg-gray-50" type="button">
            <Icon name="plus" />
          </button>
        </div>
      </div>

      <div className="px-4">
        <div className="flex gap-4 border-b">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setActiveTab(t.key)}
              className={classNames(
                "py-2 text-xs font-medium",
                activeTab === t.key ? "text-blue-700 border-b-2 border-blue-700" : "text-gray-600"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4">
        {courses.length === 0 ? (
          <div className="rounded-lg border border-dashed p-4 text-center text-sm text-gray-600">
            No courses in {activeTab.replace("_", " ")}.
            <div className="mt-3">
              <button className="rounded border bg-white px-3 py-1.5 text-sm hover:bg-gray-50" type="button">
                + Add Course
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {courses.map((c) => (
              <div key={`${term.name}-${c.id}-${c.title}-${c.grade}`} className="rounded-lg border bg-gray-50 px-3 py-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center">
                      <div className="truncate text-sm font-semibold text-gray-900">{c.id}</div>
                      <CourseFlagIcon flag={c.flag} />
                    </div>
                    <div className="truncate text-xs text-gray-700">{c.title}</div>
                  </div>

                  <div className="flex shrink-0 items-center gap-3 text-xs text-gray-700">
                    <div className="text-right">
                      <div className="font-medium">{c.credits.toFixed(2)} Cr</div>
                      {showGrades && c.grade && <div className="text-gray-600">{c.grade}</div>}
                    </div>
                    <button className="rounded border bg-white px-2 py-1 hover:bg-gray-50" type="button">
                      •••
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** ---------- PDF parsing helpers ---------- */

async function extractTextFromPdf(file: File): Promise<string> {
  const data = await file.arrayBuffer();
  const pdf = await getDocument({ data }).promise;

  let full = "";

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const content = await page.getTextContent();

    // Group text items into lines by Y coordinate (much more reliable than hasEOL)
    const items = (content.items as any[])
      .map((it) => ({
        str: (it.str ?? "").trim(),
        y: it.transform?.[5] ?? 0,
        x: it.transform?.[4] ?? 0,
      }))
      .filter((it) => it.str.length > 0);

    // Sort top-to-bottom then left-to-right
    items.sort((a, b) => (b.y - a.y) || (a.x - b.x));

    const lines: string[] = [];
    let currentY: number | null = null;
    let currentLine: string[] = [];

    const flush = () => {
      if (currentLine.length) lines.push(currentLine.join(" ").replace(/\s+/g, " ").trim());
      currentLine = [];
    };

    for (const it of items) {
      if (currentY === null) {
        currentY = it.y;
        currentLine.push(it.str);
        continue;
      }

      // If Y changes enough, start new line
      if (Math.abs(it.y - currentY) > 2.5) {
        flush();
        currentY = it.y;
        currentLine.push(it.str);
      } else {
        currentLine.push(it.str);
      }
    }

    flush();
    full += lines.join("\n") + "\n";
  }

  return full;
}

function parseCourseLine(line: string): ParsedCourse | null {
  const trimmed = line.trim().replace(/\s+/g, " ");

  // Match FA23 / FA 23 / etc
  const m = trimmed.match(/^(FA|SP|SU)\s*(\d{2})\s+(.+)$/i);
  if (!m) return null;

  const termCode = m[1].toUpperCase() as "FA" | "SP" | "SU";
  const year = 2000 + Number(m[2]);
  let rest = m[3].trim();

  // 🔧 KEY FIX:
  // Insert a space between letters and a 3-4 digit course number when they get stuck together:
  // "SCI252" -> "SCI 252", "PSYCH120" -> "PSYCH 120", "ECON3090" -> "ECON 3090"
  // Also handles things like "3090A" if it ever appears.
  rest = rest.replace(/([A-Z]{2,})(\d{3,4}[A-Z]?)/g, "$1 $2");

  // Now parse the normalized line by tokens
  const tokens = rest.split(" ").filter(Boolean);

  // Find first course number token (252, 3090, 120, 160, 564, etc)
  const idxNum = tokens.findIndex((t) => /^\d{3,4}[A-Z]?$/.test(t));
  if (idxNum <= 0) return null;

  const subject = tokens.slice(0, idxNum).join(" ");
  const number = tokens[idxNum];

  const creditsToken = tokens[idxNum + 1];
  const gradeToken = tokens[idxNum + 2];

  if (!creditsToken || !/^\d+(\.\d+)?$/.test(creditsToken)) return null;
  if (!gradeToken) return null;

  const title = tokens.slice(idxNum + 3).join(" ").trim();

  return {
    termCode,
    year,
    subject,
    number,
    credits: Number(creditsToken),
    grade: gradeToken,
    title,
  };
}

function extractCoursesFromDarsText(text: string): ParsedCourse[] {
  // Normalize weird spacing
  const normalized = text.replace(/\u00A0/g, " "); // non-breaking spaces
  const anchorRe = /total\s+credits\s+for\s+the\s+degree/i;

  // Try to find the anchor; if not found, fallback to whole document
  const m = normalized.match(anchorRe);
  const tail = m ? normalized.slice(m.index ?? 0) : normalized;

  const lines = tail
    .split(/\r?\n/)
    .map((l) => l.replace(/\s+/g, " ").trim())
    .filter(Boolean);

  // Match FA23 / FA 23 / SP24 / etc
  const courseLineRe = /^(FA|SP|SU)\s*\d{2}\b/i;

  const candidates = lines.filter((l) => courseLineRe.test(l));

  const parsed = candidates
    .map(parseCourseLine)
    .filter((x): x is ParsedCourse => Boolean(x));

  // If still nothing, fallback: scan entire doc for term-coded lines (sometimes the anchor is missing)
  if (parsed.length === 0) {
    const allCandidates = normalized
      .split(/\r?\n/)
      .map((l) => l.replace(/\s+/g, " ").trim())
      .filter((l) => courseLineRe.test(l));

    const parsedAll = allCandidates
      .map(parseCourseLine)
      .filter((x): x is ParsedCourse => Boolean(x));

    return dedupeParsed(parsedAll);
  }

  return dedupeParsed(parsed);
}

function dedupeParsed(arr: ParsedCourse[]): ParsedCourse[] {
  const seen = new Set<string>();
  const out: ParsedCourse[] = [];
  for (const c of arr) {
    const key = `${c.termCode}${c.year}|${c.subject}|${c.number}|${c.credits}|${c.grade}|${c.title}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push(c);
    }
  }
  return out;
}

function academicYearStart(termCode: "FA" | "SP" | "SU", year: number) {
  // Fall YEAR belongs to YEAR-YEAR+1
  // Spring/Summer YEAR belongs to (YEAR-1)-YEAR
  return termCode === "FA" ? year : year - 1;
}

function academicYearLabel(startYear: number) {
  return `${startYear}-${startYear + 1}`;
}

function termName(termCode: "FA" | "SP" | "SU", year: number) {
  if (termCode === "FA") return `Fall ${year}`;
  if (termCode === "SP") return `Spring ${year}`;
  return `Summer ${year}`;
}

function courseStatusFromGrade(grade: string): TermStatus {
  return grade.toUpperCase() === "INP" ? "in_progress" : "completed";
}

function classYearLabelByIndex(idx: number): string {
  const labels = ["Freshman", "Sophomore", "Junior", "Senior"];
  return labels[idx] ?? `Year ${idx + 1}`;
}

/** Build a Term object from parsed courses belonging to that term */
function buildTerm(name: string, pcs: ParsedCourse[], showGradesDefault: boolean): Term {
  const courses: Course[] = pcs.map((pc) => {
    const id = `${pc.subject} ${pc.number}`;
    const status = courseStatusFromGrade(pc.grade);

    return {
      id,
      title: pc.title,
      credits: pc.credits,
      grade: showGradesDefault ? pc.grade : pc.grade, // kept either way; UI toggle hides it
      status,
      flag: pc.grade.toUpperCase() === "INP" ? "in_progress" : undefined,
    };
  });

  const completedCount = courses.filter((c) => c.status === "completed").length;
  const inProgressCount = courses.filter((c) => c.status === "in_progress").length;
  const totalCredits = courses.reduce((sum, c) => sum + c.credits, 0);

  return {
    name,
    totalCredits,
    completedCount,
    inProgressCount,
    cartCount: 0,
    courses,
  };
}

export default function DegreePlannerFrontend() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [showGrades, setShowGrades] = useState(true);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isParsed, setIsParsed] = useState(false);

  const [plannerYears, setPlannerYears] = useState<PlannerYear[]>([]);
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({}); // key = classYearLabel

  function triggerUpload() {
    fileInputRef.current?.click();
  }

  async function onFileSelected(file: File | null) {
    setUploadedFile(file);
    setIsParsed(false);

    if (!file) return;

    const text = await extractTextFromPdf(file);
    const parsedCourses = extractCoursesFromDarsText(text);

    // Group by academic year start, then by term name
    const yearMap = new Map<number, Map<string, ParsedCourse[]>>();

    for (const c of parsedCourses) {
      const start = academicYearStart(c.termCode, c.year);
      if (!yearMap.has(start)) yearMap.set(start, new Map());

      const tName = termName(c.termCode, c.year);
      const termMap = yearMap.get(start)!;
      if (!termMap.has(tName)) termMap.set(tName, []);
      termMap.get(tName)!.push(c);
    }

    const starts = Array.from(yearMap.keys()).sort((a, b) => a - b);

    const years: PlannerYear[] = starts.map((startYear, idx) => {
      const termMap = yearMap.get(startYear)!;

      const fall = `Fall ${startYear}`;
      const spring = `Spring ${startYear + 1}`;
      const summer = `Summer ${startYear + 1}`;

      const fallCourses = termMap.get(fall) ?? [];
      const springCourses = termMap.get(spring) ?? [];
      const summerCourses = termMap.get(summer) ?? [];

      return {
        academicYearLabel: academicYearLabel(startYear),
        classYearLabel: classYearLabelByIndex(idx),
        terms: [
          buildTerm(fall, fallCourses, showGrades),
          buildTerm(spring, springCourses, showGrades),
          buildTerm(summer, summerCourses, showGrades),
        ],
      };
    });

    setPlannerYears(years);

    // Default: open all years once parsed (matches UW feel)
    const nextOpen: Record<string, boolean> = {};
    for (const y of years) nextOpen[y.classYearLabel] = true;
    setOpenMap(nextOpen);

    setIsParsed(true);
  }

  function expandAll() {
    const next: Record<string, boolean> = {};
    for (const y of plannerYears) next[y.classYearLabel] = true;
    setOpenMap(next);
  }

  function collapseAll() {
    const next: Record<string, boolean> = {};
    for (const y of plannerYears) next[y.classYearLabel] = false;
    setOpenMap(next);
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Top Nav */}
      <header className="bg-red-700 text-white">
        <div className="mx-auto flex h-14 w-full items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded bg-white/15 flex items-center justify-center font-bold">W</div>
              <span className="text-sm font-semibold">enroll.wisc.edu</span>
            </div>

            <nav className="hidden md:flex items-center gap-4 text-sm">
              <a className="opacity-90 hover:opacity-100" href="#">Course Search</a>
              <a className="opacity-90 hover:opacity-100" href="#">My Courses</a>
              <a className="opacity-90 hover:opacity-100" href="#">Scheduler</a>
              <a className="font-semibold underline underline-offset-8" href="#">Degree Planner</a>
              <a className="opacity-90 hover:opacity-100" href="#">Degree Audit (DARS)</a>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <button className="rounded-full bg-white/10 px-2 py-1 hover:bg-white/15" type="button" title="Help">
              <Icon name="info" />
            </button>
            <button className="rounded-full bg-white/10 px-2 py-1 hover:bg-white/15" type="button" title="Settings">
              <Icon name="gear" />
            </button>
            <div className="h-9 w-9 rounded-full bg-white/15 flex items-center justify-center font-semibold">A</div>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full grid-cols-1 gap-4 px-6 py-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        {/* Left */}
        <aside className="rounded-lg border bg-white p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs text-gray-500">DARS Upload</div>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">{uploadedFile ? "DARS Report" : "No file uploaded"}</span>
                {uploadedFile && <Badge>PDF</Badge>}
              </div>
            </div>

            <button type="button" className="rounded border bg-white px-2 py-1 text-sm hover:bg-gray-50" onClick={triggerUpload}>
              {uploadedFile ? "Replace" : "Upload"}
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => onFileSelected(e.target.files?.[0] ?? null)}
            />
          </div>

          <div className="mt-4 space-y-2">
            <div className="rounded-lg border bg-gray-50 p-3 text-sm text-gray-700">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <Badge>{uploadedFile ? (isParsed ? "Loaded" : "Selected") : "Waiting"}</Badge>
              </div>
              <div className="mt-2 text-xs text-gray-600">
                {uploadedFile ? (
                  <>
                    <div className="truncate"><span className="font-medium">File:</span> {uploadedFile.name}</div>
                    <div><span className="font-medium">Parsing:</span> {isParsed ? "Populated all years" : "Parsing..."}</div>
                  </>
                ) : (
                  <>Upload a DARS PDF to populate your plan automatically.</>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between">
  <span className="text-sm text-gray-700">Show Grades</span>

  <button
    type="button"
    role="switch"
    aria-checked={showGrades}
    onClick={() => setShowGrades((v) => !v)}
    className={classNames(
      "relative inline-flex h-6 w-11 items-center rounded-full border transition-colors",
      showGrades ? "bg-blue-600 border-blue-600" : "bg-gray-200 border-gray-300"
    )}
  >
    <span
      className={classNames(
        "inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform",
        showGrades ? "translate-x-5" : "translate-x-0"
      )}
    />
  </button>
</div>
          </div>
        </aside>

        {/* Center */}
        <section className="space-y-4">
          <div className="flex items-center justify-end gap-3 text-sm">
            <button className="text-blue-700 hover:underline" type="button" onClick={expandAll}>Expand All</button>
            <span className="text-gray-300">|</span>
            <button className="text-blue-700 hover:underline" type="button" onClick={collapseAll}>Collapse All</button>
          </div>

          {/* All years (Freshman/Sophomore/Junior/Senior...) */}
          <div className="space-y-2">
            {plannerYears.length === 0 ? (
              <div className="rounded-lg border bg-white p-4 text-sm text-gray-600">
                Upload a DARS report to populate your class-year plan.
              </div>
            ) : (
              plannerYears.map((y) => (
                <AccordionRow
                  key={y.classYearLabel}
                  title={`${y.classYearLabel} year (${y.academicYearLabel})`}
                  open={Boolean(openMap[y.classYearLabel])}
                  onToggle={() => setOpenMap((prev) => ({ ...prev, [y.classYearLabel]: !prev[y.classYearLabel] }))}
                >
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                    {y.terms.map((t) => (
                      <TermCard key={t.name} term={t} showGrades={showGrades} />
                    ))}
                  </div>
                </AccordionRow>
              ))
            )}
          </div>
        </section>

        
      </main>
    </div>
  );
}