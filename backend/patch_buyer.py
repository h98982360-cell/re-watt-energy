import re

with open('frontend/src/App.tsx', encoding='utf-8') as f:
    src = f.read()

# ── 1. Overview: update CTA label and add buyer requirements panel ──────────

old_action = '+ Post requirement</button> : null}'
new_action = '+ Post material requirement</button> : null}'
src = src.replace(old_action, new_action, 1)

old_overview_panel = '''        <section className="panel activity-panel">
          <div className="panel-head"><div><span className="panel-kicker">YOUR WORKFLOW</span><h2>Next steps</h2></div><span className="panel-icon">✳</span></div>
          <div className="workflow-list">
            {(isSupplier
              ? [["01", "Get verified", props.user.is_verified ? "Business approved" : "Our team is reviewing your details", props.user.is_verified],
                ["02", "List your supply", userListings.length ? `${userListings.length} active listing(s)` : "Share your first material", userListings.length > 0],
                ["03", "Respond to matches", `${props.matches.length} match request(s)`, props.matches.length > 0]]
              : [["01", "Complete verification", props.user.is_verified ? "Business approved" : "Account is under review", props.user.is_verified],
                ["02", "Post a requirement", `${props.requirements.length} requirement(s) created`, props.requirements.length > 0],
                ["03", "Review aggregated supply", `${props.matches.length} match result(s)`, props.matches.length > 0]]
            ).map(([number, title, text, done]) => (
              <div className="workflow-item" key={number as string}><span className={`workflow-number ${done ? "done" : ""}`}>{done ? "✓" : number}</span><div><strong>{title as string}</strong><span>{text as string}</span></div><span className="workflow-arrow">›</span></div>
            ))}
          </div>
          <div className="impact-note"><span>↗</span><p>Good material, found faster.<br /><strong>That\'s a better kind of growth.</strong></p></div>
        </section>'''

new_overview_panel = '''        {isBuyer ? (
          <section className="panel activity-panel">
            <div className="panel-head"><div><span className="panel-kicker">YOUR REQUIREMENTS</span><h2>Active requirements</h2></div><button className="text-button" onClick={() => props.setView("requirements")}>View all ↗</button></div>
            <div className="workflow-list">
              {props.requirements.filter((r) => r.status !== "completed").slice(0, 3).map((req) => {
                const match = props.matches.find((m) => m.requirement_id === req.id);
                let stageLabel = "SEARCHING FOR SUPPLY";
                let stageCls = "stage-searching";
                if (match) {
                  if (match.status === "confirmed" || match.status === "in_progress" || match.status === "completed") {
                    stageLabel = "MATCH CONFIRMED"; stageCls = "stage-confirmed";
                  } else if (match.status === "requested" || match.status === "partially_accepted") {
                    stageLabel = "WAITING FOR SUPPLIER ACCEPTANCE"; stageCls = "stage-waiting";
                  } else {
                    stageLabel = "SUPPLY FOUND"; stageCls = "stage-found";
                  }
                }
                return (
                  <div className="workflow-item req-overview-row" key={req.id} onClick={() => { props.onSelectRequirement(req.id); props.setView("requirement-detail"); }} style={{cursor:"pointer"}}>
                    <div className="material-thumb small-thumb" style={{flexShrink:0}}>♧</div>
                    <div style={{flex:1,minWidth:0}}>
                      <strong style={{fontSize:"9px",color:"#566157",display:"block"}}>{req.material}</strong>
                      <span style={{fontSize:"8px",color:"#9aa39a"}}>{req.quantity.toLocaleString()} {req.unit}{req.delivery_counties.length > 0 ? ` · ${req.delivery_counties[0]}` : ""}</span>
                    </div>
                    <span className={`req-stage-badge ${stageCls}`}>{stageLabel}</span>
                  </div>
                );
              })}
              {props.requirements.filter((r) => r.status !== "completed").length === 0 && (
                <div className="overview-buyer-cta">
                  <p>Post your first requirement to find matching supply.</p>
                  <button className="button button-dark button-small" onClick={() => props.setView("requirements")}>+ Post requirement ↗</button>
                </div>
              )}
            </div>
            <div className="impact-note"><span>↗</span><p>Good material, found faster.<br /><strong>That\'s a better kind of growth.</strong></p></div>
          </section>
        ) : (
          <section className="panel activity-panel">
            <div className="panel-head"><div><span className="panel-kicker">YOUR WORKFLOW</span><h2>Next steps</h2></div><span className="panel-icon">✳</span></div>
            <div className="workflow-list">
              {(isSupplier
                ? [["01", "Get verified", props.user.is_verified ? "Business approved" : "Our team is reviewing your details", props.user.is_verified],
                  ["02", "List your supply", userListings.length ? `${userListings.length} active listing(s)` : "Share your first material", userListings.length > 0],
                  ["03", "Respond to matches", `${props.matches.length} match request(s)`, props.matches.length > 0]]
                : [["01", "Complete verification", props.user.is_verified ? "Business approved" : "Account is under review", props.user.is_verified],
                  ["02", "Post a requirement", `${props.requirements.length} requirement(s) created`, props.requirements.length > 0],
                  ["03", "Review aggregated supply", `${props.matches.length} match result(s)`, props.matches.length > 0]]
              ).map(([number, title, text, done]) => (
                <div className="workflow-item" key={number as string}><span className={`workflow-number ${done ? "done" : ""}`}>{done ? "✓" : number}</span><div><strong>{title as string}</strong><span>{text as string}</span></div><span className="workflow-arrow">›</span></div>
              ))}
            </div>
            <div className="impact-note"><span>↗</span><p>Good material, found faster.<br /><strong>That\'s a better kind of growth.</strong></p></div>
          </section>
        )}'''

src = src.replace(old_overview_panel, new_overview_panel, 1)

# ── 2. Overview props: add onSelectRequirement ───────────────────────────────

old_overview_sig = '''function Overview(props: {
  user: User;
  listings: Listing[];
  requirements: Requirement[];
  matches: Match[];
  transactions: Transaction[];
  setView: (view: View) => void;
  newListing: () => void;
})'''

new_overview_sig = '''function Overview(props: {
  user: User;
  listings: Listing[];
  requirements: Requirement[];
  matches: Match[];
  transactions: Transaction[];
  setView: (view: View) => void;
  newListing: () => void;
  onSelectRequirement: (id: number) => void;
})'''

src = src.replace(old_overview_sig, new_overview_sig, 1)

# ── 3. Overview call site: pass onSelectRequirement ─────────────────────────

old_overview_call = '''            <Overview
              user={user}
              listings={listings}
              requirements={requirements}
              matches={matches}
              transactions={transactions}
              setView={setView}
              newListing={() => setView("listings")}
            />'''

new_overview_call = '''            <Overview
              user={user}
              listings={listings}
              requirements={requirements}
              matches={matches}
              transactions={transactions}
              setView={setView}
              newListing={() => setView("listings")}
              onSelectRequirement={(id) => { setSelectedRequirementId(id); }}
            />'''

src = src.replace(old_overview_call, new_overview_call, 1)

# ── 4. RequirementsPage: add matches + onSelectRequirement props, clickable cards ──

old_req_sig = 'function RequirementsPage(props: { requirements: Requirement[]; materials: MaterialItem[]; busy: boolean; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {'

new_req_sig = 'function RequirementsPage(props: { requirements: Requirement[]; materials: MaterialItem[]; matches: Match[]; busy: boolean; onSubmit: (event: FormEvent<HTMLFormElement>) => void; onSelectRequirement: (id: number) => void }) {'

src = src.replace(old_req_sig, new_req_sig, 1)

old_req_desk = '''    <section className="panel table-panel">
      <div className="panel-head"><div><span className="panel-kicker">YOUR BUYER DESK</span><h2>Open requirements <span className="heading-count">{props.requirements.length}</span></h2></div></div>
      {props.requirements.map((item) => (
        <div className="req-card" key={item.id}>
          <div className="req-card-top">
            <div><strong className="req-material">{item.material}</strong><span className="req-title">{item.title}</span></div>
            <span className={`table-status ${item.status === "open" ? "active-status" : "pending-status"}`}>{item.status.replaceAll("_", " ")}</span>
          </div>
          <div className="req-card-meta">
            <span><strong>{item.quantity.toLocaleString()} {item.unit}</strong> requested</span>
            {item.delivery_counties && item.delivery_counties.length > 0 && <span>&#128205; {item.delivery_counties.join(", ")}</span>}
            {item.acceptable_conditions && item.acceptable_conditions.length > 0 && <span>{item.acceptable_conditions.join(" · ")}</span>}
          </div>
        </div>
      ))}
      {props.requirements.length === 0 && <EmptyState title="No requirements posted" text="Post a requirement above to find matching supply." />}
    </section>'''

new_req_desk = '''    <section className="panel table-panel">
      <div className="panel-head"><div><span className="panel-kicker">YOUR BUYER DESK</span><h2>Open requirements <span className="heading-count">{props.requirements.length}</span></h2></div></div>
      {props.requirements.map((item) => {
        const match = props.matches.find((m) => m.requirement_id === item.id);
        let stageLabel = "SEARCHING FOR SUPPLY";
        let stageCls = "stage-searching";
        if (match) {
          if (match.status === "confirmed" || match.status === "in_progress" || match.status === "completed") {
            stageLabel = "MATCH CONFIRMED"; stageCls = "stage-confirmed";
          } else if (match.status === "requested" || match.status === "partially_accepted") {
            stageLabel = "WAITING FOR SUPPLIER ACCEPTANCE"; stageCls = "stage-waiting";
          } else {
            stageLabel = "SUPPLY FOUND"; stageCls = "stage-found";
          }
        }
        return (
          <div className="req-card req-card-clickable" key={item.id} onClick={() => props.onSelectRequirement(item.id)} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && props.onSelectRequirement(item.id)}>
            <div className="req-card-top">
              <div><strong className="req-material">{item.material}</strong><span className="req-title">{item.title}</span></div>
              <span className={`req-stage-badge ${stageCls}`}>{stageLabel}</span>
            </div>
            <div className="req-card-meta">
              <span><strong>{item.quantity.toLocaleString()} {item.unit}</strong> requested</span>
              {item.delivery_counties && item.delivery_counties.length > 0 && <span>&#128205; {item.delivery_counties.join(", ")}</span>}
              {item.acceptable_conditions && item.acceptable_conditions.length > 0 && <span>{item.acceptable_conditions.join(" · ")}</span>}
            </div>
            <div className="req-card-action">Open ›</div>
          </div>
        );
      })}
      {props.requirements.length === 0 && <EmptyState title="No requirements posted" text="Post a requirement above to find matching supply." />}
    </section>'''

src = src.replace(old_req_desk, new_req_desk, 1)

# ── 5. Insert RequirementDetailPage before MatchesPage ──────────────────────

detail_component = '''
function RequirementDetailPage(props: {
  requirement: Requirement | null;
  match: Match | null;
  transactions: Transaction[];
  user: User;
  token: string | null;
  busy: boolean;
  onBack: () => void;
  onGoToTransactions: () => void;
  respondToMatch: (id: number, accept: boolean) => void;
  confirmReceipt: (id: number, qty: number) => void;
  recordPayment: (id: number) => void;
}) {
  const [insight, setInsight] = useState<CompatibilityInsight | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);
  const [insightError, setInsightError] = useState("");
  const [quantities, setQuantities] = useState<Record<number, string>>({});

  const loadInsight = async () => {
    if (!props.token || !props.match) return;
    setInsightLoading(true);
    setInsightError("");
    try {
      const response = await api<AIResponse<CompatibilityInsight>>("/ai/insights/requirement", {
        method: "POST",
        body: jsonBody({ requirement_id: props.match.requirement_id, match_id: props.match.id }),
      }, props.token);
      if (!response.available || !response.data) throw new Error(response.message || "AI insight is unavailable.");
      setInsight(response.data);
    } catch (reason) {
      setInsightError(reason instanceof Error ? reason.message : "AI insight is temporarily unavailable.");
    } finally {
      setInsightLoading(false);
    }
  };

  if (!props.requirement) {
    return <EmptyState title="Requirement not found" text="Go back and select a requirement." />;
  }

  const req = props.requirement;
  const match = props.match;

  const matchStageIndex = !match ? -1
    : match.status === "confirmed" || match.status === "in_progress" ? 2
    : match.status === "completed" ? 4
    : match.status === "requested" || match.status === "partially_accepted" ? 1
    : 0;

  const hasTransactions = props.transactions.length > 0;
  const txStageIndex = !hasTransactions ? -1
    : props.transactions.every((t) => t.status === "completed") ? 4
    : props.transactions.some((t) => t.status === "paid" || t.status === "payment_pending") ? 3
    : props.transactions.some((t) => t.quantity_received != null) ? 2
    : 1;

  const journeyStage = match?.status === "confirmed" || match?.status === "in_progress" || match?.status === "completed"
    ? (hasTransactions ? txStageIndex + 2 : 2)
    : matchStageIndex;

  return (
    <>
      <div className="detail-back">
        <button className="text-button" onClick={props.onBack}>← Back to requirements</button>
      </div>
      <PageHeading
        eyebrow="REQUIREMENT DETAIL"
        title={req.material}
        description={req.title}
      />

      {/* Journey progress */}
      <div className="buyer-journey">
        {["Post requirement", "Supply found", "Supplier acceptance", "Match confirmed", "Handover", "Qty confirmed", "Payment", "Completed"].map((stage, i) => (
          <div key={stage} className={`journey-step ${i <= journeyStage ? "journey-active" : ""} ${i === journeyStage ? "journey-current" : ""}`}>
            <span>{i < journeyStage ? "✓" : i + 1}</span>
            <small>{stage}</small>
          </div>
        ))}
      </div>

      {/* Requirement details */}
      <section className="panel detail-panel">
        <div className="panel-head"><div><span className="panel-kicker">WHAT YOU NEED</span><h2>Requirement details</h2></div>
          <span className={`table-status ${req.status === "open" ? "active-status" : req.status === "confirmed" ? "active-status" : "pending-status"}`}>{req.status.replaceAll("_", " ")}</span>
        </div>
        <div className="detail-grid">
          <div><span>Material</span><strong>{req.material}</strong></div>
          <div><span>Quantity</span><strong>{req.quantity.toLocaleString()} {req.unit}</strong></div>
          {req.acceptable_conditions.length > 0 && <div><span>Condition</span><strong>{req.acceptable_conditions.join(", ")}</strong></div>}
          {req.delivery_counties.length > 0 && <div><span>Location</span><strong>{req.delivery_counties.join(", ")}</strong></div>}
          {req.required_by && <div><span>Needed by</span><strong>{req.required_by}</strong></div>}
          {req.intended_use && <div><span>Intended use</span><strong>{req.intended_use}</strong></div>}
          {req.target_price_per_unit != null && <div><span>Target price</span><strong>KES {req.target_price_per_unit.toLocaleString()} / {req.unit}</strong></div>}
          {req.description && <div className="detail-full"><span>Additional notes</span><strong>{req.description}</strong></div>}
        </div>
      </section>

      {/* No match yet */}
      {!match && (
        <section className="panel detail-panel">
          <div className="panel-head"><div><span className="panel-kicker">MATCHING STATUS</span><h2>Searching for supply</h2></div></div>
          <div className="detail-status-note">
            <span className="status-searching-icon">⌕</span>
            <div>
              <strong>TAI is looking for compatible supply</strong>
              <p>When suppliers list compatible materials, a match will appear here automatically. Check back soon.</p>
            </div>
          </div>
        </section>
      )}

      {/* Match result */}
      {match && (
        <section className="panel detail-panel">
          <div className="panel-head">
            <div><span className="panel-kicker">MATCHING RESULT</span>
              <h2>{match.coverage_percent >= 100 ? "Supply found" : "Partial supply found"}</h2>
            </div>
            <span className={`table-status ${match.status === "confirmed" ? "active-status" : "pending-status"}`}>{match.status.replaceAll("_", " ")}</span>
          </div>

          <div className="match-result-grid">
            <div className="match-result-cell">
              <span>Required</span>
              <strong>{match.requested_quantity.toLocaleString()} {match.unit}</strong>
            </div>
            <div className="match-result-cell">
              <span>Aggregated supply</span>
              <strong>{match.matched_quantity.toLocaleString()} {match.unit}</strong>
            </div>
            <div className="match-result-cell">
              <span>Suppliers</span>
              <strong>{match.supplier_count}</strong>
            </div>
            <div className="match-result-cell">
              <span>Coverage</span>
              <strong className={match.coverage_percent >= 100 ? "coverage-full" : "coverage-partial"}>{match.coverage_percent.toFixed(0)}%</strong>
            </div>
          </div>

          <div className="match-checks">
            <div className="match-check-row">
              <span className={match.coverage_percent >= 100 ? "check-yes" : "check-no"}>{match.coverage_percent >= 100 ? "✓" : "✗"}</span>
              <span>Quantity sufficient</span>
              <strong>{match.coverage_percent >= 100 ? "Yes" : `No — shortfall: ${(match.requested_quantity - match.matched_quantity).toLocaleString()} ${match.unit}`}</strong>
            </div>
          </div>

          {match.coverage_percent < 100 && (
            <div className="partial-supply-note">
              <strong>Partial supply found</strong>
              <p>Required: {match.requested_quantity.toLocaleString()} {match.unit} · Available: {match.matched_quantity.toLocaleString()} {match.unit} · Shortfall: {(match.requested_quantity - match.matched_quantity).toLocaleString()} {match.unit}</p>
              <p>More supply may appear as additional suppliers join the marketplace.</p>
            </div>
          )}

          {/* Supplier responses */}
          <div className="supplier-responses">
            <strong className="responses-heading">Supplier responses</strong>
            <div className="table-scroll">
              <table>
                <thead><tr><th>Supplier</th><th>Material</th><th>Quantity</th><th>Location</th><th>Status</th></tr></thead>
                <tbody>
                  {match.items.map((item) => (
                    <tr key={item.listing_id}>
                      <td><span className="table-person"><i>{item.supplier_name.slice(0, 1)}</i>{item.supplier_name}</span></td>
                      <td>{item.title}</td>
                      <td><strong>{Number(item.quantity).toLocaleString()} <small>{item.unit}</small></strong></td>
                      <td>{item.county || "—"}</td>
                      <td><span className={`table-status ${item.condition === "accepted" ? "active-status" : "pending-status"}`}>{match.status === "confirmed" ? "Accepted" : match.status === "requested" ? "Pending" : match.status.replaceAll("_", " ")}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* AI Compatibility Insight */}
          <div className="match-footer">
            <div className="insight-mark">✳</div>
            <p><strong>Compatibility insight</strong><span>{match.explanation || "Backend rules matched compatible materials, conditions, and locations."}</span></p>
            {!insight && <button className="text-button" disabled={insightLoading} onClick={() => void loadInsight()}>{insightLoading ? "Loading…" : "AI insight"}</button>}
          </div>
          {insightError && <div className="alert error-alert" style={{marginTop:"10px"}}><span>!</span>AI insight is temporarily unavailable.</div>}
          {insight && (
            <div className="ai-match-insight">
              <strong>{insight.compatibility} compatibility</strong>
              <p>{insight.summary}</p>
              <span>{insight.reasons.join(" ")}</span>
              <small>{insight.considerations.join(" ")}</small>
            </div>
          )}

          {/* Match confirmed state */}
          {(match.status === "confirmed" || match.status === "in_progress" || match.status === "completed") && (
            <div className="match-confirmed-banner">
              <span>✓</span>
              <div>
                <strong>MATCH CONFIRMED</strong>
                <p>Required: {match.requested_quantity.toLocaleString()} {match.unit} · Aggregated: {match.matched_quantity.toLocaleString()} {match.unit} · {match.supplier_count} supplier(s)</p>
                {hasTransactions && <button className="button button-dark button-small" style={{marginTop:"8px"}} onClick={props.onGoToTransactions}>View transactions ↗</button>}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Transaction progress for buyer */}
      {props.transactions.length > 0 && (
        <section className="panel detail-panel">
          <div className="panel-head"><div><span className="panel-kicker">TRANSACTION PROGRESS</span><h2>Handover & payment</h2></div></div>
          {props.transactions.map((transaction) => (
            <div key={transaction.id} className="detail-transaction">
              <div className="detail-tx-head">
                <span className="panel-kicker">TXN #{String(transaction.id).padStart(5, "0")} · {transaction.supplier_name}</span>
                <span className={`table-status ${transaction.status === "completed" ? "active-status" : "pending-status"}`}>{transaction.status.replaceAll("_", " ")}</span>
              </div>
              <TransactionProgress status={transaction.status} />
              <div className="transaction-details">
                <div><span>Declared</span><strong>{transaction.quantity_declared.toLocaleString()} {transaction.unit}</strong></div>
                <div><span>Received</span><strong>{transaction.quantity_received == null ? "Awaiting confirmation" : `${transaction.quantity_received.toLocaleString()} ${transaction.unit}`}</strong></div>
                <div><span>Total</span><strong>{transaction.currency} {transaction.total.toLocaleString()}</strong></div>
              </div>
              {transaction.quantity_received == null && (
                <div className="transaction-actions">
                  <label>Quantity received ({transaction.unit})
                    <input type="number" min="0.01" step="0.01" value={quantities[transaction.id] || ""} onChange={(e) => setQuantities({ ...quantities, [transaction.id]: e.target.value })} />
                  </label>
                  <button className="button button-dark" disabled={props.busy || !quantities[transaction.id]} onClick={() => props.confirmReceipt(transaction.id, Number(quantities[transaction.id]))}>Confirm receipt ↗</button>
                </div>
              )}
              {transaction.status === "payment_pending" && (
                <div className="transaction-actions">
                  <span className="field-help">After paying the supplier directly, record a payment reference.</span>
                  <button className="button button-dark" disabled={props.busy} onClick={() => props.recordPayment(transaction.id)}>Record payment reference</button>
                </div>
              )}
              {transaction.payments.filter((p) => p.status === "pending").map((payment) => (
                <div className="payment-row" key={payment.id}>
                  <div><strong>Payment awaiting supplier confirmation</strong><span>{payment.method.replaceAll("_", " ")}{payment.reference ? ` · Ref ${payment.reference}` : ""}</span></div>
                </div>
              ))}
            </div>
          ))}
        </section>
      )}
    </>
  );
}

'''

# Insert before MatchesPage
src = src.replace('function MatchesPage(', detail_component + 'function MatchesPage(', 1)

with open('frontend/src/App.tsx', 'w', encoding='utf-8') as f:
    f.write(src)

print("SUCCESS")
