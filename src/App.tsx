import { ChangeEvent, useMemo, useState } from "react";
import {
  Activity, ArrowRight, ArrowUpRight, Bell, CalendarDays, Check,
  CheckCircle2, ChevronDown, Clock3, FileCheck2, FileSpreadsheet,
  GraduationCap, LayoutDashboard, LogOut, Menu, Plus, Settings2,
  ShieldCheck, Sparkles, Users, XCircle, CircleAlert, MapPin,
  MoreHorizontal, ClipboardCheck, TrendingUp, CalendarClock, Upload,
  FileText, AlertTriangle, CheckCircle, Search, Download
} from "lucide-react";
import "./App.css";

type Role = "Student" | "Proctor" | "In-Charge";
type AttendanceRow = { studentId: string; attended: number; total: number; percentage: number; valid: boolean; message: string };

const events = [
  { title: "National Hackathon 2026", type: "Hackathon", date: "18 Oct 2026", place: "Vijayawada", status: "Approved" },
  { title: "AI & ML Innovation Summit", type: "Conference", date: "22 Oct 2026", place: "Hyderabad", status: "Under Review" },
  { title: "Google Developer Workshop", type: "Workshop", date: "25 Oct 2026", place: "On campus", status: "Pending" },
];

const requests = [
  { id: "PRM-2026-0142", student: "Reshma Sri", event: "National Hackathon 2026", attendance: "86%", status: "Under Proctor Review" },
  { id: "PRM-2026-0141", student: "Aarav Kumar", event: "AI & ML Innovation Summit", attendance: "92%", status: "Approved" },
  { id: "PRM-2026-0140", student: "Ananya Reddy", event: "Cloud Computing Workshop", attendance: "68%", status: "Returned for Correction" },
  { id: "PRM-2026-0139", student: "Rahul Varma", event: "CodeFest 2026", attendance: "78%", status: "Pending Final Decision" },
];

function Status({ value }: { value: string }) {
  const lower = value.toLowerCase();
  const cls = lower.includes("approved") ? "green" : lower.includes("reject") ? "red" : lower.includes("return") ? "orange" : lower.includes("review") || lower.includes("pending") ? "blue" : "gray";
  return <span className={`status ${cls}`}><span className="status-dot" />{value}</span>;
}

function StatCard({ icon: Icon, label, value, note, tone = "blue", trend }: {
  icon: typeof Activity; label: string; value: string; note: string; tone?: string; trend?: string;
}) {
  return <article className="stat-card"><div className="stat-top"><span className={`stat-icon ${tone}`}><Icon size={19} /></span>{trend && <span className="trend"><ArrowUpRight size={14} />{trend}</span>}</div><p className="stat-label">{label}</p><div className="stat-value">{value}</div><p className="stat-note">{note}</p></article>;
}

function RequestTable({ rows, student = false }: { rows: typeof requests; student?: boolean }) {
  return <div className="table-wrap"><table className="request-table"><thead><tr><th>REQUEST ID</th>{!student && <th>STUDENT</th>}<th>EVENT</th>{!student && <th>ATTENDANCE</th>}<th>STATUS</th><th /></tr></thead><tbody>{rows.map((r) => <tr key={r.id}><td><span className="request-id">{r.id}</span></td>{!student && <td><div className="student-cell"><span className="mini-avatar">{r.student.split(" ").map(s => s[0]).join("")}</span>{r.student}</div></td>}<td><span className="event-name">{r.event}</span></td>{!student && <td><span className={parseInt(r.attendance) < 75 ? "low-attendance" : ""}>{r.attendance}</span></td>}<td><Status value={r.status} /></td><td><button className="row-action" aria-label={`View ${r.id}`}><ArrowRight size={16} /></button></td></tr>)}</tbody></table>{rows.length === 0 && <div className="empty-state">No matching requests found.</div>}</div>;
}

function parseCsv(text: string): AttendanceRow[] {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter(line => line.trim());
  if (lines.length < 2) return [];
  const delimiter = lines[0].includes("\t") ? "\t" : ",";
  const headers = lines[0].split(delimiter).map(h => h.trim().toLowerCase().replace(/[^a-z0-9]/g, ""));
  const findIndex = (names: string[]) => headers.findIndex(h => names.includes(h));
  const idIndex = findIndex(["studentid", "id", "rollno", "rollnumber", "studentnumber"]);
  const attendedIndex = findIndex(["attended", "classesattended", "present", "classespresent"]);
  const totalIndex = findIndex(["total", "classestotal", "classesheld", "workingdays"]);
  return lines.slice(1).map(line => {
    const cells = line.split(delimiter).map(v => v.trim());
    const studentId = idIndex >= 0 ? (cells[idIndex] ?? "") : "";
    const attended = attendedIndex >= 0 ? Number(cells[attendedIndex]) : NaN;
    const total = totalIndex >= 0 ? Number(cells[totalIndex]) : NaN;
    const valid = Boolean(studentId) && Number.isFinite(attended) && Number.isFinite(total) && total > 0 && attended >= 0 && attended <= total;
    return { studentId, attended, total, percentage: valid ? Math.round((attended / total) * 1000) / 10 : 0, valid, message: valid ? "Valid" : "Check ID and attendance values" };
  });
}

function AttendanceImports() {
  const [file, setFile] = useState<File | null>(null);
  const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const validCount = rows.filter(row => row.valid).length;
  const invalidCount = rows.length - validCount;

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected); setRows([]); setMessage("");
    if (!selected) return;
    if (selected.name.toLowerCase().endsWith(".xlsx")) {
      setMessage("Excel file selected. To preview XLSX files, install the 'xlsx' package and connect its parser. CSV preview is available now.");
      return;
    }
    try {
      const text = await selected.text();
      const parsed = parseCsv(text);
      setRows(parsed);
      if (!parsed.length) setMessage("No records found. Use a header row and at least one student record.");
      else if (parsed.some(row => !row.valid)) setMessage("Preview created. Please correct rows marked 'Check ID and attendance values'.");
      else setMessage("Preview ready. Records have not been saved to the database.");
    } catch {
      setMessage("Could not read this file. Please choose a valid CSV file.");
    }
  }

  function downloadTemplate() {
    const content = "student_id,classes_attended,total_classes\nSTU001,42,48\nSTU002,38,45\n";
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8;" }));
    const link = document.createElement("a"); link.href = url; link.download = "permitrix-attendance-template.csv"; link.click(); URL.revokeObjectURL(url);
  }

  return <>
    <div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-dot" /> ATTENDANCE MANAGEMENT</div><h1>Attendance Imports</h1><p className="page-subtitle">Upload attendance records, validate student data, and review the import before saving.</p></div><button className="outline-button" onClick={downloadTemplate}><Download size={16} /> Download CSV template</button></div>
    <section className="panel" style={{ marginBottom: 20 }}>
      <div className="panel-heading"><div><h2>Upload attendance file</h2><p>Choose a CSV file to preview and validate attendance records. Excel selection is supported, but XLSX parsing needs an additional package.</p></div><FileSpreadsheet size={25} /></div>
      <label htmlFor="attendance-file" style={{ display: "block", padding: 24, border: "1px dashed #c9c7ed", borderRadius: 12, background: "#faf9ff", cursor: "pointer" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}><span className="stat-icon purple"><Upload size={20} /></span><div><strong style={{ display: "block", color: "#303a54" }}>Choose an attendance file</strong><span style={{ color: "#8991a5", fontSize: 12 }}>CSV or XLSX · Use the template for the expected column names</span></div></div>
        <input id="attendance-file" type="file" accept=".csv,.xlsx" onChange={handleFileChange} />
      </label>
      {file && <p style={{ color: "#626c83", fontSize: 12, marginTop: 14 }}><FileText size={15} style={{ verticalAlign: "middle", marginRight: 6 }} />Selected: <strong>{file.name}</strong> ({Math.max(1, Math.round(file.size / 1024))} KB)</p>}
      {message && <div role="status" style={{ marginTop: 16, padding: 12, borderRadius: 9, background: invalidCount ? "#fff5e7" : "#f1f0ff", color: invalidCount ? "#9a681f" : "#554bb7", fontSize: 12 }}>{invalidCount > 0 ? <AlertTriangle size={16} style={{ verticalAlign: "middle", marginRight: 7 }} /> : <CheckCircle size={16} style={{ verticalAlign: "middle", marginRight: 7 }} />}{message}</div>}
      {rows.length > 0 && <>
        <div className="stats-grid" style={{ marginTop: 20 }}><StatCard icon={FileCheck2} label="Records found" value={String(rows.length)} note="Rows in selected CSV" tone="purple" /><StatCard icon={CheckCircle2} label="Valid records" value={String(validCount)} note="Ready for backend validation" tone="green" /><StatCard icon={CircleAlert} label="Records to check" value={String(invalidCount)} note="Review highlighted rows" tone={invalidCount ? "orange" : "blue"} /><StatCard icon={GraduationCap} label="Eligibility threshold" value="75%" note="Configured demo threshold" tone="blue" /></div>
        <div className="panel-heading" style={{ marginTop: 24 }}><div><h2>Attendance preview</h2><p>Verify the records before sending them to the backend.</p></div><span className="status blue">{rows.length} records</span></div>
        <div className="table-wrap"><table className="request-table"><thead><tr><th>STUDENT ID</th><th>CLASSES ATTENDED</th><th>TOTAL CLASSES</th><th>ATTENDANCE</th><th>VALIDATION</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.studentId}-${index}`}><td>{row.studentId || "—"}</td><td>{Number.isFinite(row.attended) ? row.attended : "—"}</td><td>{Number.isFinite(row.total) ? row.total : "—"}</td><td>{row.valid ? `${row.percentage}%` : "—"}</td><td><Status value={row.message} /></td></tr>)}</tbody></table></div>
        <button className="primary-button" style={{ marginTop: 18 }} disabled={!rows.length || invalidCount > 0 || loading} onClick={() => { setLoading(true); setMessage("Validation passed. Database import is not connected yet; no records have been saved."); setLoading(false); }}><Upload size={16} />{loading ? "Validating…" : "Validate import"}</button>
      </>}
      <p style={{ marginTop: 18, color: "#8991a5", fontSize: 11 }}>Expected CSV headers: <code>student_id, classes_attended, total_classes</code>. This page currently previews and validates CSV data locally; it does not write to your database.</p>
    </section>
    <section className="panel"><div className="panel-heading"><div><h2>Import history</h2><p>Recent imports will appear here after backend integration.</p></div><Clock3 size={20} /></div><div className="empty-state">No attendance imports recorded yet.</div></section>
  </>;
}

function App() {
  const [role, setRole] = useState<Role>("Student");
  const [active, setActive] = useState("Overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const isStudent = role === "Student";
  const isProctor = role === "Proctor";
  const navItems = isStudent ? [
    { label: "Overview", icon: LayoutDashboard }, { label: "My Event Requests", icon: FileCheck2 }, { label: "Explore Events", icon: CalendarDays }, { label: "Attendance & Eligibility", icon: GraduationCap },
  ] : isProctor ? [
    { label: "Overview", icon: LayoutDashboard }, { label: "Assigned Students", icon: Users }, { label: "Request Reviews", icon: ClipboardCheck }, { label: "Attendance Issues", icon: CircleAlert },
  ] : [
    { label: "Overview", icon: LayoutDashboard }, { label: "All Requests", icon: FileCheck2 }, { label: "Attendance Imports", icon: FileSpreadsheet }, { label: "Reports & Analytics", icon: TrendingUp },
  ];
  const pageTitle = active === "Overview" ? `${role === "In-Charge" ? "In-Charge" : role} dashboard` : active;
  const visibleRequests = useMemo(() => requests.filter(r => `${r.id} ${r.student} ${r.event} ${r.status}`.toLowerCase().includes(query.toLowerCase())), [query]);
  const isDedicatedPage = active === "Attendance Imports" || active === "My Event Requests" || active === "Explore Events" || active === "Attendance & Eligibility" || active === "Assigned Students" || active === "Request Reviews" || active === "Attendance Issues" || active === "All Requests" || active === "Reports & Analytics" || active === "Notifications" || active === "Settings";

  return <div className="app-shell">
    {mobileOpen && <button className="mobile-overlay" onClick={() => setMobileOpen(false)} aria-label="Close menu" />}
    <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
      <div className="brand"><div className="brand-mark"><ShieldCheck size={24} strokeWidth={2.3} /></div><div><div className="brand-name">permitrix<span>.</span></div><div className="brand-subtitle">CAMPUS EVENT PORTAL</div></div><button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close sidebar"><XCircle size={19} /></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <div className="role-card"><div className="role-avatar">{isStudent ? <GraduationCap size={20} /> : isProctor ? <Users size={20} /> : <ShieldCheck size={20} />}</div><div className="role-text"><strong>{role}</strong><span>{isStudent ? "Student portal" : isProctor ? "Faculty workspace" : "Administration"}</span></div><ChevronDown size={16} className="muted-icon" /></div>
      <div className="nav-caption">MENU</div>
      <nav className="side-nav">{navItems.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${active === label ? "selected" : ""}`} onClick={() => { setActive(label); setMobileOpen(false); }}><Icon size={18} /><span>{label}</span>{label === "Request Reviews" && <span className="nav-count">8</span>}</button>)}</nav>
      <div className="nav-caption tools-caption">TOOLS</div>
      <nav className="side-nav"><button className={`nav-item ${active === "Notifications" ? "selected" : ""}`} onClick={() => { setActive("Notifications"); setMobileOpen(false); }}><Bell size={18} /><span>Notifications</span><span className="notification-dot" /></button><button className={`nav-item ${active === "Settings" ? "selected" : ""}`} onClick={() => { setActive("Settings"); setMobileOpen(false); }}><Settings2 size={18} /><span>Settings</span></button></nav>
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon"><Sparkles size={17} /></div><strong>Need a hand?</strong><p>Make event approvals simpler with Permitrix.</p><button onClick={() => window.alert("Help center will be connected soon.")}>Visit help center <ArrowRight size={14} /></button></div><div className="profile-row"><div className="profile-avatar">{isStudent ? "RS" : isProctor ? "PK" : "AD"}</div><div className="profile-info"><strong>{isStudent ? "Reshma Sri" : isProctor ? "Praveen Kumar" : "Event Administrator"}</strong><span>{role}</span></div><LogOut size={17} className="muted-icon" /></div></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="menu-toggle" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={21} /></button><div className="breadcrumb">Workspace <span>/</span> <strong>{active}</strong></div></div><div className="topbar-actions"><label className="role-switch"><span>Preview role</span><select value={role} onChange={e => { setRole(e.target.value as Role); setActive("Overview"); }}><option>Student</option><option>Proctor</option><option>In-Charge</option></select><ChevronDown size={14} /></label><button className="icon-button notification-button" aria-label="Notifications" onClick={() => setActive("Notifications")}><Bell size={19} /><span /></button><div className="top-avatar">{isStudent ? "RS" : isProctor ? "PK" : "AD"}</div></div></header>
      <div className="page-content">
        {active === "Attendance Imports" && role === "In-Charge" ? <AttendanceImports /> : isDedicatedPage && active !== "Overview" ? <>
          <div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-dot" /> MONDAY, OCTOBER 12, 2026</div><h1>{pageTitle}</h1><p className="page-subtitle">{active === "Explore Events" ? "Discover technical events and find your next opportunity." : active === "Request Reviews" ? "Review assigned student requests and record your recommendation." : active === "Notifications" ? "Updates about requests, attendance, and approvals." : active === "Settings" ? "Manage your Permitrix workspace preferences." : "Review records and information for campus event participation."}</p></div>{active === "Explore Events" && <button className="primary-button" onClick={() => setActive("My Event Requests")}><Plus size={17} /> My event requests</button>}</div>
          {active === "Explore Events" ? <section className="events-grid">{events.map((event, i) => <article className="event-card" key={event.title}><div className={`event-art art-${i + 1}`}><span>{event.type}</span><div className="event-art-icon"><Sparkles size={27} /></div></div><div className="event-card-body"><h3>{event.title}</h3><p><CalendarDays size={14} />{event.date}</p><p><MapPin size={14} />{event.place}</p><div className="event-card-footer"><Status value={event.status} /><button aria-label={`Request ${event.title}`} onClick={() => setActive("My Event Requests")}><ArrowRight size={17} /></button></div></div></article>)}</section> : active === "My Event Requests" || active === "All Requests" || active === "Request Reviews" || active === "Assigned Students" || active === "Attendance Issues" ? <section className="panel"><div className="panel-heading"><div><h2>{active}</h2><p>Search and review event participation requests.</p></div><label style={{ display: "flex", alignItems: "center", gap: 8 }}><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search requests..." /></label></div><RequestTable rows={visibleRequests} student={active === "My Event Requests"} /></section> : active === "Attendance & Eligibility" ? <section className="content-grid"><article className="panel"><div className="panel-heading"><div><h2>Attendance overview</h2><p>Your current academic attendance</p></div><GraduationCap size={22} /></div><div className="donut-wrap"><div className="donut"><div className="donut-center"><strong>86.4<span>%</span></strong><small>Attendance</small></div></div></div><p>Required attendance: 75%</p></article><article className="panel"><div className="panel-heading"><div><h2>Eligibility status</h2><p>Based on your latest attendance record</p></div><ShieldCheck size={22} /></div><div className="eligibility-status"><span className="eligibility-check"><Check size={21} /></span><div><strong>You're eligible!</strong><span>Ready for technical events</span></div></div></article></section> : active === "Reports & Analytics" ? <section className="content-grid"><article className="panel"><div className="panel-heading"><div><h2>Request distribution</h2><p>Sample workflow statistics</p></div><TrendingUp size={22} /></div><div className="distribution-total"><strong>148</strong><span>Total requests</span></div><p>Approved: 65% · Pending review: 22% · Other: 13%</p></article><article className="panel"><h2>Attendance issues</h2><p>11 records need review in this sample dashboard.</p></article></section> : <section className="panel"><div className="empty-state">No new items to display yet.</div></section>}
        </> : <>
          <div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-dot" /> MONDAY, OCTOBER 12, 2026</div><h1>Good morning, {isStudent ? "Reshma" : isProctor ? "Praveen" : "Admin"} <span className="wave">✦</span></h1><p className="page-subtitle">{isStudent ? "Here's what's happening with your event participation." : isProctor ? "Review your students' requests and keep approvals moving." : "Your overview of campus event participation and approvals."}</p></div>{isStudent ? <button className="primary-button" onClick={() => setActive("Explore Events")}><Plus size={17} /> New event request</button> : <button className="primary-button" onClick={() => setActive(isProctor ? "Request Reviews" : "Attendance Imports")}>{isProctor ? <ClipboardCheck size={17} /> : <FileSpreadsheet size={17} />}{isProctor ? "Review requests" : "Import attendance"}</button>}</div>
          {isStudent ? <>
            <section className="stats-grid"><StatCard icon={GraduationCap} label="Attendance percentage" value="86.4%" note="Above the required 75%" tone="purple" trend="+2.4%" /><StatCard icon={ShieldCheck} label="Event eligibility" value="Eligible" note="You can request participation" tone="green" /><StatCard icon={Clock3} label="Pending requests" value="02" note="1 awaiting proctor review" tone="orange" /><StatCard icon={CheckCircle2} label="Approved requests" value="04" note="Keep building your experience" tone="blue" /></section>
            <section className="content-grid"><article className="panel attendance-panel"><div className="panel-heading"><div><h2>Attendance overview</h2><p>Your current academic attendance</p></div><button className="subtle-icon" aria-label="Attendance options"><MoreHorizontal size={20} /></button></div><div className="attendance-content"><div className="donut-wrap"><div className="donut"><div className="donut-center"><strong>86.4<span>%</span></strong><small>Attendance</small></div></div></div><div className="attendance-legend"><div><span className="legend-dot purple-dot" /><span>Classes attended</span><strong>190</strong></div><div><span className="legend-dot light-dot" /><span>Classes missed</span><strong>30</strong></div><div className="threshold-note"><ShieldCheck size={16} /><span>You're 11.4% above the eligibility threshold.</span></div></div></div><div className="attendance-footer"><span><CheckCircle2 size={15} /> Last updated: 10 Oct 2026</span><button onClick={() => setActive("Attendance & Eligibility")}>View details <ArrowRight size={14} /></button></div></article><article className="panel eligibility-panel"><div className="panel-heading"><div><h2>Eligibility status</h2><p>Based on your latest attendance record</p></div><ShieldCheck className="eligibility-shield" size={22} /></div><div className="eligibility-status"><span className="eligibility-check"><Check size={21} /></span><div><strong>You're eligible!</strong><span>Ready for technical events</span></div></div><div className="eligibility-progress-label"><span>Attendance</span><strong>86.4% <small>/ 75% required</small></strong></div><div className="progress-track"><div style={{ width: "86.4%" }} /></div><div className="eligibility-callout"><Activity size={17} /><span>Keep attending classes to maintain your eligibility for upcoming events.</span></div></article></section>
            <section className="panel events-panel"><div className="panel-heading"><div><h2>Upcoming technical events</h2><p>Discover opportunities to learn, build and connect.</p></div><button className="text-button" onClick={() => setActive("Explore Events")}>Explore events <ArrowRight size={15} /></button></div><div className="events-grid">{events.map((event, i) => <article className="event-card" key={event.title}><div className={`event-art art-${i + 1}`}><span>{event.type}</span><div className="event-art-icon"><Sparkles size={27} /></div></div><div className="event-card-body"><h3>{event.title}</h3><p><CalendarDays size={14} />{event.date}</p><p><MapPin size={14} />{event.place}</p><div className="event-card-footer"><Status value={event.status} /><button aria-label={`View ${event.title}`} onClick={() => setActive("Explore Events")}><ArrowRight size={17} /></button></div></div></article>)}</div></section>
            <section className="panel requests-panel"><div className="panel-heading"><div><h2>Recent event requests</h2><p>Keep track of your participation applications.</p></div><button className="text-button" onClick={() => setActive("My Event Requests")}>View all requests <ArrowRight size={15} /></button></div><RequestTable rows={visibleRequests.slice(0, 3)} student /></section>
          </> : <>
            <section className="stats-grid"><StatCard icon={FileCheck2} label={isProctor ? "Assigned requests" : "Total requests"} value={isProctor ? "24" : "148"} note={isProctor ? "Across your assigned students" : "Across all departments"} tone="purple" /><StatCard icon={Clock3} label="Awaiting review" value={isProctor ? "08" : "18"} note="Requires attention" tone="orange" /><StatCard icon={CheckCircle2} label={isProctor ? "Recommended" : "Approved"} value={isProctor ? "12" : "96"} note={isProctor ? "Reviews completed" : "Final decisions recorded"} tone="green" trend="+12%" /><StatCard icon={CircleAlert} label="Attendance issues" value={isProctor ? "03" : "11"} note="Check eligibility records" tone="blue" /></section>
            <section className="content-grid admin-grid"><article className="panel chart-panel"><div className="panel-heading"><div><h2>Request activity</h2><p>Event requests received this week</p></div><button className="period-button">This week <ChevronDown size={14} /></button></div><div className="chart-legend"><span><i className="legend-dot purple-dot" />Submitted</span><span><i className="legend-dot teal-dot" />Approved</span></div><div className="bar-chart">{[["Mon", 46, 30], ["Tue", 70, 45], ["Wed", 55, 36], ["Thu", 88, 60], ["Fri", 65, 43], ["Sat", 38, 20], ["Sun", 48, 32]].map(([day, a, b]) => <div className="bar-group" key={String(day)}><div className="bars"><span className="bar bar-purple" style={{ height: `${a}%` }} /><span className="bar bar-teal" style={{ height: `${b}%` }} /></div><small>{day}</small></div>)}</div></article><article className="panel distribution-panel"><div className="panel-heading"><div><h2>Request distribution</h2><p>Current workflow status</p></div><MoreHorizontal size={20} className="muted-icon" /></div><div className="distribution-total"><strong>148</strong><span>Total requests</span></div>{[["Approved", 65, "green-fill"], ["Pending review", 22, "purple-fill"], ["Awaiting decision", 9, "orange-fill"], ["Rejected / returned", 4, "red-fill"]].map(([label, pct, cls]) => <div className="distribution-row" key={String(label)}><div><span>{label}</span><strong>{pct}%</strong></div><div className="progress-track"><div className={String(cls)} style={{ width: `${pct}%` }} /></div></div>)}</article></section>
            <section className="panel requests-panel"><div className="panel-heading"><div><h2>{isProctor ? "Requests awaiting review" : "Recent event requests"}</h2><p>{isProctor ? "Review assigned student requests and record your recommendation." : "Review the approval pipeline and make final decisions."}</p></div><button className="outline-button" onClick={() => setActive(isProctor ? "Request Reviews" : "All Requests")}>View all <ArrowRight size={15} /></button></div><RequestTable rows={visibleRequests} /></section>
            <section className="bottom-note"><div className="note-icon"><CalendarClock size={19} /></div><div><strong>{isProctor ? "Your reviews make a difference" : "Keep the approval process moving"}</strong><p>{isProctor ? "Check eligibility and add clear remarks before recommending a decision." : "Check attendance import freshness and review pending final decisions regularly."}</p></div><ArrowRight size={18} /></section>
          </>}
        </>}
        <footer className="footer"><span>© 2026 Permitrix</span><span>Making campus opportunities accessible <span className="footer-heart">♥</span></span><span><span className="online-dot" /> All systems operational</span></footer>
      </div>
    </main>
  </div>;
}

export default App;
