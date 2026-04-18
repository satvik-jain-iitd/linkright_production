// ENTER phase: Screens 1-3 (Landing, Pricing, Auth)

function Screen01_Landing() {
  return (
    <div className="frame" id="s01">
      <Chrome url="linkright.in" />
      <div className="frame-body">
        {/* Landing nav */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 48px", background: "rgba(250,251,252,0.8)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--color-border)" }}>
          <Wordmark size={20} />
          <div style={{ display: "flex", alignItems: "center", gap: 28, fontSize: 14 }}>
            <a style={{ color: "var(--color-muted)", textDecoration: "none" }}>How it works</a>
            <a style={{ color: "var(--color-muted)", textDecoration: "none" }}>Pricing</a>
            <a style={{ color: "var(--color-muted)", textDecoration: "none" }}>Sign in</a>
            <button className="pill pill-cta pill-sm">Start for free</button>
          </div>
        </div>

        {/* Hero */}
        <div style={{ position: "relative", padding: "96px 48px 80px", textAlign: "center", background: "radial-gradient(ellipse at center, rgba(15,190,175,0.08) 0%, transparent 70%)" }}>
          <div className="eyebrow" style={{ marginBottom: 20 }}>Career OS · built for India · PM · SWE · DA</div>
          <h1 style={{ fontSize: 64, fontWeight: 700, letterSpacing: "-0.025em", lineHeight: 1.02, margin: 0, maxWidth: 880, marginInline: "auto" }}>
            Job hunting,<br/>but your profile gets <span style={{ color: "var(--color-accent)" }}>sharper</span> every week.
          </h1>
          <p style={{ fontSize: 18, color: "var(--color-muted)", maxWidth: 620, margin: "28px auto 0", lineHeight: 1.55 }}>
            Upload your resume once. LinkRight builds a profile that learns what you're good at — then makes every application, every post, every interview prep sharper.
          </p>
          <div style={{ display: "flex", gap: 14, justifyContent: "center", marginTop: 36 }}>
            <button className="pill pill-cta pill-lg">Start for free <Icon d={I.arrowRight} size={16}/></button>
            <button className="pill pill-ghost pill-lg">See how it works</button>
          </div>
          <p style={{ fontSize: 13, color: "var(--color-muted)", marginTop: 18 }}>First resume free · No credit card · Takes 90 seconds</p>
        </div>

        {/* Proof tiles — 4 pillars (without the internal names) */}
        <div style={{ padding: "16px 48px 80px", maxWidth: 1080, marginInline: "auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20 }}>
            {[
              { c: "purple", icon: I.sparkles, t: "A profile that remembers you", d: "Every achievement, every project, every learning. It grows with you." },
              { c: "teal", icon: I.search, t: "Honest match scores", d: "Top 20 roles for you today. If it's 62%, we say 62% — and the 3 gaps." },
              { c: "coral", icon: I.document, t: "One click, five artefacts", d: "Resume, cover letter, LinkedIn DM, recruiter email, portfolio — tailored." },
              { c: "pink", icon: I.chat, t: "Posts in your voice", d: "Drafted from your real wins and diary — not ChatGPT slop." },
            ].map(t => (
              <div key={t.t} className="card" style={{ padding: 22 }}>
                <div className={`iconTile iconTile-${t.c}`}><Icon d={t.icon} /></div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: "14px 0 6px", letterSpacing: "-0.01em" }}>{t.t}</h3>
                <p style={{ fontSize: 13, color: "var(--color-muted)", margin: 0, lineHeight: 1.55 }}>{t.d}</p>
              </div>
            ))}
          </div>
        </div>

        {/* How it works */}
        <div style={{ padding: "48px 48px 96px", borderTop: "1px solid var(--color-border)", background: "#fff" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <div className="eyebrow">How it works</div>
            <h2 style={{ fontSize: 36, fontWeight: 700, letterSpacing: "-0.015em", margin: "10px 0 0" }}>Three steps. One daily ritual.</h2>
          </div>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "center", gap: 16, maxWidth: 1000, marginInline: "auto" }}>
            {[
              ["01", "Drop your resume", "We parse it, show you what we understood, and start your profile."],
              ["02", "Pick a role", "Honest match scores. We tell you why it's a fit and where the gaps are."],
              ["03", "Ship the application", "Resume, cover letter, LinkedIn DM, recruiter email — all tailored."],
            ].map(([n, t, d], i, a) => (
              <React.Fragment key={n}>
                <div style={{ flex: 1, textAlign: "center" }}>
                  <div style={{ width: 44, height: 44, borderRadius: "50%", background: "var(--color-accent)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 14, margin: "0 auto 14px" }}>{n}</div>
                  <h3 style={{ fontSize: 17, fontWeight: 600, margin: "0 0 6px" }}>{t}</h3>
                  <p style={{ fontSize: 13, color: "var(--color-muted)", margin: 0, lineHeight: 1.55 }}>{d}</p>
                </div>
                {i < a.length - 1 && <div style={{ flex: "0 0 50px", marginTop: 18, color: "var(--color-muted)", textAlign: "center" }}>→</div>}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: "32px 48px", borderTop: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13, color: "var(--color-muted)" }}>
          <Wordmark size={15} />
          <span>Made in India 🇮🇳</span>
        </div>
      </div>
    </div>
  );
}

function Screen02_Pricing() {
  const plans = [
    { name: "Free", price: "₹0", sub: "Forever free", features: ["3 tailored resumes / month", "Profile that learns from every resume", "Top 20 role matches", "Basic interview drills"], cta: "Start free", variant: "ghost" },
    { name: "Pro", price: "₹499", sub: "per month", badge: "Recommended", features: ["Everything in Free", "Unlimited tailored resumes", "5-artefact apply pack (cover letter, DMs, email, portfolio)", "Oracle interview coach", "Brand-color matching", "Broadcast — LinkedIn scheduling"], cta: "Upgrade to Pro", variant: "cta" },
  ];
  return (
    <div className="frame" id="s02">
      <Chrome url="linkright.in/pricing" />
      <div className="frame-body">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 48px", borderBottom: "1px solid var(--color-border)", background: "#fff" }}>
          <Wordmark size={20} />
          <button className="pill pill-cta pill-sm">Start for free</button>
        </div>
        <div style={{ padding: "72px 48px", maxWidth: 1080, marginInline: "auto", textAlign: "center" }}>
          <div className="eyebrow">Pricing</div>
          <h2 style={{ fontSize: 44, fontWeight: 700, letterSpacing: "-0.02em", margin: "10px 0 14px" }}>Start free. Upgrade when you ship.</h2>
          <p style={{ color: "var(--color-muted)", fontSize: 16, margin: 0 }}>One plan handles the whole hunt. No seat fees. No upsells mid-flow.</p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 56, textAlign: "left" }}>
            {plans.map(p => (
              <div key={p.name} className="card card-lg" style={{ padding: 32, borderColor: p.variant === "cta" ? "var(--color-accent)" : undefined, boxShadow: p.variant === "cta" ? "0 12px 32px rgba(15,190,175,0.12)" : undefined, position: "relative" }}>
                {p.badge && <span className="chip chip-teal" style={{ position: "absolute", top: 24, right: 24 }}>{p.badge}</span>}
                <h3 style={{ fontSize: 20, fontWeight: 700, margin: 0, letterSpacing: "-0.01em" }}>{p.name}</h3>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 12 }}>
                  <span style={{ fontSize: 48, fontWeight: 700, letterSpacing: "-0.02em" }}>{p.price}</span>
                  <span style={{ color: "var(--color-muted)", fontSize: 14 }}>{p.sub}</span>
                </div>
                <div style={{ marginTop: 24, borderTop: "1px solid var(--color-border)", paddingTop: 20 }}>
                  {p.features.map(f => (
                    <div key={f} style={{ display: "flex", gap: 10, alignItems: "flex-start", fontSize: 14, marginBottom: 12, color: "var(--color-foreground)" }}>
                      <span style={{ color: "var(--color-accent)", marginTop: 2 }}>✓</span>
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
                <button className={`pill pill-${p.variant === "cta" ? "cta" : "ghost"}`} style={{ marginTop: 24, width: "100%" }}>{p.cta}</button>
              </div>
            ))}
          </div>

          <p style={{ marginTop: 48, fontSize: 13, color: "var(--color-muted)" }}>Broadcast is in early access · Coming to Pro in May 2026</p>
        </div>
      </div>
    </div>
  );
}

function Screen03_Auth() {
  return (
    <div className="frame" id="s03">
      <Chrome url="linkright.in/auth" />
      <div className="frame-body" style={{ minHeight: 720, display: "flex" }}>
        {/* Left — warm side panel, reinforces promise */}
        <div style={{ flex: "0 0 44%", background: "linear-gradient(180deg, #FDF6F0 0%, #F8E6D4 100%)", padding: "56px 48px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <Wordmark size={20} />
          <div>
            <h2 style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.2, margin: 0, maxWidth: 360 }}>
              Your career, remembered.
            </h2>
            <p style={{ color: "#5F4632", fontSize: 15, lineHeight: 1.6, marginTop: 16, maxWidth: 360 }}>
              Upload a resume once. We read it, understand it, and keep it ready — for every role you ever apply to.
            </p>
            <div style={{ marginTop: 32, display: "flex", flexDirection: "column", gap: 10 }}>
              {["Top 20 matching roles refreshed daily", "Five artefacts per application, one click", "Posts drafted from your real wins"].map(t => (
                <div key={t} style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 13, color: "#5F4632" }}>
                  <span style={{ color: "var(--color-accent)" }}>✓</span>{t}
                </div>
              ))}
            </div>
          </div>
          <p style={{ fontSize: 12, color: "#8A6E53", margin: 0 }}>Made in India 🇮🇳 · Built by someone who ships</p>
        </div>

        {/* Right — auth form */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 48 }}>
          <div style={{ width: "100%", maxWidth: 380 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: 0 }}>Create your account</h1>
            <p style={{ color: "var(--color-muted)", margin: "8px 0 32px", fontSize: 14 }}>Your first resume is free. No credit card.</p>

            <button style={{ width: "100%", padding: "12px 16px", border: "1px solid var(--color-border)", background: "#fff", borderRadius: 9999, fontSize: 14, fontWeight: 600, cursor: "default", display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
              <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              Continue with Google
            </button>

            <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "24px 0", color: "var(--color-muted)", fontSize: 11, letterSpacing: "0.12em" }}>
              <div style={{ flex: 1, height: 1, background: "var(--color-border)" }}/><span>OR</span><div style={{ flex: 1, height: 1, background: "var(--color-border)" }}/>
            </div>

            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--color-foreground)" }}>Email</label>
            <input disabled placeholder="you@example.com" style={{ width: "100%", padding: "11px 14px", marginTop: 6, border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 14, fontFamily: "inherit", background: "#fff" }} />

            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--color-foreground)", marginTop: 16, display: "block" }}>Password</label>
            <input disabled type="password" placeholder="••••••••" style={{ width: "100%", padding: "11px 14px", marginTop: 6, border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 14, fontFamily: "inherit", background: "#fff" }} />

            <button className="pill pill-cta" style={{ width: "100%", marginTop: 20 }}>Create account</button>
            <p style={{ fontSize: 12, color: "var(--color-muted)", textAlign: "center", marginTop: 18 }}>Already have an account? <a style={{ color: "var(--color-accent)", fontWeight: 500 }}>Sign in</a></p>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Screen01_Landing, Screen02_Pricing, Screen03_Auth });
