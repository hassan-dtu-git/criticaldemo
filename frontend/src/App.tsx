import { FormEvent, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

type CredentialCheck = {
  credential_ref: string;
  decision: "allow" | "deny" | "review" | "unknown";
  reason_codes: string[];
  checked_at: string;
  zone: string;
  valid_from: string | null;
  valid_until: string | null;
  credential_status: "active" | "expired" | "revoked" | "unknown";
  policy_version: string;
};

type Notice = {
  title: string;
  source_url: string;
  domain: string;
  excerpt: string | null;
  published_at: string | null;
  retrieved_at: string;
  source_type: "official" | "public" | "unknown";
  freshness: "fresh" | "stale" | "unknown";
  match_reason: string | null;
};

type NoticeResult = {
  status: "success" | "no_match" | "stale" | "provider_error";
  query: string;
  results: Notice[];
  retrieved_at: string;
  freshness_threshold_seconds: number;
  error: { code: string; message: string; retryable: boolean } | null;
};

type CaseCard = {
  case_id: string;
  created_at: string;
  summary: string;
  access_decision: "allow" | "deny" | "review" | "unknown";
  credential_check: CredentialCheck | null;
  notice_result: NoticeResult | null;
  vision_observation: null;
  matched_rules: string[];
  source_refs: Array<{ source_url: string; domain: string; title: string; published_at: string | null; retrieved_at: string; freshness: string; match_reason: string | null }>;
  uncertainty: string[];
  review_checklist: string[];
  review_status: "pending" | "in_review" | "resolved";
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.message || payload?.detail || "Request failed (" + response.status + ")";
    throw new Error(typeof message === "string" ? message : "Request was rejected. Check the input.");
  }
  return payload as T;
}

function prettyDate(value: string | null | undefined) {
  if (!value) return "Not supplied";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function StatusPill({ value }: { value: string }) {
  return <span className={"pill pill-" + value.replaceAll("_", "-")}>{value.replaceAll("_", " ")}</span>;
}

export default function App() {
  const [credentialRef, setCredentialRef] = useState("SYN-1042");
  const [zone, setZone] = useState("LAB-A");
  const [query, setQuery] = useState("official public service notice near a campus venue");
  const [location, setLocation] = useState("India");
  const [credential, setCredential] = useState<CredentialCheck | null>(null);
  const [notice, setNotice] = useState<NoticeResult | null>(null);
  const [card, setCard] = useState<CaseCard | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState("Ready for a synthetic access check.");

  async function runCheck(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setCard(null);
    setCredential(null);
    setNotice(null);
    try {
      setStage("Checking synthetic credential against deterministic rules…");
      const checked = await post<CredentialCheck>("/api/credential/check", {
        credential_ref: credentialRef.trim(),
        zone: zone.trim(),
      });
      setCredential(checked);
      setStage("Credential check complete. Retrieving public context…");
      const context = await post<NoticeResult>("/api/context/search-fetch", { query: query.trim(), location: location.trim() });
      setNotice(context);
      setStage("Composing evidence-linked review card…");
      const composed = await post<CaseCard>("/api/cases/compose", {
        credential_check: checked,
        notice_result: context,
        vision_observation: null,
      });
      setCard(composed);
      setStage("Review card ready. Human review is required before consequential action.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error.");
      setStage("Workflow incomplete. Missing results must not be treated as an all-clear.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="SecureEntry Lens home">
          <span className="brand-mark">SL</span>
          <span><strong>SecureEntry Lens</strong><small>Security verification &amp; incident intelligence</small></span>
        </a>
        <span className="top-tag">P0 · HUMAN REVIEW</span>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">EVIDENCE OVER ASSUMPTIONS</p>
          <h1>Access signals.<br /><em>Traceable review.</em></h1>
          <p className="hero-lede">Verify synthetic credentials with deterministic rules, then connect relevant public context with visible source provenance and uncertainty.</p>
          <div className="principles"><span>01 / Policy first</span><span>02 / Sources visible</span><span>03 / Human decides</span></div>
        </div>
        <aside className="hero-note">
          <span className="note-icon">i</span>
          <div><strong>Demo environment</strong><p>Use synthetic credential IDs only. Public notices are context, not evidence about a person. No automated enforcement.</p></div>
        </aside>
      </section>

      <section className="workspace">
        <div className="section-heading"><div><p className="eyebrow">01 / RUN A CHECK</p><h2>Review workspace</h2></div><span className="muted">Synthetic data only</span></div>
        <form className="input-panel" onSubmit={runCheck}>
          <label>Credential reference
            <select value={credentialRef} onChange={(e) => setCredentialRef(e.target.value)}>
              <option value="SYN-1042">SYN-1042 · Active demo credential</option>
              <option value="SYN-1043">SYN-1043 · Expired demo credential</option>
              <option value="SYN-1044">SYN-1044 · Revoked demo credential</option>
              <option value="SYN-9999">SYN-9999 · Unknown reference</option>
            </select>
          </label>
          <label>Requested zone
            <select value={zone} onChange={(e) => setZone(e.target.value)}>
              <option value="LAB-A">LAB-A</option><option value="ENTRY-A">ENTRY-A</option><option value="SERVER-ROOM">SERVER-ROOM</option>
            </select>
          </label>
          <label className="wide">Public context query
            <input value={query} onChange={(e) => setQuery(e.target.value)} minLength={3} maxLength={500} required />
          </label>
          <label>Location
            <input value={location} onChange={(e) => setLocation(e.target.value)} minLength={2} maxLength={100} required />
          </label>
          <div className="form-action"><button type="submit" disabled={busy}>{busy ? "Checking…" : "Run verification"} <span aria-hidden="true">↗</span></button><small>API: {API}</small></div>
        </form>
        <div className={"status-line " + (error ? "status-error" : "")} role="status">{error ? "Workflow issue: " + error : stage}</div>
      </section>

      {credential && <section className="result-grid">
        <article className="panel credential-panel">
          <div className="panel-head"><div><p className="eyebrow">02 / POLICY RESULT</p><h3>Credential check</h3></div><StatusPill value={credential.decision} /></div>
          <div className="decision-row"><span className="credential-icon">✓</span><div><strong>{credential.credential_ref}</strong><p>{credential.zone} · policy {credential.policy_version}</p></div></div>
          <dl className="facts"><div><dt>Credential status</dt><dd>{credential.credential_status}</dd></div><div><dt>Checked at</dt><dd>{prettyDate(credential.checked_at)}</dd></div><div><dt>Valid until</dt><dd>{prettyDate(credential.valid_until)}</dd></div></dl>
          <h4>Rule reasons</h4><div className="chips">{credential.reason_codes.map((reason) => <span className="chip" key={reason}>{reason.replaceAll("_", " ")}</span>)}</div>
        </article>
        <article className="panel context-panel">
          <div className="panel-head"><div><p className="eyebrow">03 / PUBLIC CONTEXT</p><h3>TinyFish Search → Fetch</h3></div>{notice && <StatusPill value={notice.status} />}</div>
          {!notice && <p className="empty">No context result is available yet.</p>}
          {notice?.error && <div className="warning"><strong>{notice.error.code}</strong><p>{notice.error.message}</p></div>}
          {notice?.status === "no_match" && <div className="empty">No usable notice matched the query. This is not proof that the location is safe.</div>}
          {notice?.results.map((item) => <div className="notice" key={item.source_url}>
            <div className="notice-meta"><span>{item.source_type}</span><span>{item.freshness} · {item.domain}</span></div>
            <h4><a href={item.source_url} target="_blank" rel="noreferrer">{item.title} ↗</a></h4>
            <p>{item.excerpt || "No excerpt was returned by the provider."}</p>
            <div className="timestamps"><span>Published: {prettyDate(item.published_at)}</span><span>Retrieved: {prettyDate(item.retrieved_at)}</span></div>
            {item.match_reason && <small>{item.match_reason}</small>}
          </div>)}
          {notice && <p className="provider-time">Retrieved {prettyDate(notice.retrieved_at)} · freshness threshold {Math.round(notice.freshness_threshold_seconds / 3600)}h</p>}
        </article>
      </section>}

      {card && <section className="case-section">
        <div className="section-heading"><div><p className="eyebrow">04 / SIGNATURE FEATURE</p><h2>Access Integrity Case Card</h2></div><StatusPill value={card.review_status} /></div>
        <article className="case-card">
          <div className="case-title"><div><span className="case-label">CASE REFERENCE</span><h3>{card.case_id}</h3></div><StatusPill value={card.access_decision} /></div>
          <p className="case-summary">{card.summary}</p>
          <div className="case-columns">
            <div><h4>Matched rules</h4>{card.matched_rules.length ? <ul>{card.matched_rules.map((rule) => <li key={rule}>{rule.replaceAll("_", " ")}</li>)}</ul> : <p className="muted">No rule result supplied.</p>}</div>
            <div><h4>Uncertainty &amp; limitations</h4>{card.uncertainty.length ? <ul>{card.uncertainty.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">No additional uncertainty recorded.</p>}</div>
          </div>
          <div className="review-checklist"><h4>Human review checklist</h4>{card.review_checklist.map((item, index) => <div key={item}><span>{String(index + 1).padStart(2, "0")}</span>{item}</div>)}</div>
          <footer className="case-footer"><span>Created {prettyDate(card.created_at)}</span><span>{card.source_refs.length} source reference(s)</span><strong>Human review required</strong></footer>
        </article>
      </section>}

      <footer className="site-footer"><span>SecureEntry Lens · P0 MVP</span><span>Security-first · Human review · Evidence over assumptions</span></footer>
    </main>
  );
}
