import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  AIResponse,
  Category,
  CompatibilityInsight,
  jsonBody,
  Listing,
  MaterialInsight,
  Match,
  Requirement,
  Transaction,
  User,
} from "./api";

type View = "overview" | "supply" | "listings" | "requirements" | "matches" | "transactions" | "admin" | "requirement-detail";

const TOKEN_KEY = "rewatt.accessToken";
const conditions = ["dry", "wet", "mixed", "contaminated", "processed", "unsorted", "unknown"];
const terminalMatchStatuses = new Set(["declined", "cancelled", "expired"]);

function isCurrentMatch(match: Match): boolean {
  return !terminalMatchStatuses.has(match.status);
}

function App() {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [pendingUsers, setPendingUsers] = useState<
    Array<{ user_id: number; name: string; email: string; role: string; business_name?: string; county?: string }>
  >([]);
  const [view, setView] = useState<View>("overview");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedRequirementId, setSelectedRequirementId] = useState<number | null>(null);

  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 4000);
    return () => clearTimeout(t);
  }, [notice]);

  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(""), 6000);
    return () => clearTimeout(t);
  }, [error]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [authMode, setAuthMode] = useState<"login" | "register">("register");
  const [role, setRole] = useState<"supplier" | "buyer">("supplier");
  const [showAuth, setShowAuth] = useState(false);

  const loadPublicData = useCallback(async () => {
    setLoading(true);
    try {
      const [catalog, supply] = await Promise.all([
        api<Category[]>("/catalog"),
        api<Listing[]>("/listings"),
      ]);
      setCategories(catalog);
      setListings(supply);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load marketplace data.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadWorkspace = useCallback(
    async (activeToken: string, activeUser: User) => {
      const requirementsRequest = activeUser.role === "supplier"
        ? Promise.resolve([] as Requirement[])
        : api<Requirement[]>("/requirements", {}, activeToken);
      const [supply, ownRequirements, ownMatches, ownTransactions] = await Promise.all([
        api<Listing[]>("/listings", {}, activeToken),
        requirementsRequest,
        api<Match[]>("/matches", {}, activeToken),
        api<Transaction[]>("/transactions", {}, activeToken),
      ]);
      setListings(supply);
      setRequirements(ownRequirements);
      setMatches(ownMatches);
      setTransactions(ownTransactions);
      if (activeUser.role === "admin") {
        const pending = await api<typeof pendingUsers>(
          "/admin/verifications/pending",
          {},
          activeToken,
        );
        setPendingUsers(pending);
      }
    },
    [],
  );

  useEffect(() => {
    void loadPublicData();
  }, [loadPublicData]);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    let mounted = true;
    api<User>("/auth/me", {}, token)
      .then(async (activeUser) => {
        if (!mounted) return;
        setUser(activeUser);
        await loadWorkspace(token, activeUser);
      })
      .catch(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        if (mounted) {
          setToken(null);
          setUser(null);
        }
      });
    return () => {
      mounted = false;
    };
  }, [token, loadWorkspace]);

  const materials = useMemo(
    () => categories.flatMap((category) => category.materials),
    [categories],
  );

  const refresh = async () => {
    await loadPublicData();
    if (token && user) await loadWorkspace(token, user);
  };

  const refreshRequirementMatch = useCallback(async (requirementId: number) => {
    if (!token) return null;
    const currentMatches = await api<Match[]>("/matches", {}, token);
    const existingMatch = currentMatches.find((match) => match.requirement_id === requirementId && isCurrentMatch(match));
    setMatches(currentMatches);
    if (existingMatch) return existingMatch;
    try {
      const match = await api<Match>(
        `/requirements/${requirementId}/matches`,
        { method: "POST" },
        token,
      );
      setMatches((current) => [match, ...current.filter((item) => item.requirement_id !== requirementId)]);
      setRequirements((current) => current.map((requirement) => requirement.id === requirementId
        ? { ...requirement, status: "match_requested" }
        : requirement));
      return match;
    } catch {
      return null;
    }
  }, [token]);

  const handleAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const path = authMode === "register" ? "/auth/register" : "/auth/login";
      const body =
        authMode === "register"
          ? {
              email: form.get("email"),
              password: form.get("password"),
              full_name: form.get("full_name"),
              role,
              phone: form.get("phone") || null,
              business_name: form.get("business_name"),
              business_type: form.get("business_type") || null,
              supplier_type: form.get("supplier_type") || null,
              county: form.get("county") || null,
            }
          : { email: form.get("email"), password: form.get("password") };
      const response = await api<{ access_token: string; user: User }>(path, {
        method: "POST",
        body: jsonBody(body),
      });
      sessionStorage.setItem(TOKEN_KEY, response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      setShowAuth(false);
      setNotice(
        authMode === "register"
          ? "Your account is ready. An admin must verify your business before you can publish or transact."
          : `Welcome back, ${response.user.full_name.split(" ")[0]}.`,
      );
      setView("overview");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setRequirements([]);
    setMatches([]);
    setTransactions([]);
    setNotice("You have been signed out.");
  };

  const createListing = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    setError("");
    try {
      await api("/listings", {
        method: "POST",
        body: jsonBody({
          material_id: Number(form.get("material_id")),
          title: form.get("title"),
          condition: form.get("condition"),
          quantity: Number(form.get("quantity")),
          unit: form.get("unit"),
          price_per_unit: form.get("price_per_unit")
            ? Number(form.get("price_per_unit"))
            : null,
          currency: "KES",
          county: form.get("county") || null,
          city: form.get("city") || null,
          available_from: form.get("available_from") || null,
          description: form.get("description") || null,
        }),
      }, token);
      formElement.reset();
      setNotice("Your material is now listed in the marketplace.");
      await refresh();
      setView("listings");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not publish the listing.");
    } finally {
      setBusy(false);
    }
  };

  const createRequirement = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const selectedConditions = form.getAll("conditions").map(String);
    setBusy(true);
    setError("");
    try {
      const requirement = await api<Requirement>("/requirements", {
        method: "POST",
        body: jsonBody({
          material_id: Number(form.get("material_id")),
          title: form.get("title"),
          quantity: Number(form.get("quantity")),
          unit: form.get("unit"),
          acceptable_conditions: selectedConditions,
          delivery_counties: String(form.get("delivery_counties") || "")
            .split(",")
            .map((county) => county.trim())
            .filter(Boolean),
          target_price_per_unit: form.get("target_price_per_unit")
            ? Number(form.get("target_price_per_unit"))
            : null,
          required_by: form.get("required_by") || null,
          intended_use: form.get("intended_use") || null,
          description: form.get("description") || null,
          currency: "KES",
        }),
      }, token);
      formElement.reset();
      setRequirements((current) => [requirement, ...current]);
      setNotice("Requirement posted. Searching for compatible supply...");
      const match = await refreshRequirementMatch(requirement.id);
      setSelectedRequirementId(requirement.id);
      setView("requirement-detail");
      if (match) {
        setNotice(match.quantity_sufficient
          ? "Requirement posted. Compatible supply found — check your Matches."
          : `Requirement posted. Partial supply found: ${match.matched_quantity.toLocaleString()} ${match.unit} available.`);
      } else {
        setNotice("Requirement saved. TAI is still searching for compatible supply.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not post your requirement.");
    } finally {
      setBusy(false);
    }
  };

  const respondToMatch = async (matchId: number, accept: boolean) => {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ status: string; transactions: number[] }>(
        `/matches/${matchId}/respond`,
        { method: "POST", body: jsonBody({ accept }) },
        token,
      );
      setNotice(
        result.transactions.length
          ? "All suppliers accepted. Transaction records are ready for handover."
          : accept
            ? "Your response was recorded. The match will confirm when every supplier accepts."
            : "The invitation was declined.",
      );
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not respond to the match.");
    } finally {
      setBusy(false);
    }
  };

  const reviewAccount = async (userId: number, decision: "verified" | "rejected") => {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await api(`/admin/verifications/${userId}`, {
        method: "PATCH",
        body: jsonBody({ decision }),
      }, token);
      setNotice(`Account ${decision}.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update verification.");
    } finally {
      setBusy(false);
    }
  };

  const confirmReceipt = async (transactionId: number, quantity: number) => {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await api(`/transactions/${transactionId}/confirm-receipt`, {
        method: "POST",
        body: jsonBody({ quantity_received: quantity }),
      }, token);
      setNotice("Receipt recorded. Add the payment reference after arranging payment directly.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not confirm receipt.");
    } finally {
      setBusy(false);
    }
  };

  const recordPayment = async (transactionId: number) => {
    if (!token) return;
    const reference = window.prompt("Enter the payment reference (or leave blank if unavailable):") || "";
    setBusy(true);
    setError("");
    try {
      await api(`/transactions/${transactionId}/payments`, {
        method: "POST",
        body: jsonBody({ method: "mobile_money", reference: reference || null }),
      }, token);
      setNotice("Payment record saved. The supplier can confirm receipt of funds.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not record payment.");
    } finally {
      setBusy(false);
    }
  };

  const confirmPayment = async (paymentId: number) => {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await api(`/payments/${paymentId}/confirm-received`, { method: "POST" }, token);
      setNotice("Payment receipt confirmed and transaction completed.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not confirm payment.");
    } finally {
      setBusy(false);
    }
  };

  if (!user) {
    if (loading && categories.length === 0) {
      return <div className="loading-screen" role="status">Loading the marketplace…</div>;
    }
    return (
      <Landing
        showAuth={showAuth}
        setShowAuth={setShowAuth}
        authMode={authMode}
        setAuthMode={setAuthMode}
        role={role}
        setRole={setRole}
        handleAuth={handleAuth}
        busy={busy}
        categories={categories}
        listings={listings}
        error={error}
        setError={setError}
      />
    );
  }

  const activeView = user.role === "admin" && view === "overview" ? "admin" : view;
  const navActiveView = activeView === "requirement-detail" ? "requirements" : activeView;
  const navItems: Array<{ id: View; label: string; icon: string }> = [
    { id: "overview", label: "Overview", icon: "⌂" },
    { id: "supply", label: "Browse supply", icon: "◉" },
    ...(user.role === "supplier" ? [{ id: "listings" as View, label: "My listings", icon: "▤" }] : []),
    ...(user.role === "buyer" ? [{ id: "requirements" as View, label: "Requirements", icon: "⌕" }] : []),
    { id: "matches", label: "Matches", icon: "⇄" },
    { id: "transactions", label: "Transactions", icon: "↗" },
    ...(user.role === "admin" ? [{ id: "admin" as View, label: "Verification", icon: "✓" }] : []),
  ];

  const pageTitle: Record<View, string> = {
    overview: "Your marketplace",
    supply: "Available supply",
    listings: "Your material listings",
    requirements: "Procurement requirements",
    "requirement-detail": "Requirement details",
    matches: "Aggregated matches",
    transactions: "Transaction history",
    admin: "Verification queue",
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => setView("overview")}>
          <span className="brand-mark">R</span>
          <span>re-watt<span className="brand-period">.</span></span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav">
          {navItems.map((item) => (
            <button
              className={`nav-item ${navActiveView === item.id ? "selected" : ""}`}
              key={item.id}
              onClick={() => setView(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>{item.label}
              {item.id === "matches" && matches.length > 0 && (
                <span className="nav-count">{matches.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="note-icon">✳</span>
            <strong>Small supplies.<br />One market.</strong>
            <p>Make useful materials easier to find, buy, and track.</p>
          </div>
          <div className="user-mini">
            <div className="avatar">{user.full_name.slice(0, 1).toUpperCase()}</div>
            <div className="user-mini-copy">
              <strong>{user.full_name}</strong>
              <span>{user.role}</span>
            </div>
            <button className="icon-button logout-icon" onClick={logout} title="Sign out" aria-label="Sign out">↗</button>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">Workspace <span>/</span> {pageTitle[activeView]}</div>
          <div className="topbar-right">
            <span className={`status-pill ${user.is_verified ? "verified" : "pending"}`}>
              <span className="status-dot" />{user.is_verified ? "Verified" : "Verification pending"}
            </span>
            <button className="icon-button" onClick={logout} title="Sign out" aria-label="Sign out">↗</button>
          </div>
        </header>
        <section className="page-content">
          {error && <div className="alert error-alert"><span>!</span>{error}<button onClick={() => setError("")}>×</button></div>}
          {notice && <div className="alert success-alert"><span>✓</span>{notice}<button onClick={() => setNotice("")}>×</button></div>}
          {activeView === "overview" && (
            <Overview
              user={user}
              listings={listings}
              requirements={requirements}
              matches={matches}
              transactions={transactions}
              setView={setView}
              newListing={() => setView("listings")}
              onSelectRequirement={(id) => { setSelectedRequirementId(id); setView("requirement-detail"); }}
            />
          )}
          {activeView === "supply" && <Supply listings={listings} user={user} />}
          {activeView === "listings" && (
            <ListingsPage
              user={user}
              listings={listings.filter((listing) => listing.supplier_id === user.id)}
              materials={materials}
              busy={busy}
              token={token}
              onSubmit={createListing}
            />
          )}
          {activeView === "requirements" && (
            <RequirementsPage
              requirements={requirements}
              materials={materials}
              matches={matches}
              busy={busy}
              onSubmit={createRequirement}
              onSelectRequirement={(id) => { setSelectedRequirementId(id); setView("requirement-detail"); }}
            />
          )}
          {activeView === "requirement-detail" && (
            <RequirementDetailPage
              requirement={requirements.find((r) => r.id === selectedRequirementId) ?? null}
              match={matches.find((m) => m.requirement_id === selectedRequirementId && isCurrentMatch(m)) ?? null}
              transactions={transactions.filter((t) => matches.find((m) => m.requirement_id === selectedRequirementId && isCurrentMatch(m) && m.id === t.match_id))}
              user={user}
              token={token}
              busy={busy}
              refreshMatch={refreshRequirementMatch}
              onBack={() => setView("requirements")}
              onGoToTransactions={() => setView("transactions")}
              respondToMatch={respondToMatch}
              confirmReceipt={confirmReceipt}
              recordPayment={recordPayment}
            />
          )}
          {activeView === "matches" && (
            <MatchesPage user={user} matches={matches} busy={busy} token={token} respond={respondToMatch} />
          )}
          {activeView === "transactions" && (
            <TransactionsPage
              user={user}
              transactions={transactions}
              busy={busy}
              confirmReceipt={confirmReceipt}
              recordPayment={recordPayment}
              confirmPayment={confirmPayment}
            />
          )}
          {activeView === "admin" && (
            <AdminPage users={pendingUsers} busy={busy} review={reviewAccount} />
          )}
        </section>
      </main>
    </div>
  );
}

function Landing(props: {
  showAuth: boolean;
  setShowAuth: (value: boolean) => void;
  authMode: "login" | "register";
  setAuthMode: (value: "login" | "register") => void;
  role: "supplier" | "buyer";
  setRole: (value: "supplier" | "buyer") => void;
  handleAuth: (event: FormEvent<HTMLFormElement>) => void;
  busy: boolean;
  categories: Category[];
  listings: Listing[];
  error: string;
  setError: (value: string) => void;
}) {
  return (
    <div className="landing">
      <header className="landing-nav">
        <a className="brand" href="#">
          <span className="brand-mark">R</span>
          <span>re-watt<span className="brand-period">.</span></span>
        </a>
        <nav className="landing-links">
          <a href="#how-it-works">How it works</a>
          <a href="#marketplace">Marketplace</a>
          <button className="button button-outline button-small" onClick={() => { props.setAuthMode("login"); props.setShowAuth(true); }}>
            Log in
          </button>
          <button className="button button-dark button-small" onClick={() => { props.setAuthMode("register"); props.setShowAuth(true); }}>
            Join the marketplace <span>↗</span>
          </button>
        </nav>
      </header>

      {props.error && <div className="landing-error">{props.error}<button onClick={() => props.setError("")}>×</button></div>}

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="live-dot" /> KENYA'S MATERIAL MARKETPLACE</div>
          <h1>Small supplies.<br />One <em>market.</em></h1>
          <p className="hero-description">
            We bring fragmented material supply together, so useful resources reach the businesses that need them.
          </p>
          <div className="hero-actions">
            <button className="button button-dark button-large" onClick={() => { props.setRole("supplier"); props.setAuthMode("register"); props.setShowAuth(true); }}>
              I have materials <span>↗</span>
            </button>
            <button className="button button-outline button-large" onClick={() => { props.setRole("buyer"); props.setAuthMode("register"); props.setShowAuth(true); }}>
              I need materials <span>↗</span>
            </button>
          </div>
          <div className="hero-trust">
            <div className="trust-avatars"><i>W</i><i>K</i><i>M</i></div>
            <span>Connecting local supply to real demand</span>
          </div>
        </div>
        <div className="hero-art" aria-label="Illustration of material supply being aggregated">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="orbit-label label-top">LOCAL MATERIAL <span>↘</span></div>
          <div className="supply-card supply-one"><span className="supply-icon">♧</span><span><b>Supplier supply</b><small>Material, condition, location</small></span></div>
          <div className="supply-card supply-two"><span className="supply-icon icon-coral">⌕</span><span><b>Buyer demand</b><small>Requirements from businesses</small></span></div>
          <div className="aggregate-core"><span className="core-spark">✳</span><b>TAI</b><small>SUPPLY + DEMAND</small><span className="core-sub">READY TO CONNECT</span></div>
          <div className="supply-card supply-three"><span className="supply-icon icon-gold">↗</span><span><b>Shared market</b><small>Clearer opportunities</small></span></div>
          <div className="orbit-label label-bottom">CONNECTED MARKET <span>↗</span></div>
          <div className="art-decoration leaf-shape">✳</div>
        </div>
      </section>

      <section className="proof-strip">
        <div><strong>Small supplies.</strong><span>Collected from local suppliers.</span></div>
        <div><strong>One market.</strong><span>Connected to real demand.</span></div>
        <div><strong>Clear next steps.</strong><span>List, discover, connect.</span></div>
        <div className="proof-mark">TAI <span>TRUSTED AGGREGATION & INTELLIGENCE</span></div>
      </section>

      <section className="how-section" id="how-it-works">
        <div className="section-kicker">HOW TAI WORKS</div>
        <div className="section-heading">
          <h2>From what you have<br /><em>to what businesses need.</em></h2>
        </div>
        <div className="steps">
          {[
            ["01", "List", "Tell us what material you have."],
            ["02", "Discover", "See businesses looking for it."],
            ["03", "Aggregate", "TAI brings fragmented supply together."],
            ["04", "Connect & transact", "Suppliers and buyers complete the transaction."],
          ].map(([number, title, detail]) => (
            <article className="step-card" key={number}>
              <span className="step-number">{number}</span><span className="step-arrow">↗</span>
              <h3>{title}</h3><p>{detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="aggregation-story">
        <div className="section-kicker">SMALL SUPPLIES. ONE MARKET. REAL DEMAND.</div>
        <h2>TAI brings scattered supply into view.</h2>
        <div className="aggregation-equation">
          <div className="equation-supplies"><strong>Local suppliers</strong><span>→</span><strong>TAI marketplace</strong><span>→</span><strong>Business buyers</strong></div>
          <div className="equation-arrow">↓</div>
          <strong className="equation-total">Connect with clarity</strong>
          <div className="equation-arrow">↓</div>
          <span>Real quantities and match results come from the backend after you sign in.</span>
        </div>
      </section>

      <section className="audience-section">
        <div className="section-kicker">WHO IS TAI FOR?</div>
        <div className="audience-grid">
          <article className="audience-card">
            <span className="audience-icon">♧</span>
            <h2>I have material</h2>
            <p>For farmers, small producers, and businesses with recoverable materials.</p>
            <button className="button button-dark" onClick={() => { props.setRole("supplier"); props.setAuthMode("register"); props.setShowAuth(true); }}>List your material <span>↗</span></button>
          </article>
          <article className="audience-card audience-card-light">
            <span className="audience-icon">⌕</span>
            <h2>I need material</h2>
            <p>For biomass processors, briquette producers, pellet manufacturers, and buyers.</p>
            <button className="button button-outline" onClick={() => { props.setRole("buyer"); props.setAuthMode("register"); props.setShowAuth(true); }}>Post a requirement <span>↗</span></button>
          </article>
        </div>
      </section>

      <section className="ai-secondary-section">
        <div><div className="section-kicker">SMARTER DECISIONS</div><h2>Useful intelligence, at the right moment.</h2></div>
        <p>Suppliers understand potential uses for their material. Buyers understand how compatible available supply is with their requirement.</p>
      </section>

      <footer className="landing-footer">
        <a className="brand" href="#"><span className="brand-mark">R</span><span>re-watt<span className="brand-period">.</span></span></a>
        <span>Turning scattered supply into shared opportunity.</span><span>© 2026 Re-Watt Energy</span>
      </footer>

      {props.showAuth && (
        <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) props.setShowAuth(false); }}>
          <section className="auth-modal">
            <button className="modal-close" onClick={() => props.setShowAuth(false)} aria-label="Close">×</button>
            <div className="eyebrow"><span className="live-dot" /> RE-WATT MARKETPLACE</div>
            <h2>{props.authMode === "login" ? "Welcome back." : "Join the movement."}</h2>
            <p className="modal-subtitle">{props.authMode === "login" ? "Sign in to continue to your workspace." : "Create an account to connect with local material markets."}</p>
            {props.authMode === "register" && (
              <div className="role-select">
                <button className={props.role === "supplier" ? "active" : ""} onClick={() => props.setRole("supplier")} type="button">I have materials</button>
                <button className={props.role === "buyer" ? "active" : ""} onClick={() => props.setRole("buyer")} type="button">I need materials</button>
              </div>
            )}
            <form className="form-stack" onSubmit={props.handleAuth}>
              {props.authMode === "register" && (
                <>
                  <label>Full name<input name="full_name" required minLength={2} placeholder="Your name" autoComplete="name" /></label>
                  <label>{props.role === "supplier" ? "Farm or business name" : "Business name"}<input name="business_name" required minLength={2} placeholder="Organisation name" /></label>
                  <div className="form-row">
                    <label>County<input name="county" placeholder="e.g. Kiambu" /></label>
                    <label>Phone<input name="phone" type="tel" placeholder="+254…" autoComplete="tel" /></label>
                  </div>
                  {props.role === "supplier" ? (
                    <label>Supplier type<select name="supplier_type" required defaultValue="farmer"><option value="farmer">Farmer</option><option value="small_producer">Small producer</option><option value="business">Business</option></select></label>
                  ) : (
                    <label>Business type<select name="business_type" defaultValue="biomass_processor"><option value="biomass_processor">Biomass processor</option><option value="manufacturer">Manufacturer</option><option value="recycler">Recycler</option><option value="other">Other</option></select></label>
                  )}
                </>
              )}
              <label>Email address<input name="email" type="email" required placeholder="you@business.com" autoComplete="email" /></label>
              <label>Password<input name="password" type="password" minLength={8} maxLength={72} required placeholder="At least 8 characters" autoComplete={props.authMode === "login" ? "current-password" : "new-password"} /></label>
              <button className="button button-dark button-full" disabled={props.busy}>
                {props.busy ? "Please wait…" : props.authMode === "login" ? "Log in" : "Create account"} <span>↗</span>
              </button>
            </form>
            <div className="auth-switch">
              {props.authMode === "login" ? "New to Re-Watt?" : "Already have an account?"}
              <button onClick={() => props.setAuthMode(props.authMode === "login" ? "register" : "login")}>
                {props.authMode === "login" ? "Create account" : "Log in"}
              </button>
            </div>
            <p className="auth-footnote">Accounts are reviewed by our team before marketplace activity is enabled.</p>
          </section>
        </div>
      )}
    </div>
  );
}

function PageHeading(props: { eyebrow: string; title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="page-heading">
      <div><div className="section-kicker">{props.eyebrow}</div><h1>{props.title}</h1>{props.description && <p>{props.description}</p>}</div>
      {props.action}
    </div>
  );
}

function Overview(props: {
  user: User;
  listings: Listing[];
  requirements: Requirement[];
  matches: Match[];
  transactions: Transaction[];
  setView: (view: View) => void;
  newListing: () => void;
  onSelectRequirement: (id: number) => void;
}) {
  const isSupplier = props.user.role === "supplier";
  const isBuyer = props.user.role === "buyer";
  const userListings = props.listings.filter((listing) => listing.supplier_id === props.user.id);
  const completed = props.transactions.filter((transaction) => transaction.status === "completed").length;
  return (
    <>
      <PageHeading
        eyebrow={`GOOD TO SEE YOU, ${props.user.full_name.split(" ")[0].toUpperCase()}`}
        title={isSupplier ? "Your supply, in good company." : isBuyer ? "Let’s find what you need." : "Marketplace at a glance."}
        description={isSupplier ? "Bring your materials to the businesses looking for them." : isBuyer ? "Discover verified supply, brought together for your next order." : "Review new businesses and keep the marketplace trusted."}
        action={isSupplier ? <button className="button button-dark" onClick={props.newListing}>+ List material</button> : isBuyer ? <button className="button button-dark" onClick={() => props.setView("requirements")}>+ Post material requirement</button> : null}
      />
      {!props.user.is_verified && props.user.role !== "admin" && (
        <div className="verification-banner"><span className="verification-symbol">◷</span><div><strong>Your account is under review</strong><p>Our team checks business details before you can publish materials or request a match.</p></div><span className="pending-tag">IN REVIEW</span></div>
      )}
      <div className="metric-grid">
        <Metric label={isSupplier ? "Active listings" : "Available listings"} value={isSupplier ? userListings.length : props.listings.length} note="Live on the marketplace" icon="▤" />
        <Metric label={isBuyer ? "Open requirements" : "Your matches"} value={isBuyer ? props.requirements.filter((item) => item.status !== "completed").length : props.matches.length} note="Across your workspace" icon="⇄" />
        <Metric label="Transactions" value={props.transactions.length} note={`${completed} completed`} icon="↗" />
        <Metric label="Trust status" value={props.user.is_verified ? "Verified" : "Pending"} note="Admin reviewed business" icon="✓" positive={props.user.is_verified} />
      </div>
      <div className="dashboard-grid">
        <section className="panel main-panel">
          <div className="panel-head"><div><span className="panel-kicker">MARKET ACTIVITY</span><h2>{isSupplier ? "Your latest listings" : "Available material"}</h2></div><button className="text-button" onClick={() => props.setView(isSupplier ? "listings" : "supply")}>View all ↗</button></div>
          {(isSupplier ? userListings : props.listings).slice(0, 4).map((listing) => (
            <div className="listing-row" key={listing.id}>
              <div className="material-thumb small-thumb">♧</div>
              <div className="row-main"><strong>{listing.material}</strong><span>{listing.county || "Kenya"} · {listing.condition}</span></div>
              <div className="row-quantity"><strong>{listing.quantity_available.toLocaleString()} {listing.unit}</strong><span>available</span></div>
              <span className="table-status active-status">Active</span>
            </div>
          ))}
          {(isSupplier ? userListings : props.listings).length === 0 && <EmptyState title="Nothing listed yet" text={isSupplier ? "Add your first material listing once your account is verified." : "New verified listings will appear here."} />}
        </section>
        {isBuyer ? (
          <section className="panel activity-panel">
            <div className="panel-head"><div><span className="panel-kicker">YOUR REQUIREMENTS</span><h2>Active requirements</h2></div><button className="text-button" onClick={() => props.setView("requirements")}>View all ↗</button></div>
            <div className="workflow-list">
              {props.requirements.filter((requirement) => requirement.status !== "completed").slice(0, 3).map((requirement) => {
                const match = props.matches.find((candidate) => candidate.requirement_id === requirement.id);
                const confirmed = match?.status === "confirmed" || match?.status === "in_progress" || match?.status === "completed";
                const waiting = match?.status === "requested" || match?.status === "partially_accepted";
                const stage = !match ? "SEARCHING FOR SUPPLY" : confirmed ? "MATCH CONFIRMED" : waiting ? "WAITING FOR SUPPLIER ACCEPTANCE" : "SUPPLY FOUND";
                return <button className="workflow-item req-overview-row" key={requirement.id} onClick={() => { props.onSelectRequirement(requirement.id); }}>
                  <div className="material-thumb small-thumb">♧</div>
                  <div className="row-main"><strong>{requirement.material}</strong><span>{requirement.quantity.toLocaleString()} {requirement.unit} · {requirement.acceptable_conditions.join(", ") || "Any condition"} · {requirement.delivery_counties.join(", ") || "Any location"}</span></div>
                  <span className={`req-stage-badge ${confirmed ? "stage-confirmed" : waiting ? "stage-waiting" : match ? "stage-found" : "stage-searching"}`}>{stage}</span>
                </button>;
              })}
              {props.requirements.length === 0 && <EmptyState title="No requirements posted" text="Post a requirement to start finding supply." />}
            </div>
            <div className="impact-note"><span>↗</span><p>Current status, match facts, and next action.<br /><strong>Everything stays in one place.</strong></p></div>
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
            <div className="impact-note"><span>↗</span><p>Good material, found faster.<br /><strong>That’s a better kind of growth.</strong></p></div>
          </section>
        )}
      </div>
    </>
  );
}

function Metric(props: { label: string; value: string | number; note: string; icon: string; positive?: boolean }) {
  return <div className="metric-card"><div className="metric-top"><span>{props.label}</span><span className="metric-icon">{props.icon}</span></div><strong className={`metric-value ${props.positive ? "metric-positive" : ""}`}>{props.value}</strong><span className="metric-note">{props.note}</span></div>;
}

function Supply({ listings, user }: { listings: Listing[]; user: User }) {
  return <>
    <PageHeading eyebrow="THE OPEN MARKET" title="Available supply" description="Browse active material listings from across the marketplace." />
    <div className="market-summary"><span className="market-summary-icon">✳</span><div><strong>Scattered supply, brought into view.</strong><p>Check the condition, location, and available amount before requesting a match.</p></div><span className="summary-count">{listings.length} listings</span></div>
    <div className="supply-grid">
      {listings.map((listing) => <article className="supply-tile" key={listing.id}>
        <div className="tile-top"><div className="material-thumb">♧</div><span className="table-status active-status">Available</span></div>
        <div className="section-kicker">{listing.county || "KENYA"}{listing.city ? ` · ${listing.city.toUpperCase()}` : ""}</div>
        <h3>{listing.material}</h3><p className="tile-title">{listing.title}</p>
        <div className="tile-quantity"><strong>{listing.quantity_available.toLocaleString()}</strong><span>{listing.unit} available</span></div>
        <div className="tile-meta"><span>Condition</span><strong>{listing.condition}</strong></div>
        <div className="tile-meta"><span>Listed by</span><strong>{listing.supplier_name}{listing.supplier_id === user.id ? " · you" : ""}</strong></div>
        <div className="tile-meta"><span>Indicative price</span><strong>{listing.price_per_unit == null ? "Ask supplier" : `${listing.currency} ${listing.price_per_unit.toLocaleString()} / ${listing.unit}`}</strong></div>
      </article>)}
    </div>
    {listings.length === 0 && <EmptyState title="The marketplace is getting ready" text="No active supply is available yet. Verified supplier listings will show here." />}
  </>;
}

function ListingsPage(props: { user: User; listings: Listing[]; materials: ReturnType<typeof flattenMaterials>; busy: boolean; token: string | null; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  const [insight, setInsight] = useState<MaterialInsight | null>(null);
  const [insightListingId, setInsightListingId] = useState<number | null>(null);
  const [insightError, setInsightError] = useState("");

  const loadInsight = async (listingId: number) => {
    if (!props.token) return;
    setInsightListingId(listingId);
    setInsightError("");
    try {
      const response = await api<AIResponse<MaterialInsight>>("/ai/insights/listing", {
        method: "POST",
        body: jsonBody({ listing_id: listingId }),
      }, props.token);
      if (!response.available || !response.data) throw new Error(response.message || "AI insight is unavailable.");
      setInsight(response.data);
    } catch (reason) {
      setInsightError(reason instanceof Error ? reason.message : "AI insight is unavailable.");
    } finally {
      setInsightListingId(null);
    }
  };

  return <>
    <PageHeading eyebrow="SUPPLIER WORKSPACE" title="Your material listings" description="Turn your available materials into supply buyers can discover." />
    {!props.user.is_verified ? <div className="verification-banner"><span className="verification-symbol">◷</span><div><strong>Verification required before publishing</strong><p>We’ll activate listing tools after an admin has verified your supplier account.</p></div><span className="pending-tag">PENDING</span></div> : (
      <section className="panel form-panel"><div className="panel-head"><div><span className="panel-kicker">ADD TO THE MARKET</span><h2>List available material</h2></div></div>
        <form className="market-form" onSubmit={props.onSubmit}>
          <label>Material<select name="material_id" required>{props.materials.map((material) => <option value={material.id} key={material.id}>{material.name}</option>)}</select></label>
          <label>Listing title<input name="title" required minLength={3} placeholder="e.g. Dry maize cobs from this harvest" /></label>
          <div className="form-row"><label>Quantity<input name="quantity" type="number" required min="0.01" step="0.01" placeholder="500" /></label><label>Unit<select name="unit" defaultValue="kg"><option value="kg">Kilograms (kg)</option><option value="tonne">Tonnes</option><option value="pieces">Pieces</option></select></label><label>Condition<select name="condition">{conditions.map((condition) => <option key={condition} value={condition}>{condition}</option>)}</select></label></div>
          <div className="form-row"><label>County<input name="county" placeholder="e.g. Kiambu" /></label><label>Town<input name="city" placeholder="e.g. Thika" /></label><label>Available from<input name="available_from" type="date" /></label></div>
          <div className="form-row"><label>Indicative price (KES / unit)<input name="price_per_unit" type="number" min="0" step="0.01" placeholder="Optional" /></label><label>Notes<textarea name="description" rows={2} placeholder="Share details buyers should know" /></label></div>
          <div className="form-actions"><span>Quantity and condition are confirmed by the buyer at handover.</span><button className="button button-dark" disabled={props.busy}>{props.busy ? "Publishing…" : "Publish listing"} <span>↗</span></button></div>
        </form>
      </section>
    )}
    <section className="panel table-panel"><div className="panel-head"><div><span className="panel-kicker">YOUR CATALOGUE</span><h2>Active listings <span className="heading-count">{props.listings.length}</span></h2></div></div>
      {props.listings.map((listing) => <div className="listing-row" key={listing.id}><div className="material-thumb small-thumb">♧</div><div className="row-main"><strong>{listing.material}</strong><span>{listing.county || "Kenya"} · {listing.condition}</span></div><div className="row-quantity"><strong>{listing.quantity_available.toLocaleString()} {listing.unit}</strong><span>available</span></div><span className="table-status active-status">{listing.status.replaceAll("_", " ")}</span><button className="text-button" disabled={insightListingId === listing.id} onClick={() => void loadInsight(listing.id)}>{insightListingId === listing.id ? "Loading…" : "AI insight"}</button></div>)}
      {props.listings.length === 0 && <EmptyState title="No listings yet" text={props.user.is_verified ? "Publish your first material above." : "Your listings will appear here once your account is verified."} />}
    </section>
    {insightError && <div className="alert error-alert"><span>!</span>{insightError}</div>}
    {insight && <section className="panel insight-panel"><div className="panel-head"><div><span className="panel-kicker">AI MATERIAL INSIGHT</span><h2>{insight.material}</h2></div><span className="table-status active-status">{insight.confidence} confidence</span></div><p>{insight.summary}</p><div className="insight-columns"><div><strong>Potential uses</strong><span>{insight.potential_uses.join(", ")}</span></div><div><strong>Potential buyers</strong><span>{insight.potential_buyer_types.join(", ")}</span></div><div><strong>Characteristics</strong><span>{insight.important_characteristics.join(", ")}</span></div></div><small>{insight.disclaimer}</small></section>}
  </>;
}

type MaterialItem = { id: number; name: string; typical_conditions: string[] };
function flattenMaterials(categories: Category[]): MaterialItem[] {
  return categories.flatMap((category) => category.materials);
}

function RequirementsPage(props: { requirements: Requirement[]; materials: MaterialItem[]; matches: Match[]; busy: boolean; onSubmit: (event: FormEvent<HTMLFormElement>) => void; onSelectRequirement: (id: number) => void }) {
  return <>
    <PageHeading eyebrow="BUYER WORKSPACE" title="What do you need?" description="Tell TAI what material you are looking for and we will find compatible supply." />
    <section className="panel form-panel">
      <div className="panel-head"><div><span className="panel-kicker">CREATE A REQUIREMENT</span></div></div>
      <form className="market-form" onSubmit={props.onSubmit}>
        <div className="req-field-group">
          <div className="req-field-label">Material</div>
          <div className="req-field-desc">What are you sourcing?</div>
          <select name="material_id" required>{props.materials.map((m) => <option value={m.id} key={m.id}>{m.name}</option>)}</select>
        </div>
        <div className="req-field-group">
          <div className="req-field-label">Requirement title</div>
          <input name="title" required minLength={3} placeholder="e.g. Dry maize cobs for briquette production" />
        </div>
        <div className="req-field-group">
          <div className="req-field-label">Quantity</div>
          <div className="req-field-desc">How much do you need?</div>
          <div className="form-row">
            <input name="quantity" type="number" required min="0.01" step="0.01" placeholder="2000" />
            <select name="unit" defaultValue="kg"><option value="kg">Kilograms (kg)</option><option value="tonne">Tonnes</option><option value="pieces">Pieces</option></select>
          </div>
        </div>
        <div className="req-field-group">
          <div className="req-field-label">Condition</div>
          <div className="req-field-desc">What condition do you need? <span className="field-help">(No selection means any condition)</span></div>
          <div className="condition-options">{conditions.map((c) => <label key={c} className="checkbox-pill"><input type="checkbox" name="conditions" value={c} />{c}</label>)}</div>
        </div>
        <div className="req-field-group">
          <div className="req-field-label">Where do you need it?</div>
          <div className="req-field-desc">Enter one or more counties separated by commas</div>
          <input name="delivery_counties" placeholder="e.g. Kiambu, Nairobi, Nyeri" />
        </div>
        <div className="req-field-group">
          <div className="req-field-label">When do you need it?</div>
          <input name="required_by" type="date" />
        </div>
        <div className="req-field-group">
          <div className="req-field-label">Target price per unit <span className="field-help">(optional)</span></div>
          <input name="target_price_per_unit" type="number" min="0" step="0.01" placeholder="KSh / unit" />
        </div>
        <div className="req-field-group">
          <div className="req-field-label">Intended use</div>
          <div className="req-field-desc">What will you use it for?</div>
          <input name="intended_use" placeholder="e.g. Biomass processing" />
        </div>
        <div className="req-field-group">
          <div className="req-field-label">Additional requirements <span className="field-help">(optional)</span></div>
          <textarea name="description" rows={2} placeholder="Any additional quality or supply requirements..." />
        </div>
        <div className="form-actions">
          <span>We will match based on: Material &bull; Quantity &bull; Condition &bull; Location &bull; Availability</span>
          <button className="button button-dark" disabled={props.busy}>{props.busy ? "Finding supply..." : "Post Requirement"} <span>&#8599;</span></button>
        </div>
      </form>
    </section>
    <section className="panel table-panel">
      <div className="panel-head"><div><span className="panel-kicker">YOUR BUYER DESK</span><h2>Open requirements <span className="heading-count">{props.requirements.length}</span></h2></div></div>
      {props.requirements.map((item) => {
        const match = props.matches.find((m) => m.requirement_id === item.id && isCurrentMatch(m));
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
    </section>
  </>;
}


function RequirementDetailPage(props: {
  requirement: Requirement | null;
  match: Match | null;
  transactions: Transaction[];
  user: User;
  token: string | null;
  refreshMatch: (requirementId: number) => Promise<Match | null>;
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
  const [matching, setMatching] = useState(false);

  useEffect(() => {
    if (!props.requirement || props.match || !props.token) {
      setMatching(false);
      return;
    }
    let active = true;
    setMatching(true);
    void props.refreshMatch(props.requirement.id).finally(() => {
      if (active) setMatching(false);
    });
    return () => {
      active = false;
    };
  }, [props.requirement?.id, props.match?.id, props.token, props.refreshMatch]);

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

  useEffect(() => {
    setInsight(null);
    setInsightError("");
    if (!props.token || !props.match) return;
    let active = true;
    setInsightLoading(true);
    void api<AIResponse<CompatibilityInsight>>("/ai/insights/requirement", {
      method: "POST",
      body: jsonBody({ requirement_id: props.match.requirement_id, match_id: props.match.id }),
    }, props.token)
      .then((response) => {
        if (!active) return;
        if (!response.available || !response.data) throw new Error(response.message || "AI insight is unavailable.");
        setInsight(response.data);
      })
      .catch(() => {
        if (active) setInsightError("AI insight is temporarily unavailable.");
      })
      .finally(() => {
        if (active) setInsightLoading(false);
      });
    return () => {
      active = false;
    };
  }, [props.match?.id, props.token]);

  if (!props.requirement) {
    return <EmptyState title="Requirement not found" text="Go back and select a requirement." />;
  }

  const req = props.requirement;
  const match = props.match;

  const hasTransactions = props.transactions.length > 0;
  const transactionStage = !hasTransactions ? 4
    : props.transactions.every((transaction) => transaction.status === "completed") ? 7
    : props.transactions.some((transaction) => transaction.status === "paid" || transaction.status === "payment_pending") ? 6
    : props.transactions.some((transaction) => transaction.quantity_received != null) ? 5
    : 4;
  const journeyStage = !match ? 0
    : match.status === "confirmed" || match.status === "in_progress" || match.status === "completed"
      ? transactionStage
      : match.status === "requested" || match.status === "partially_accepted" ? 2 : 1;
  const acceptedCount = match?.items.filter((item) => item.response_status === "accepted" || item.response_status === "fulfilled").length ?? 0;
  const pendingCount = match?.items.filter((item) => item.response_status === "invited").length ?? 0;
  const declinedCount = match?.items.filter((item) => item.response_status === "declined").length ?? 0;
  const completedTransactions = props.transactions.filter((transaction) => transaction.status === "completed").length;
  const paymentPendingTransactions = props.transactions.filter((transaction) => transaction.status === "payment_pending").length;
  const receiptPendingTransactions = props.transactions.filter((transaction) => transaction.quantity_received == null).length;
  const actionTitle = !match
    ? "TAI is finding compatible supply"
    : match.status === "requested" || match.status === "partially_accepted"
      ? "Waiting for supplier acceptance"
      : match.status === "confirmed" && props.transactions.length > 0
        ? "Move through handover and payment"
        : "Match result is available";
  const actionText = !match
    ? "No buyer action is needed right now. TAI checks backend marketplace supply for this requirement."
    : match.status === "requested" || match.status === "partially_accepted"
      ? `${acceptedCount} supplier(s) accepted, ${pendingCount} pending${declinedCount ? `, ${declinedCount} declined` : ""}. The match confirms only when the backend receives all required acceptances.`
      : props.transactions.length > 0
        ? `${receiptPendingTransactions} transaction(s) need quantity confirmation, ${paymentPendingTransactions} await payment recording, and ${completedTransactions} are completed.`
        : "The backend has confirmed the match. Transaction records will appear here after acceptance processing completes.";

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

      <section className="panel detail-panel buyer-next-step">
        <div>
          <span className="panel-kicker">CURRENT STATE</span>
          <strong>{actionTitle}</strong>
          <p>{actionText}</p>
        </div>
        {!match && <button className="button button-outline button-small" disabled={matching || props.busy} onClick={() => void props.refreshMatch(req.id)}>{matching ? "Checking..." : "Check backend again"}</button>}
        {match && props.transactions.length > 0 && <button className="button button-outline button-small" onClick={props.onGoToTransactions}>Open transactions</button>}
      </section>

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
          <div className="panel-head"><div><span className="panel-kicker">MATCHING STATUS</span><h2>{matching ? "Searching for supply" : "No compatible supply yet"}</h2></div></div>
          <div className="detail-status-note">
            <span className="status-searching-icon">⌕</span>
            <div>
              <strong>{matching ? "TAI is looking for compatible supply" : "TAI is still looking for compatible supply"}</strong>
              <p>{matching ? "TAI is checking the existing marketplace supply now." : "When compatible supply is available, use Check backend again to refresh this requirement from the matching API."}</p>
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
              <span className={match.quantity_sufficient ? "check-yes" : "check-no"}>{match.quantity_sufficient ? "✓" : "✗"}</span>
              <span>Quantity sufficient</span>
              <strong>{match.quantity_sufficient ? "Yes" : `No — shortfall: ${match.shortfall.toLocaleString()} ${match.unit}`}</strong>
            </div>
            <div className="match-check-row">
              <span className={match.material_compatible ? "check-yes" : "check-no"}>{match.material_compatible ? "✓" : "✗"}</span>
              <span>Material compatible</span>
              <strong>{match.material_compatible ? "Yes" : "No"}</strong>
            </div>
            <div className="match-check-row">
              <span className={match.condition_compatible ? "check-yes" : "check-no"}>{match.condition_compatible ? "✓" : "✗"}</span>
              <span>Condition compatible</span>
              <strong>{match.condition_compatible ? "Yes" : "No"}</strong>
            </div>
            <div className="match-check-row">
              <span>Supply balance</span>
              <strong>{match.surplus > 0 ? `${match.surplus.toLocaleString()} ${match.unit} surplus` : match.shortfall > 0 ? `${match.shortfall.toLocaleString()} ${match.unit} shortfall` : "No shortfall"}</strong>
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
                      <td><span className={`table-status ${item.response_status === "accepted" || item.response_status === "fulfilled" ? "active-status" : "pending-status"}`}>{item.response_status === "invited" ? "Pending" : item.response_status.replaceAll("_", " ")}</span></td>
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
            {!insight && <button className="text-button" disabled={insightLoading} onClick={() => void loadInsight()}>{insightLoading ? "Loading..." : "Retry AI insight"}</button>}
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
                <div><span>Price per unit</span><strong>{transaction.currency} {transaction.unit_price.toLocaleString()} / {transaction.unit}</strong></div>
                <div><span>Total</span><strong>{transaction.currency} {transaction.total.toLocaleString()}</strong></div>
                <div><span>Payment</span><strong>{transaction.payments.length ? `${transaction.payments[0].method.replaceAll("_", " ")} · ${transaction.payments[0].status}` : "Not recorded"}</strong></div>
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

function MatchesPage(props: { user: User; matches: Match[]; busy: boolean; token: string | null; respond: (id: number, accept: boolean) => void }) {
  const [insights, setInsights] = useState<Record<number, CompatibilityInsight>>({});
  const [insightLoading, setInsightLoading] = useState<number | null>(null);
  const [insightError, setInsightError] = useState("");

  const loadInsight = async (match: Match) => {
    if (!props.token) return;
    setInsightLoading(match.id);
    setInsightError("");
    try {
      const response = await api<AIResponse<CompatibilityInsight>>("/ai/insights/requirement", {
        method: "POST",
        body: jsonBody({ requirement_id: match.requirement_id, match_id: match.id }),
      }, props.token);
      if (!response.available || !response.data) throw new Error(response.message || "AI insight is unavailable.");
      setInsights((current) => ({ ...current, [match.id]: response.data as CompatibilityInsight }));
    } catch (reason) {
      setInsightError(reason instanceof Error ? reason.message : "AI insight is unavailable.");
    } finally {
      setInsightLoading(null);
    }
  };

  return <>
    <PageHeading eyebrow="THE AGGREGATION ENGINE" title="One need. Many suppliers." description="Compatible supply is grouped into a single clear offer. Suppliers still decide whether to take part." />
    {props.matches.map((match) => (
      <section className="match-card panel" key={match.id}>
        <div className="match-heading"><div><span className="panel-kicker">MATCH #{String(match.id).padStart(4, "0")}</span><h2>Supply found</h2></div><span className={`table-status ${match.status === "confirmed" ? "active-status" : "pending-status"}`}>{match.status.replaceAll("_", " ")}</span></div>
        <div className="match-summary"><strong>{match.matched_quantity.toLocaleString()} {match.unit} available</strong><span>Buyer needs {match.requested_quantity.toLocaleString()} {match.unit}</span><b>{match.coverage_percent >= 100 ? "✓ Requirement met" : "More supply may be needed"}</b></div>
        <div className="match-coverage"><div className="coverage-label"><span>Supply coverage</span><strong>{match.coverage_percent.toFixed(0)}%</strong></div><div className="coverage-track"><span style={{ width: `${Math.min(match.coverage_percent, 100)}%` }} /></div><small>{match.matched_quantity.toLocaleString()} of {match.requested_quantity.toLocaleString()} {match.unit} requested</small></div>
        <div className="table-scroll"><table><thead><tr><th>Supplier</th><th>Available material</th><th>Condition</th><th>Location</th><th>Offer</th></tr></thead><tbody>
          {match.items.map((item) => <tr key={item.listing_id}><td><span className="table-person"><i>{item.supplier_name.slice(0, 1)}</i>{item.supplier_name}{item.supplier_id === props.user.id && <small>YOU</small>}</span></td><td>{item.title}</td><td><span className="condition-tag">{item.condition}</span></td><td>{item.county || "—"}</td><td><strong>{Number(item.quantity).toLocaleString()} <small>{item.unit}</small></strong></td></tr>)}
        </tbody></table></div>
        <div className="match-footer"><div className="insight-mark">✳</div><p><strong>Matching insight</strong><span>{match.explanation || "Backend rules matched compatible materials, conditions, and locations. This explanation does not make the final transaction decision."}</span></p><button className="text-button" disabled={insightLoading === match.id} onClick={() => void loadInsight(match)}>{insightLoading === match.id ? "Loading…" : "AI insight"}</button>
          {props.user.role === "supplier" && match.status === "requested" && match.items.some((item) => item.supplier_id === props.user.id) && <div className="match-actions"><button className="button button-outline" disabled={props.busy} onClick={() => props.respond(match.id, false)}>Decline</button><button className="button button-dark" disabled={props.busy} onClick={() => props.respond(match.id, true)}>Accept invitation <span>↗</span></button></div>}
        </div>
        {insights[match.id] && <div className="ai-match-insight"><strong>{insights[match.id].compatibility} compatibility</strong><p>{insights[match.id].summary}</p><span>{insights[match.id].reasons.join(" ")}</span><small>{insights[match.id].considerations.join(" ")}</small></div>}
      </section>
    ))}
    {insightError && <div className="alert error-alert"><span>!</span>{insightError}</div>}
    {props.matches.length === 0 && <EmptyState title="No matches yet" text={props.user.role === "buyer" ? "Post a requirement to discover aggregated supply." : "When a buyer's requirement matches your listings, their offer will appear here."} />}
  </>;
}

function TransactionsPage(props: {
  user: User;
  transactions: Transaction[];
  busy: boolean;
  confirmReceipt: (id: number, quantity: number) => void;
  recordPayment: (id: number) => void;
  confirmPayment: (id: number) => void;
}) {
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  return <>
    <PageHeading eyebrow="HANDOVER & HISTORY" title="Transactions, clearly tracked." description="The platform records declared and received quantities. Payment is arranged directly between buyer and supplier." />
    <div className="payment-note"><span>ⓘ</span><p><strong>Payments are recorded, not processed by Re-Watt.</strong> Do not mark a payment as received until funds have actually cleared.</p></div>
    {props.transactions.map((transaction) => (
      <section className="transaction-card panel" key={transaction.id}>
        <div className="transaction-top"><div><span className="panel-kicker">TRANSACTION #{String(transaction.id).padStart(5, "0")}</span><h2>{transaction.material}</h2><p>{props.user.role === "buyer" ? `Supplier · ${transaction.supplier_name}` : `Buyer · ${transaction.buyer_name}`}</p></div><span className={`table-status ${transaction.status === "completed" ? "active-status" : "pending-status"}`}>{transaction.status.replaceAll("_", " ")}</span></div>
        <TransactionProgress status={transaction.status} />
        <div className="transaction-details"><div><span>Declared amount</span><strong>{transaction.quantity_declared.toLocaleString()} {transaction.unit}</strong></div><div><span>Received amount</span><strong>{transaction.quantity_received == null ? "Awaiting confirmation" : `${transaction.quantity_received.toLocaleString()} ${transaction.unit}`}</strong></div><div><span>Price per unit</span><strong>{transaction.currency} {transaction.unit_price.toLocaleString()} / {transaction.unit}</strong></div><div><span>Total (incl. platform fee)</span><strong>{transaction.currency} {transaction.total.toLocaleString()}</strong></div><div><span>Payment</span><strong>{transaction.payments.length ? `${transaction.payments[0].method.replaceAll("_", " ")} · ${transaction.payments[0].status}` : "Not recorded"}</strong></div></div>
        {props.user.role === "buyer" && transaction.quantity_received == null && <div className="transaction-actions"><label>Quantity received ({transaction.unit})<input type="number" min="0.01" step="0.01" value={quantities[transaction.id] || ""} onChange={(event) => setQuantities({ ...quantities, [transaction.id]: event.target.value })} /></label><button className="button button-dark" disabled={props.busy || !quantities[transaction.id]} onClick={() => props.confirmReceipt(transaction.id, Number(quantities[transaction.id]))}>Confirm receipt <span>↗</span></button></div>}
        {props.user.role === "buyer" && transaction.status === "payment_pending" && <div className="transaction-actions"><span className="field-help">After paying the supplier directly, record a payment reference.</span><button className="button button-dark" disabled={props.busy} onClick={() => props.recordPayment(transaction.id)}>Record payment reference</button></div>}
        {transaction.payments.filter((payment) => payment.status === "pending").map((payment) => (
          <div className="payment-row" key={payment.id}><div><strong>Payment awaiting supplier confirmation</strong><span>{payment.method.replaceAll("_", " ")}{payment.reference ? ` · Ref ${payment.reference}` : ""}</span></div>{props.user.role === "supplier" && transaction.supplier_id === props.user.id && <button className="button button-dark button-small" disabled={props.busy} onClick={() => props.confirmPayment(payment.id)}>Confirm funds received</button>}</div>
        ))}
      </section>
    ))}
    {props.transactions.length === 0 && <EmptyState title="No transactions yet" text="Accepted supplier matches will turn into transaction records here." />}
  </>;
}

function TransactionProgress({ status }: { status: string }) {
  const stages = ["Match confirmed", "Handover", "Quantity confirmed", "Payment", "Completed"];
  const normalizedStatus = status.toLowerCase();
  const activeIndex = normalizedStatus === "completed"
    ? 4
    : normalizedStatus.includes("payment")
      ? 3
      : normalizedStatus.includes("receipt") || normalizedStatus.includes("quantity")
        ? 2
        : normalizedStatus.includes("handover") || normalizedStatus.includes("deliver")
          ? 1
          : 0;
  return <div className="transaction-progress" aria-label={`Transaction progress: ${stages[activeIndex]}`}>
    {stages.map((stage, index) => <div className={index <= activeIndex ? "progress-step active" : "progress-step"} key={stage}><span>{index < activeIndex ? "✓" : index + 1}</span><small>{stage}</small></div>)}
  </div>;
}

function AdminPage(props: { users: Array<{ user_id: number; name: string; email: string; role: string; business_name?: string; county?: string }>; busy: boolean; review: (id: number, decision: "verified" | "rejected") => void }) {
  return <>
    <PageHeading eyebrow="MARKETPLACE OPERATIONS" title="Build trust, one review at a time." description="Verify business accounts before they publish supply or take part in matches." />
    <section className="panel table-panel"><div className="panel-head"><div><span className="panel-kicker">NEEDS YOUR REVIEW</span><h2>Pending business accounts <span className="heading-count">{props.users.length}</span></h2></div></div>
      {props.users.map((account) => <div className="admin-user-row" key={account.user_id}><div className="avatar">{account.name.slice(0, 1)}</div><div className="row-main"><strong>{account.business_name || account.name}</strong><span>{account.name} · {account.email} · {account.county || "County not provided"}</span></div><span className="role-tag">{account.role}</span><div className="admin-actions"><button className="button button-outline button-small" disabled={props.busy} onClick={() => props.review(account.user_id, "rejected")}>Reject</button><button className="button button-dark button-small" disabled={props.busy} onClick={() => props.review(account.user_id, "verified")}>Verify</button></div></div>)}
      {props.users.length === 0 && <EmptyState title="All caught up" text="No accounts are waiting for verification." />}
    </section>
    <div className="admin-disclaimer">Verification is an administrative trust decision. The platform does not independently verify physical stock until handover.</div>
  </>;
}

function EmptyState(props: { title: string; text: string }) {
  return <div className="empty-state"><span>✳</span><strong>{props.title}</strong><p>{props.text}</p></div>;
}

export default App;
