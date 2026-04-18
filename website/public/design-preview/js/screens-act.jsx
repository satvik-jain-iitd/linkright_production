// ACT phase: Screens 8-11 (Find roles, Resume layout plan, Live writing, Review)

function Screen08_FindRoles() {
  const rows = [
    { co: "Razorpay", role: "Senior Product Manager, Payments", loc: "Bangalore · Hybrid", score: 87, comp: "₹55–75L", tags: ["Payments", "Fintech", "Series F"] },
    { co: "Zepto", role: "Product Lead, Merchant Platform", loc: "Mumbai · Onsite", score: 82, comp: "₹60–80L", tags: ["Marketplace", "Series F"] },
    { co: "Groww", role: "Principal PM, Investing", loc: "Bangalore · Hybrid", score: 79, comp: "₹70–90L", tags: ["Wealth", "Series E"] },
    { co: "Meesho", role: "Senior PM, Seller Experience", loc: "Remote-India", score: 76, comp: "₹50–70L", tags: ["Marketplace", "Series F"] },
    { co: "Cred", role: "Product Manager, Cred Pay", loc: "Bangalore · Hybrid", score: 72, comp: "₹55–75L", tags: ["Fintech", "Payments"] },
    { co: "Rippling", role: "Senior PM, India HR Tech", loc: "Bangalore · Hybrid", score: 68, comp: "₹65–85L", tags: ["HRIS", "B2B SaaS"] },
  ];
  return (
    <div className="frame" id="s08">
      <Chrome url="linkright.in/find" />
      <div className="frame-body">
        <AppTopNav current="find" />
        <div style={{ padding: "32px 48px 56px", maxWidth: 1200, marginInline: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
            <div>
              <div className="eyebrow">Find roles</div>
              <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: "6px 0 6px" }}>20 roles matched today</h1>
              <p style={{ color: "var(--color-muted)", margin: 0, fontSize: 14 }}>Ranked by honest fit against your profile · Refreshed 8 minutes ago</p>
            </div>
            <button className="pill pill-ghost pill-sm"><Icon d={I.arrowLeft} size={12}/> Tune preferences</button>
          </div>

          {/* Spotlight */}
          <div className="card card-lg" style={{ padding: 28, borderColor: "var(--color-accent)", boxShadow: "0 12px 32px rgba(15,190,175,0.12)", background: "linear-gradient(180deg, #FFFFFF 0%, rgba(15,190,175,0.04) 100%)", marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 24 }}>
              <div style={{ flex: 1 }}>
                <span className="chip chip-teal" style={{ marginBottom: 12 }}><Icon d={I.bolt} size={12}/> Best fit today</span>
                <h2 style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.01em", margin: "10px 0 4px" }}>Senior Product Manager, Payments</h2>
                <p style={{ fontSize: 14, color: "var(--color-muted)", margin: 0 }}>Razorpay · Bangalore · Hybrid · ₹55–75L · Series F</p>

                <div style={{ marginTop: 20, display: "grid", gap: 8 }}>
                  {[
                    "Your Amex payments work is a direct match for this JD",
                    "Your 36 enterprise shipments at Sprinklr line up with their merchant scale",
                    "Hybrid in Bangalore matches your preferences",
                  ].map(r => (
                    <div key={r} style={{ display: "flex", gap: 10, fontSize: 13.5, alignItems: "flex-start" }}>
                      <span style={{ color: "var(--color-accent)", marginTop: 2 }}>✓</span>{r}
                    </div>
                  ))}
                </div>
              </div>

              {/* Score */}
              <div style={{ flex: "0 0 180px", textAlign: "center", padding: 18, background: "#fff", border: "1px solid var(--color-border)", borderRadius: 16 }}>
                <div style={{ fontSize: 11, color: "var(--color-muted)", letterSpacing: "0.14em", textTransform: "uppercase", fontWeight: 600 }}>Match</div>
                <div style={{ fontSize: 56, fontWeight: 700, color: "var(--color-accent)", letterSpacing: "-0.02em", lineHeight: 1, marginTop: 6 }}>87<span style={{ fontSize: 20 }}>%</span></div>
                <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 8 }}>3 gaps to address</div>
                <div style={{ height: 1, background: "var(--color-border)", margin: "12px 0" }}/>
                <div style={{ fontSize: 11, color: "#B3341C", fontWeight: 500, textAlign: "left" }}>
                  · No B2C payments exp.<br/>
                  · No UPI flow direct work<br/>
                  · PRD sample needed
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 20, paddingTop: 20, borderTop: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", gap: 6 }}>
                {["Payments", "Fintech", "Series F", "ESOPs", "36 other matched criteria"].map(t => <span key={t} className="chip">{t}</span>)}
              </div>
              <button className="pill pill-cta">Start custom application <Icon d={I.arrowRight} size={14}/></button>
            </div>
          </div>

          {/* List */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "12px 20px", borderBottom: "1px solid var(--color-border)", fontSize: 11, color: "var(--color-muted)", letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 600, display: "grid", gridTemplateColumns: "60px 1fr 220px 180px 180px", gap: 16 }}>
              <span>Match</span><span>Role</span><span>Company · Location</span><span>Comp</span><span></span>
            </div>
            {rows.map((r, i) => (
              <div key={i} style={{ padding: "16px 20px", borderBottom: i === rows.length - 1 ? "none" : "1px solid var(--color-border)", display: "grid", gridTemplateColumns: "60px 1fr 220px 180px 180px", gap: 16, alignItems: "center" }}>
                <span style={{ fontSize: 18, fontWeight: 700, color: r.score >= 80 ? "var(--color-accent)" : r.score >= 70 ? "#C49B09" : "var(--color-muted)" }}>{r.score}%</span>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{r.role}</div>
                  <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                    {r.tags.map(t => <span key={t} className="chip" style={{ fontSize: 10 }}>{t}</span>)}
                  </div>
                </div>
                <div style={{ fontSize: 13 }}>
                  <div style={{ fontWeight: 500 }}>{r.co}</div>
                  <div style={{ color: "var(--color-muted)", fontSize: 12 }}>{r.loc}</div>
                </div>
                <span style={{ fontSize: 13, color: "var(--color-muted)" }}>{r.comp}</span>
                <button className="pill pill-outline-teal pill-sm" style={{ justifySelf: "end" }}>Start application →</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen09_LayoutPlan() {
  return (
    <div className="frame" id="s09">
      <Chrome url="linkright.in/resume/customize?job=razorpay-spm-payments" />
      <div className="frame-body">
        <AppTopNav current="find" />
        <div style={{ padding: "24px 48px", borderBottom: "1px solid var(--color-border)", background: "#fff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="chip chip-outline">Razorpay · Senior PM, Payments</span>
            <div className="steps">
              <span className="step active">1 Layout</span><span className="sep"/>
              <span className="step">2 Writing</span><span className="sep"/>
              <span className="step">3 Review</span>
            </div>
          </div>
          <button className="pill pill-cta pill-sm">Confirm layout → Start writing</button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", minHeight: 720 }}>
          {/* Blueprint canvas */}
          <div style={{ padding: "40px 48px", background: "#F7FAFC" }}>
            <div className="eyebrow">Blueprint</div>
            <h2 style={{ fontSize: 22, fontWeight: 700, margin: "6px 0 6px", letterSpacing: "-0.01em" }}>The shape of your resume</h2>
            <p style={{ color: "var(--color-muted)", fontSize: 13, margin: "0 0 24px" }}>Drag to reorder. Drag edges to resize. Click to toggle. Must fit A4.</p>

            {/* A4 preview */}
            <div style={{ width: 560, aspectRatio: "1/1.414", background: "#fff", border: "1px solid var(--color-border)", borderRadius: 8, margin: "0 auto", padding: 20, boxShadow: "0 8px 28px rgba(0,0,0,0.06)", position: "relative", fontSize: 10, color: "#4A5568" }}>
              {/* Header block */}
              <div style={{ border: "2px dashed var(--color-accent)", borderRadius: 6, padding: 10, background: "rgba(15,190,175,0.05)", position: "relative" }}>
                <span style={{ position: "absolute", top: -9, left: 10, background: "#fff", padding: "0 6px", fontSize: 9, fontWeight: 600, color: "var(--color-accent)" }}>HEADER · 60px</span>
                <div style={{ height: 14, background: "#CBD5E0", borderRadius: 3, width: "30%" }}/>
                <div style={{ height: 6, background: "#E2E8F0", borderRadius: 3, width: "55%", marginTop: 6 }}/>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "62% 1fr", gap: 10, marginTop: 10 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {/* Summary */}
                  <div style={{ border: "1.5px dashed #CBD5E0", borderRadius: 6, padding: 8, position: "relative" }}>
                    <span style={{ position: "absolute", top: -8, left: 8, background: "#F7FAFC", padding: "0 6px", fontSize: 8, color: "var(--color-muted)" }}>SUMMARY · 3 lines</span>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, width: "70%" }}/>
                  </div>
                  {/* Experience */}
                  <div style={{ border: "2px solid var(--color-accent)", borderRadius: 6, padding: 10, background: "rgba(15,190,175,0.05)", position: "relative" }}>
                    <span style={{ position: "absolute", top: -9, left: 10, background: "#F7FAFC", padding: "0 6px", fontSize: 9, fontWeight: 600, color: "var(--color-accent)" }}>EXPERIENCE · 14 bullets · 4 roles</span>
                    {[4, 4, 3, 3].map((n, i) => (
                      <div key={i} style={{ marginTop: i === 0 ? 0 : 10 }}>
                        <div style={{ height: 6, background: "#A0AEC0", borderRadius: 3, width: "35%", marginBottom: 4 }}/>
                        {Array.from({length: n}).map((_, k) => <div key={k} style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>)}
                      </div>
                    ))}
                  </div>
                  {/* Projects */}
                  <div style={{ border: "1.5px dashed #CBD5E0", borderRadius: 6, padding: 8, position: "relative" }}>
                    <span style={{ position: "absolute", top: -8, left: 8, background: "#F7FAFC", padding: "0 6px", fontSize: 8, color: "var(--color-muted)" }}>PROJECTS · 2 · 2 bullets each</span>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {/* Education */}
                  <div style={{ border: "1.5px dashed #CBD5E0", borderRadius: 6, padding: 8, position: "relative" }}>
                    <span style={{ position: "absolute", top: -8, left: 8, background: "#F7FAFC", padding: "0 6px", fontSize: 8, color: "var(--color-muted)" }}>EDUCATION</span>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, width: "70%" }}/>
                  </div>
                  {/* Skills */}
                  <div style={{ border: "1.5px dashed #CBD5E0", borderRadius: 6, padding: 8, position: "relative" }}>
                    <span style={{ position: "absolute", top: -8, left: 8, background: "#F7FAFC", padding: "0 6px", fontSize: 8, color: "var(--color-muted)" }}>SKILLS</span>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, marginBottom: 3 }}/>
                    <div style={{ height: 4, background: "#E2E8F0", borderRadius: 2, width: "60%" }}/>
                  </div>
                  {/* Certifications */}
                  <div style={{ border: "1.5px dashed #CBD5E0", borderRadius: 6, padding: 8, position: "relative", opacity: 0.5 }}>
                    <span style={{ position: "absolute", top: -8, left: 8, background: "#F7FAFC", padding: "0 6px", fontSize: 8, color: "var(--color-muted)" }}>CERTS · off</span>
                  </div>
                </div>
              </div>

              <div style={{ position: "absolute", bottom: 8, right: 12, fontSize: 9, color: "var(--color-accent)", fontWeight: 600 }}>✓ Fits A4 · 98% filled</div>
            </div>
          </div>

          {/* Sidebar */}
          <div style={{ padding: 24, borderLeft: "1px solid var(--color-border)", background: "#fff" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 14px" }}>Sections</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                ["Header", true, "60px"],
                ["Summary", true, "3 lines"],
                ["Experience", true, "14 bullets"],
                ["Projects", true, "2 items"],
                ["Education", true, "compact"],
                ["Skills", true, "3 rows"],
                ["Certifications", false, "off"],
                ["Languages", false, "off"],
              ].map(([n, on, note]) => (
                <div key={n} className="card" style={{ padding: "10px 12px", display: "flex", justifyContent: "space-between", alignItems: "center", borderColor: on ? "rgba(15,190,175,0.3)" : undefined }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{n}</div>
                    <div style={{ fontSize: 11, color: "var(--color-muted)" }}>{note}</div>
                  </div>
                  <div style={{ width: 32, height: 18, background: on ? "var(--color-accent)" : "#E2E8F0", borderRadius: 9999, position: "relative" }}>
                    <div style={{ position: "absolute", top: 2, left: on ? 16 : 2, width: 14, height: 14, background: "#fff", borderRadius: "50%", boxShadow: "0 1px 2px rgba(0,0,0,0.1)" }} />
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 20, padding: 14, background: "rgba(15,190,175,0.06)", border: "1px solid rgba(15,190,175,0.2)", borderRadius: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#09766D" }}>Fits one page ✓</div>
              <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 4 }}>98% of the A4 page is used. Room for 1 more bullet if you add.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen10_LiveWriting() {
  const phases = [
    { n: "Layout", done: true },
    { n: "Writing", done: false, active: true, progress: 64 },
    { n: "Condensing", done: false },
    { n: "Width opt.", done: false },
    { n: "Scoring", done: false },
    { n: "Validating", done: false },
  ];
  return (
    <div className="frame" id="s10">
      <Chrome url="linkright.in/resume/customize?job=razorpay-spm-payments" />
      <div className="frame-body">
        <AppTopNav current="find" />
        <div style={{ padding: "24px 48px", borderBottom: "1px solid var(--color-border)", background: "#fff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="chip chip-outline">Razorpay · Senior PM, Payments</span>
            <div className="steps">
              <span className="step done">1 ✓</span><span className="sep"/>
              <span className="step active">2 Writing</span><span className="sep"/>
              <span className="step">3 Review</span>
            </div>
          </div>
          <span style={{ fontSize: 13, color: "var(--color-muted)" }}>Elapsed 42s · est. 90s total</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", minHeight: 720 }}>
          {/* Resume preview */}
          <div style={{ padding: "40px 48px", background: "#F7FAFC", display: "flex", justifyContent: "center" }}>
            <div style={{ width: 560, aspectRatio: "1/1.414", background: "#fff", boxShadow: "0 12px 40px rgba(0,0,0,0.08)", borderRadius: 4, padding: 36, fontSize: 10, color: "#1A202C", fontFamily: "Inter, sans-serif" }}>
              {/* Header with brand color */}
              <div style={{ borderBottom: "2px solid #0D3B66", paddingBottom: 10 }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#0D3B66", letterSpacing: "-0.015em" }}>Satvik Jain</div>
                <div style={{ fontSize: 9, color: "#4A5568", marginTop: 2 }}>Senior Product Manager · Bangalore · satvik@linkright.in · +91 98xxx xxxxx</div>
              </div>

              <div style={{ fontSize: 10, fontWeight: 700, color: "#0D3B66", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 14 }}>Summary</div>
              <p style={{ margin: "4px 0", fontSize: 9.5, lineHeight: 1.45 }}>
                Product Manager with 5 years across payments, marketplaces, and enterprise SaaS. Shipped the Amex India returns redesign (+18% conversion), led 36 enterprise deployments at Sprinklr.
              </p>

              <div style={{ fontSize: 10, fontWeight: 700, color: "#0D3B66", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 12 }}>Experience</div>

              <div style={{ marginTop: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 600 }}><span>Product Manager, American Express</span><span style={{ color: "#4A5568", fontWeight: 400 }}>Jul 2024 – Present</span></div>
                <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 9.5, lineHeight: 1.5 }}>
                  <li>Redesigned returns flow for Indian merchants, lifting completion 18% and reducing support tickets 22% within 6 weeks of rollout</li>
                  <li>Automated refund SLA engine, cutting merchant wait from 5 days to 8 hours across 14k onboarded partners</li>
                  <li>Shipped v3 merchant onboarding with KYC auto-verification — onboarding time dropped from 72h to 6h</li>
                  <li style={{ opacity: 0.3, background: "linear-gradient(90deg, #E5E7EB 50%, transparent)", borderRadius: 2, position: "relative" }}>
                    <span style={{ position: "absolute", right: 0, top: 2, fontSize: 8, color: "#8B5CF6", fontWeight: 600 }}>writing…</span>
                    &nbsp;
                  </li>
                </ul>
              </div>

              <div style={{ marginTop: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 600 }}><span>Senior PM, Sprinklr Enterprise</span><span style={{ color: "#4A5568", fontWeight: 400 }}>2021 – 2024</span></div>
                <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 9.5, lineHeight: 1.5 }}>
                  <li>Drove 36 enterprise deployments across Walmart, Samsung, Cisco — aggregate ARR of $14M</li>
                  <li>Built real-time policy engine for AI moderation, reducing moderator overhead by 34%</li>
                  <li style={{ opacity: 0.4 }}>&nbsp;</li>
                  <li style={{ opacity: 0.2 }}>&nbsp;</li>
                </ul>
              </div>

              <div style={{ marginTop: 10, opacity: 0.3 }}>
                <div style={{ background: "#E5E7EB", height: 8, borderRadius: 2, width: "40%" }}/>
                <div style={{ background: "#E5E7EB", height: 4, borderRadius: 2, width: "80%", marginTop: 4 }}/>
                <div style={{ background: "#E5E7EB", height: 4, borderRadius: 2, width: "72%", marginTop: 3 }}/>
              </div>

              <div style={{ position: "absolute", bottom: 24, right: 24, fontSize: 9, color: "#8B5CF6", fontWeight: 600, background: "rgba(139,92,246,0.08)", padding: "4px 10px", borderRadius: 9999 }}>
                <Icon d={I.sparkles} size={11} style={{ display: "inline", verticalAlign: -2 }}/> 8 of 14 bullets written
              </div>
            </div>
          </div>

          {/* Status panel */}
          <div style={{ padding: 24, borderLeft: "1px solid var(--color-border)", background: "#fff" }}>
            <div className="eyebrow" style={{ color: "#8B5CF6" }}>In progress</div>
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: "6px 0 4px" }}>Building your resume</h3>
            <p style={{ fontSize: 13, color: "var(--color-muted)", margin: "0 0 20px" }}>Scroll around — you can watch it happen.</p>

            {/* Progress bar */}
            <div style={{ height: 6, background: "#E2E8F0", borderRadius: 9999, overflow: "hidden", marginBottom: 18 }}>
              <div style={{ width: "47%", height: "100%", background: "linear-gradient(90deg, #8B5CF6 0%, #0FBEAF 100%)" }}/>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {phases.map(p => (
                <div key={p.n} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 10, background: p.active ? "rgba(139,92,246,0.08)" : "transparent" }}>
                  <div style={{ width: 18, height: 18, borderRadius: "50%", background: p.done ? "var(--color-accent)" : p.active ? "#fff" : "#EDF2F7", border: p.active ? "2px solid #8B5CF6" : "none", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 10 }}>
                    {p.done && "✓"}
                    {p.active && <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#8B5CF6" }}/>}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: p.active ? 600 : 500, color: p.done ? "var(--color-muted)" : p.active ? "#5A36AB" : "var(--color-foreground)" }}>{p.n}</div>
                    {p.active && <div style={{ fontSize: 11, color: "var(--color-muted)" }}>Bullet 8 of 14 · {p.progress}%</div>}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 24, padding: 14, background: "#FDF6F0", border: "1px solid #F8E6D4", borderRadius: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#8A6E53" }}>Brand match: Razorpay</div>
              <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                {["#0D3B66", "#528AAE", "#E0E5EC"].map(c => <div key={c} style={{ width: 22, height: 22, borderRadius: 6, background: c, border: "1px solid rgba(0,0,0,0.05)" }}/>)}
              </div>
              <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 8 }}>Applied to header + section titles · WCAG AA passed.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen11_Review() {
  return (
    <div className="frame" id="s11">
      <Chrome url="linkright.in/resume/customize?job=razorpay-spm-payments" />
      <div className="frame-body">
        <AppTopNav current="find" />
        <div style={{ padding: "24px 48px", borderBottom: "1px solid var(--color-border)", background: "#fff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="chip chip-teal">✓ Done in 87 seconds</span>
            <span className="chip chip-outline">Razorpay · Senior PM, Payments</span>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="pill pill-ghost pill-sm"><Icon d={I.document} size={14}/> Download PDF</button>
            <button className="pill pill-ghost pill-sm">Download HTML</button>
            <button className="pill pill-teal pill-sm"><Icon d={I.github} size={14}/> Host on GitHub Pages</button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", minHeight: 720 }}>
          {/* Final resume preview */}
          <div style={{ padding: "40px 48px", background: "#F7FAFC", display: "flex", justifyContent: "center" }}>
            <div style={{ width: 560, aspectRatio: "1/1.414", background: "#fff", boxShadow: "0 12px 40px rgba(0,0,0,0.1)", borderRadius: 4, padding: 36, fontSize: 10, color: "#1A202C", position: "relative" }}>
              <div style={{ borderBottom: "2px solid #0D3B66", paddingBottom: 10 }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#0D3B66", letterSpacing: "-0.015em" }}>Satvik Jain</div>
                <div style={{ fontSize: 9, color: "#4A5568", marginTop: 2 }}>Senior Product Manager · Bangalore · satvik@linkright.in · +91 98xxx xxxxx</div>
              </div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#0D3B66", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 14 }}>Summary</div>
              <p style={{ margin: "4px 0", fontSize: 9.5, lineHeight: 1.45 }}>Product Manager with 5 years across payments, marketplaces, and enterprise SaaS. Shipped the Amex India returns redesign (+18% conversion), led 36 enterprise deployments at Sprinklr managing $14M ARR.</p>

              <div style={{ fontSize: 10, fontWeight: 700, color: "#0D3B66", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 12 }}>Experience</div>
              <div style={{ marginTop: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 600 }}><span>Product Manager, American Express</span><span style={{ color: "#4A5568", fontWeight: 400 }}>Jul 2024 – Present</span></div>
                <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 9.5, lineHeight: 1.5 }}>
                  <li>Redesigned returns flow for 14,200 Indian merchants, lifting completion 18% and cutting tickets 22% within 6 weeks</li>
                  <li>Automated refund SLA engine — merchant wait dropped from 5 days to 8 hours across all onboarded partners</li>
                  <li style={{ background: "rgba(15,190,175,0.12)", outline: "2px solid var(--color-accent)", outlineOffset: 2, borderRadius: 2 }}>Shipped v3 merchant onboarding with KYC auto-verify — onboarding time dropped 72h to 6h, NPS 34 → 58</li>
                  <li>Ran discovery for UPI-Amex rails partnership — signed term sheet with 3 bank partners</li>
                </ul>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, fontWeight: 600 }}><span>Senior PM, Sprinklr Enterprise</span><span style={{ color: "#4A5568", fontWeight: 400 }}>2021 – 2024</span></div>
                <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 9.5, lineHeight: 1.5 }}>
                  <li>Drove 36 enterprise deployments across Walmart, Samsung, Cisco — aggregate ARR of $14M by close of 2023</li>
                  <li>Built real-time policy engine for AI moderation — cut moderator overhead 34%, adopted by 8 global brands</li>
                  <li>Led Walmart legal escalation rebuild after 3-week embed — SLA compliance rose from 76% to 94%</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Refine + What's next */}
          <div style={{ padding: 24, borderLeft: "1px solid var(--color-border)", background: "#fff", display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Refine bullet */}
            <div>
              <div className="eyebrow">Refine highlighted bullet</div>
              <p style={{ fontSize: 12, color: "var(--color-muted)", margin: "6px 0 12px" }}>"Shipped v3 merchant onboarding…"</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {["Shorter", "More metrics", "Different verb", "More impact-first"].map(t => <span key={t} className="chip chip-outline" style={{ cursor: "default" }}>{t}</span>)}
              </div>
              <textarea disabled placeholder="Or type a custom instruction…" style={{ width: "100%", marginTop: 10, padding: 10, border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 12, fontFamily: "inherit", resize: "none", height: 56 }}/>
            </div>

            <div style={{ height: 1, background: "var(--color-border)" }}/>

            {/* What's next */}
            <div>
              <div className="eyebrow">What's next</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
                <button className="card" style={{ padding: 14, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, border: "1px solid var(--color-border)", background: "#fff", cursor: "default", textAlign: "left" }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div className="iconTile iconTile-sage" style={{ width: 32, height: 32 }}><Icon d={I.chat} size={16}/></div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Interview prep for this role</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)" }}>Product sense drills, tailored</div>
                    </div>
                  </div>
                  <Icon d={I.arrowRight} size={14} style={{ color: "var(--color-muted)" }}/>
                </button>
                <button className="card" style={{ padding: 14, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, border: "1px solid var(--color-border)", background: "#fff", cursor: "default", textAlign: "left" }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div className="iconTile" style={{ width: 32, height: 32 }}><Icon d={I.search} size={16}/></div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Find more roles</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)" }}>19 more matches today</div>
                    </div>
                  </div>
                  <Icon d={I.arrowRight} size={14} style={{ color: "var(--color-muted)" }}/>
                </button>
                <button className="card" style={{ padding: 14, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, border: "1px solid var(--color-border)", background: "#fff", cursor: "default", textAlign: "left", opacity: 0.55 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div className="iconTile iconTile-coral" style={{ width: 32, height: 32 }}><Icon d={I.document} size={16}/></div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Cover letter</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)" }}>Personalised for Razorpay</div>
                    </div>
                  </div>
                  <span className="chip chip-gold">Soon</span>
                </button>
                <button className="card" style={{ padding: 14, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, border: "1px solid var(--color-border)", background: "#fff", cursor: "default", textAlign: "left", opacity: 0.55 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div className="iconTile iconTile-gold" style={{ width: 32, height: 32 }}><Icon d={I.globe} size={16}/></div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Portfolio site</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)" }}>One page · hosted for you</div>
                    </div>
                  </div>
                  <span className="chip chip-gold">Soon</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Screen08_FindRoles, Screen09_LayoutPlan, Screen10_LiveWriting, Screen11_Review });
