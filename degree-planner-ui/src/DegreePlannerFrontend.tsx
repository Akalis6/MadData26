import React, { useMemo, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker?url";
import Papa from "papaparse";
//temp for test
import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";

GlobalWorkerOptions.workerSrc = pdfWorker;

type TermStatus = "completed" | "in_progress" | "cart";
type CourseFlag = "in_progress" | "waitlisted" | "not_offered" | "no_longer_offered";

type Course = {
  id: string; // "COMP SCI 564" or catalog "ACCT I S 100"
  title: string;
  credits: number;
  grade?: string; // DARS only
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

// -------- Catalog types (CSV) --------
type CatalogCourse = {
  courseId: string; // "ACCT I S 100"
  title: string;
  credits: number;
  subject: string; // "ACCT I S"
  number: string; // "100"
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
        <span className={classNames(common, "text-[12px] font-bold px-2 py-1 rounded bg-gray-100 border")}>
          PDF
        </span>
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
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={onToggle}
        type="button"
      >
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

function TermCard({
  term,
  showGrades,
  onAddCourse,
}: {
  term: Term;
  showGrades: boolean;
  onAddCourse: (termName: string) => void;
}) {
  const tabs = useMemo(
    () => [
      { key: "completed" as const, label: `Completed (${term.completedCount})` },
      { key: "in_progress" as const, label: `In Progress (${term.inProgressCount})` },
      { key: "cart" as const, label: `Cart (${term.cartCount})` },
    ],
    [term.completedCount, term.inProgressCount, term.cartCount]
  );

  const [activeTab, setActiveTab] = useState<TermStatus>("completed");
  React.useEffect(() => {
  if (term.cartCount > 0) {
    setActiveTab("cart");
  }
}, [term.cartCount]);
  const courses = term.courses.filter((c) => c.status === activeTab);

  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="text-sm font-semibold text-gray-900">{term.name}</div>

        <div className="text-sm text-gray-700">
          <span className="font-medium">{term.totalCredits.toFixed(2)}</span> credits{" "}
          <button
            className="ml-2 inline-flex h-7 w-7 items-center justify-center rounded border bg-white hover:bg-gray-50"
            type="button"
            title="Add course"
            onClick={() => onAddCourse(term.name)}
          >
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
              <button
                className="rounded border bg-white px-3 py-1.5 text-sm hover:bg-gray-50"
                type="button"
                onClick={() => onAddCourse(term.name)}
              >
                + Add Course
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {courses.map((c, idx) => (
              <div key={`${term.name}-${c.id}-${c.title}-${c.grade ?? "NA"}-${idx}`} className="rounded-lg border bg-gray-50 px-3 py-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center">
                      <div className="truncate text-sm font-semibold text-gray-900">{c.id}</div>
                      <CourseFlagIcon flag={c.flag} />
                    </div>
                    <div className="text-xs text-gray-700 whitespace-normal break-words">{c.title}</div>
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

    const items = (content.items as any[])
      .map((it) => ({
        str: (it.str ?? "").trim(),
        y: it.transform?.[5] ?? 0,
        x: it.transform?.[4] ?? 0,
      }))
      .filter((it) => it.str.length > 0);

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
  const m = trimmed.match(/^(FA|SP|SU)\s*(\d{2})\s+(.+)$/i);
  if (!m) return null;

  const termCode = m[1].toUpperCase() as "FA" | "SP" | "SU";
  const year = 2000 + Number(m[2]);
  let rest = m[3].trim();

  // Fix stuck subject+number e.g. "SCI252" -> "SCI 252"
  rest = rest.replace(/([A-Z]{2,})(\d{3,4}[A-Z]?)/g, "$1 $2");

  const tokens = rest.split(" ").filter(Boolean);
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
  const normalized = text.replace(/\u00A0/g, " ");
  const anchorRe = /total\s+credits\s+for\s+the\s+degree/i;

  const m = normalized.match(anchorRe);
  const tail = m ? normalized.slice(m.index ?? 0) : normalized;

  const lines = tail
    .split(/\r?\n/)
    .map((l) => l.replace(/\s+/g, " ").trim())
    .filter(Boolean);

  const courseLineRe = /^(FA|SP|SU)\s*\d{2}\b/i;

  const candidates = lines.filter((l) => courseLineRe.test(l));
  const parsed = candidates.map(parseCourseLine).filter((x): x is ParsedCourse => Boolean(x));

  if (parsed.length === 0) {
    const allCandidates = normalized
      .split(/\r?\n/)
      .map((l) => l.replace(/\s+/g, " ").trim())
      .filter((l) => courseLineRe.test(l));

    const parsedAll = allCandidates.map(parseCourseLine).filter((x): x is ParsedCourse => Boolean(x));
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

function buildTerm(name: string, pcs: ParsedCourse[]): Term {
  const courses: Course[] = pcs.map((pc) => {
    const id = `${pc.subject} ${pc.number}`;
    const status = courseStatusFromGrade(pc.grade);

    return {
      id,
      title: pc.title,
      credits: pc.credits,
      grade: pc.grade,
      status,
      flag: pc.grade.toUpperCase() === "INP" ? "in_progress" : undefined,
    };
  });

  const completedCount = courses.filter((c) => c.status === "completed").length;
  const inProgressCount = courses.filter((c) => c.status === "in_progress").length;
  const cartCount = courses.filter((c) => c.status === "cart").length;
  const totalCredits = courses.reduce((sum, c) => sum + c.credits, 0);

  return {
    name,
    totalCredits,
    completedCount,
    inProgressCount,
    cartCount,
    courses,
  };
}

// -------- Catalog helpers --------
function safeNumber(x: any): number {
  if (x == null) return 0;
  const s = String(x).trim();
  if (!s) return 0;
  const n = Number.parseFloat(s);
  return Number.isFinite(n) ? n : 0;
}

function splitCourseId(courseId: string): { subject: string; number: string } {
  const tokens = courseId.trim().split(/\s+/);
  const last = tokens[tokens.length - 1] ?? "";
  if (/^\d{2,5}[A-Z]?$/.test(last)) {
    return { subject: tokens.slice(0, -1).join(" "), number: last };
  }
  return { subject: courseId.trim(), number: "" };
}

export default function DegreePlannerFrontend() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [showGrades, setShowGrades] = useState(true);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isParsed, setIsParsed] = useState(false);

  const [plannerYears, setPlannerYears] = useState<PlannerYear[]>([]);
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({});

  // -------- Catalog state --------
  const [catalog, setCatalog] = useState<CatalogCourse[]>([]);
  const [subjects, setSubjects] = useState<string[]>([]);

  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTermName, setDrawerTermName] = useState<string>("");
  const [drawerSubject, setDrawerSubject] = useState<string>("");
  const [drawerQuery, setDrawerQuery] = useState<string>("");
  const [drawerResults, setDrawerResults] = useState<CatalogCourse[]>([]);

  // Load catalog once
  React.useEffect(() => {
    fetch("/uwmadison_courses.csv")
      .then((r) => r.text())
      .then((text) => {
        const parsed = Papa.parse<Record<string, any>>(text, {
          header: true,
          skipEmptyLines: true,
        });

        const rows = (parsed.data ?? []).filter(Boolean);

        const mapped: CatalogCourse[] = rows
          .map((row) => {
            // 🔧 If your CSV headers differ, adjust here
            const courseId =
              row.courseId ?? row.course_id ?? row["course id"] ?? row["Course ID"] ?? row["courseId"] ?? "";
            const title =
              row.title ?? row.course_title ?? row["course title"] ?? row["Title"] ?? "";
            const creditsRaw =
  row.credit ??
  row.credits ??
  row.course_credits ??
  row["Credit"] ??
  row["Credits"] ??
  row["credit"] ??
  row["credit_hours"] ??
  row["Credit Hours"] ??
  0;
            if (!courseId || !title) return null;

            const { subject, number } = splitCourseId(String(courseId));
            return {
              courseId: String(courseId).trim(),
              title: String(title).trim(),
              credits: safeNumber(creditsRaw),
              subject,
              number,
            };
          })
          .filter((x): x is CatalogCourse => Boolean(x));

        setCatalog(mapped);

        const subj = Array.from(new Set(mapped.map((c) => c.subject))).sort((a, b) => a.localeCompare(b));
        setSubjects(subj);
      })
      .catch((e) => console.error("Failed to load uwmadison_courses.csv", e));
  }, []);

  function triggerUpload() {
    fileInputRef.current?.click();
  }

  async function onFileSelected(file: File | null) {
    setUploadedFile(file);
    setIsParsed(false);

    if (!file) return;

    const text = await extractTextFromPdf(file);
    const parsedCourses = extractCoursesFromDarsText(text);

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
          buildTerm(fall, fallCourses),
          buildTerm(spring, springCourses),
          buildTerm(summer, summerCourses),
        ],
      };
    });

    setPlannerYears(years);

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

  // -------- Drawer logic --------
  function openCourseDrawerForTerm(termName: string) {
    setDrawerTermName(termName);
    setDrawerSubject("");
    setDrawerQuery("");
    setDrawerResults([]);
    setDrawerOpen(true);
  }

  function runCourseSearch() {
    const subj = drawerSubject.trim();
    const q = drawerQuery.trim().toLowerCase();

    let filtered = catalog;

    if (subj) filtered = filtered.filter((c) => c.subject === subj);

    if (q) {
      filtered = filtered.filter((c) => {
        const numMatch = c.number.toLowerCase().includes(q);
        const titleMatch = c.title.toLowerCase().includes(q);
        const idMatch = c.courseId.toLowerCase().includes(q);
        return numMatch || titleMatch || idMatch;
      });
    }

    setDrawerResults(filtered.slice(0, 200));
  }

  function addCatalogCourseToTerm(course: CatalogCourse) {
    setPlannerYears((prev) =>
      prev.map((py) => ({
        ...py,
        terms: py.terms.map((t) => {
          if (t.name !== drawerTermName) return t;

          const newCourse: Course = {
            id: course.courseId,
            title: course.title,
            credits: course.credits,
            status: "cart",
          };

          const courses = [newCourse, ...t.courses];

          const completedCount = courses.filter((c) => c.status === "completed").length;
          const inProgressCount = courses.filter((c) => c.status === "in_progress").length;
          const cartCount = courses.filter((c) => c.status === "cart").length;
          const totalCredits = courses.reduce((sum, c) => sum + c.credits, 0);

          return { ...t, courses, completedCount, inProgressCount, cartCount, totalCredits };
        }),
      }))
    );

    setDrawerOpen(false);
  }

  //temp
  const tasks = useQuery(api.tasks.get);

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
              {/* for test */}
              {tasks?.map(({_id, text }) => <div key={_id}>{text}</div>)}
              <div className="mt-1 flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">{uploadedFile ? "DARS Report" : "No file uploaded"}</span>
                {uploadedFile && <Badge>PDF</Badge>}
              </div>
            </div>

            <button
              type="button"
              className="rounded border bg-white px-2 py-1 text-sm hover:bg-gray-50"
              onClick={triggerUpload}
            >
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
                    <div className="truncate">
                      <span className="font-medium">File:</span> {uploadedFile.name}
                    </div>
                    <div>
                      <span className="font-medium">Parsing:</span> {isParsed ? "Populated all years" : "Parsing..."}
                    </div>
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
            <button className="text-blue-700 hover:underline" type="button" onClick={expandAll}>
              Expand All
            </button>
            <span className="text-gray-300">|</span>
            <button className="text-blue-700 hover:underline" type="button" onClick={collapseAll}>
              Collapse All
            </button>
          </div>

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
                      <TermCard key={t.name} term={t} showGrades={showGrades} onAddCourse={openCourseDrawerForTerm} />
                    ))}
                  </div>
                </AccordionRow>
              ))
            )}
          </div>
        </section>
      </main>

      {/* -------- Right-side Course Search Drawer -------- */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/30" onClick={() => setDrawerOpen(false)} />

          <div className="absolute right-0 top-0 h-full w-full max-w-[420px] bg-white shadow-xl flex flex-col">
            <div className="bg-sky-700 text-white px-5 py-4 flex items-center justify-between">
              <div className="text-lg font-semibold">Course Search</div>
              <button
                className="rounded px-2 py-1 hover:bg-white/10"
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="p-5 space-y-5 overflow-auto">
              <div className="text-xs text-gray-500">Term</div>
              <div className="rounded border px-3 py-2 text-sm bg-gray-50">{drawerTermName || "—"}</div>

              <div>
                <label className="block text-xs text-gray-500 mb-2">Subject</label>
                <select
                  className="w-full rounded border px-3 py-2 text-sm"
                  value={drawerSubject}
                  onChange={(e) => setDrawerSubject(e.target.value)}
                >
                  <option value="">All subjects</option>
                  {subjects.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-2">Keyword, number</label>
                <div className="flex gap-2">
                  <input
                    className="flex-1 rounded border px-3 py-2 text-sm"
                    placeholder="e.g. 100 or accounting"
                    value={drawerQuery}
                    onChange={(e) => setDrawerQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") runCourseSearch();
                    }}
                  />
                  <button
                    className="rounded border px-4 py-2 text-sm font-semibold hover:bg-gray-50"
                    type="button"
                    onClick={runCourseSearch}
                  >
                    Search
                  </button>
                </div>

                <div className="mt-2 text-xs text-gray-500">
                  {drawerSubject
                    ? `Showing ${drawerResults.length} result(s) for ${drawerSubject}${drawerQuery ? ` + "${drawerQuery}"` : ""}`
                    : `Select a subject to narrow results (or search all).`}
                </div>
              </div>

              <div className="space-y-3">
                {drawerResults.map((c) => (
                  <div key={`${c.courseId}-${c.title}`} className="rounded-lg border bg-white p-3 shadow-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-gray-900">{c.courseId}</div>
                        <div className="text-xs text-gray-700 whitespace-normal break-words">{c.title}</div>
                      </div>
                      <div className="shrink-0 text-right text-xs text-gray-700">
                        <div className="font-medium">{c.credits.toFixed(2)} Cr</div>
                        <button
                          type="button"
                          className="mt-2 rounded border px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-gray-50"
                          onClick={() => addCatalogCourseToTerm(c)}
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                ))}

                {drawerResults.length === 0 && (
                  <div className="text-sm text-gray-600">
                    No results yet. Choose a subject and click Search.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}