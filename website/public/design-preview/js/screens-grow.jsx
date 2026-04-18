// GROW phase: Screens 12-21 (Dashboard, Interview prep, Apps tracker, Broadcast x4, Diary, Profile, Notifications)

function Screen12_Dashboard() {
  return (
    <div className="frame" id="s12">
      <Chrome url="linkright.in/dashboard" />
      <div className="frame-body">
        <AppTopNav current="dashboard" />
        <div style={{ padding: "32px 48px 56px", maxWidth: 1200, marginInline: "auto" }}>
          {/* Welcome */}
          <div style={{ marginBottom: 28 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: 0 }}>Good morning, Satvik.</h1>
            <p style={{ color: "var(--color-muted)", margin: "6px 0 0", fontSize: 14 }}>5 new matches since Tuesday.</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24 }}>
            {/* Main column */}
            <div>
              {/* Today's pipeline: matches + in-progress applications, unified */}
              <div style={{ marginBottom: 28 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 14 }}>
                  <div>
                    <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>Today's pipeline</h2>
                    <p style={{ fontSize: 12.5, color: "var(--color-muted)", margin: "4px 0 0" }}>Work you've started · roles matched this morning · applications that moved</p>
                  </div>
                  <div style={{ display: "flex", gap: 14, alignItems: "center", fontSize: 12.5 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--color-muted)" }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#C49B09" }}/> In progress
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--color-muted)" }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-accent)" }}/> New
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--color-muted)" }}>
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#64748B" }}/> Sent
                    </span>
                    <a style={{ fontSize: 13, color: "var(--color-accent)", fontWeight: 500, marginLeft: 4 }}>Open pipeline →</a>
                  </div>
                </div>

                <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                  <div style={{ padding: "10px 18px", borderBottom: "1px solid var(--color-border)", fontSize: 10.5, color: "var(--color-muted)", letterSpacing: "0.12em", textTransform: "uppercase", fontWeight: 600, display: "grid", gridTemplateColumns: "52px 1.4fr 1fr 200px 150px", gap: 14 }}>
                    <span>Match</span><span>Role</span><span>Company · Location</span><span>Status</span><span style={{ textAlign: "right" }}>Action</span>
                  </div>
                  {[
                    { score: 74, role: "Product Manager, Cred Pay", co: "Cred", loc: "Bangalore", statusKind: "progress", statusText: "Resume draft · 72% done", statusNote: "Last touched 2h ago", action: { kind: "primary", label: "Resume" }, accent: "#C49B09" },
                    { score: 91, role: "Senior PM, Merchant Payments", co: "Phonepe", loc: "Bangalore", statusKind: "progress", statusText: "Layout plan · step 2 of 3", statusNote: "Paused yesterday · resume any time", action: { kind: "primary", label: "Resume" }, accent: "#C49B09" },
                    { score: 87, role: "Senior PM, Payments", co: "Razorpay", loc: "Bangalore · Hybrid", statusKind: "new", statusText: "New match · today", statusNote: "3 evidence links", action: { kind: "teal", label: "Start" }, accent: "var(--color-accent)" },
                    { score: 82, role: "Product Lead, Merchant", co: "Zepto", loc: "Mumbai", statusKind: "new", statusText: "New match · today", statusNote: "Matches your ops scale work", action: { kind: "teal", label: "Start" }, accent: "var(--color-accent)" },
                    { score: 79, role: "Principal PM, Investing", co: "Groww", loc: "Bangalore", statusKind: "new", statusText: "New match · today", statusNote: "1 gap: consumer investing experience", action: { kind: "teal", label: "Start" }, accent: "#C49B09" },
                    { score: 84, role: "Senior PM, Risk", co: "Cashfree", loc: "Bangalore", statusKind: "sent", statusText: "Applied · Apr 14", statusNote: "Awaiting recruiter reply · 3 days", action: { kind: "ghost", label: "View" }, accent: "#64748B" },
                  ].map((r, i, arr) => (
                    <div key={i} style={{ padding: "14px 18px", borderBottom: i === arr.length - 1 ? "none" : "1px solid var(--color-border)", display: "grid", gridTemplateColumns: "52px 1.4fr 1fr 200px 150px", gap: 14, alignItems: "center", background: r.statusKind === "progress" ? "rgba(196,155,9,0.035)" : "transparent" }}>
                      <span style={{ fontSize: 15, fontWeight: 700, color: r.score >= 85 ? "var(--color-accent)" : r.score >= 75 ? "#C49B09" : "var(--color-muted)" }}>{r.score}%</span>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.role}</div>
                      </div>
                      <div style={{ fontSize: 12.5, minWidth: 0 }}>
                        <div style={{ fontWeight: 500 }}>{r.co}</div>
                        <div style={{ color: "var(--color-muted)", fontSize: 11.5 }}>{r.loc}</div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: r.statusKind === "progress" ? "#C49B09" : r.statusKind === "new" ? "var(--color-accent)" : "#64748B", flexShrink: 0 }}/>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: 12.5, fontWeight: 500, color: r.statusKind === "progress" ? "#8A6E1E" : r.statusKind === "new" ? "#09766D" : "#475569" }}>{r.statusText}</div>
                          <div style={{ fontSize: 11, color: "var(--color-muted)" }}>{r.statusNote}</div>
                        </div>
                      </div>
                      <div style={{ justifySelf: "end" }}>
                        {r.action.kind === "primary" && <button className="pill pill-sm" style={{ background: "#C49B09", color: "#fff", border: "none" }}>{r.action.label} <Icon d={I.arrowRight} size={12}/></button>}
                        {r.action.kind === "teal" && <button className="pill pill-outline-teal pill-sm">{r.action.label} <Icon d={I.arrowRight} size={12}/></button>}
                        {r.action.kind === "ghost" && <button className="pill pill-ghost pill-sm">{r.action.label}</button>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Keep going — interview prep focus */}
              <div style={{ marginBottom: 28 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                  <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>Keep going. Interview prep.</h2>
                  <a style={{ fontSize: 13, color: "#4A5D32", fontWeight: 500 }}>Open all drills</a>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div className="card" style={{ padding: 16, display: "flex", alignItems: "center", gap: 14, borderColor: "rgba(107,131,70,0.3)", background: "rgba(107,131,70,0.04)" }}>
                    <div className="iconTile iconTile-sage"><Icon d={I.chat}/></div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>5 behavioural drills for Razorpay</div>
                      <div style={{ fontSize: 12, color: "var(--color-muted)" }}>15 minutes. Based on their past interview questions.</div>
                    </div>
                    <button className="pill pill-sm" style={{ background: "#6B8346", color: "#fff", border: "none" }}>Resume drill</button>
                  </div>
                  <div className="card" style={{ padding: 16, display: "flex", alignItems: "center", gap: 14 }}>
                    <div className="iconTile iconTile-sage"><Icon d={I.bolt}/></div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>Product-sense warmup · 8 questions</div>
                      <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Tailored to your Amex payments work. 12 minutes.</div>
                    </div>
                    <button className="pill pill-ghost pill-sm">Start</button>
                  </div>
                  <div className="card" style={{ padding: 16, display: "flex", alignItems: "center", gap: 14 }}>
                    <div className="iconTile iconTile-sage"><Icon d={I.mic}/></div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>Record a "Tell me about yourself" take</div>
                      <div style={{ fontSize: 12, color: "var(--color-muted)" }}>3 previous takes. Last feedback: trim the Sprinklr arc by 20s.</div>
                    </div>
                    <button className="pill pill-ghost pill-sm">Record</button>
                  </div>
                </div>
              </div>

              {/* Broadcast pulse */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                  <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>Broadcast pulse</h2>
                  <a style={{ fontSize: 13, color: "#B13355", fontWeight: 500 }}>Open Broadcast</a>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 12 }}>
                  {/* Last post performance */}
                  <div className="card" style={{ padding: 18, borderColor: "rgba(240,90,121,0.2)", background: "linear-gradient(180deg, rgba(240,90,121,0.04) 0%, #fff 55%)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                      <span className="pillar-tag pillar-broadcast" style={{ fontSize: 10 }}><span className="dot"/>Posted Apr 12</span>
                    </div>
                    <div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.35, marginBottom: 10 }}>Refund SLA automation shipped: 5 days to 8 hours</div>
                    <div style={{ display: "flex", gap: 18, fontSize: 11, color: "var(--color-muted)" }}>
                      <span><b style={{ color: "#B13355", fontSize: 15, fontWeight: 700 }}>142</b> reactions</span>
                      <span><b style={{ color: "#B13355", fontSize: 15, fontWeight: 700 }}>31</b> comments</span>
                      <span><b style={{ color: "#B13355", fontSize: 15, fontWeight: 700 }}>12</b> reposts</span>
                    </div>
                    <div style={{ marginTop: 10, padding: "8px 10px", background: "rgba(240,90,121,0.06)", borderRadius: 8, fontSize: 11.5, color: "#5B3140", lineHeight: 1.5 }}>
                      <b>3 PMs from Razorpay</b> engaged. Warm intro surface ready.
                    </div>
                  </div>

                  {/* Scheduled + draft ready */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div className="card" style={{ padding: 14 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--color-muted)", fontWeight: 500, marginBottom: 6 }}>
                        <Icon d={I.calendar} size={12}/> Tomorrow · 9:30 AM
                      </div>
                      <div style={{ fontSize: 12.5, fontWeight: 600, lineHeight: 1.4 }}>The reason-code drop-off insight</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 4 }}>Scheduled · review before post</div>
                    </div>
                    <div className="card" style={{ padding: 14, borderColor: "rgba(240,90,121,0.35)", background: "rgba(240,90,121,0.04)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#B13355", fontWeight: 600, marginBottom: 6 }}>
                        <Icon d={I.sparkles} size={12}/> Draft from Tuesday's diary
                      </div>
                      <div style={{ fontSize: 12.5, lineHeight: 1.4 }}>"Refund SLA shipped, 5 days → 8 hours…"</div>
                      <button className="pill pill-sm" style={{ marginTop: 10, background: "#F05A79", color: "#fff", border: "none", width: "100%" }}>Review &amp; schedule</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right column. Profile card */}
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div className="card card-lg" style={{ padding: 24, background: "linear-gradient(180deg, rgba(139,92,246,0.06) 0%, #FFFFFF 100%)" }}>
                <div className="eyebrow" style={{ color: "#8B5CF6" }}>Your profile</div>
                <h3 style={{ fontSize: 18, fontWeight: 700, margin: "6px 0 12px", letterSpacing: "-0.01em" }}>Still growing.</h3>

                <div style={{ marginTop: 6 }}>
                  <div style={{ fontSize: 36, fontWeight: 700, color: "#5A36AB", letterSpacing: "-0.02em" }}>47</div>
                  <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>highlights captured.</div>
                </div>

                <button className="pill pill-sm" style={{ marginTop: 18, width: "100%", background: "#8B5CF6", color: "#fff", border: "none" }}>Add more to your profile</button>
              </div>

              {/* Diary quick-log */}
              <div className="card card-lg" style={{ padding: 20, flex: 1, display: "flex", flexDirection: "column", minHeight: 280 }}>
                <div className="eyebrow" style={{ marginBottom: 12, color: "#5A36AB" }}>Daily diary</div>
                <textarea disabled placeholder="What did you ship today?" style={{ width: "100%", padding: 12, border: "1px solid rgba(139,92,246,0.25)", borderRadius: 10, fontSize: 13, fontFamily: "inherit", resize: "none", flex: 1, background: "#FAF8FF" }}/>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
                  <button className="pill pill-ghost pill-sm"><Icon d={I.mic} size={12}/> Record instead</button>
                  <button className="pill pill-sm" style={{ background: "#8B5CF6", color: "#fff", border: "none" }}>Log</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen13_InterviewPrep() {
  const cards = [
    { c: "sage", title: "Telephonic screen", d: "The 20-minute recruiter call, practiced.", n: "6 drills queued" },
    { c: "sage", title: "SQL", d: "Window functions, joins, query optimisation.", n: "7 drills queued" },
    { c: "sage", title: "Case", d: "Consulting-style market-size and profitability cases.", n: "6 drills queued" },
    { c: "sage", title: "Product sense", d: "Frame, prioritise, design. Tailored to your target roles.", n: "8 drills queued" },
    { c: "sage", title: "Growth", d: "Funnel diagnosis, experiment design, activation work.", n: "4 drills queued" },
    { c: "sage", title: "System design", d: "Whiteboard walkthroughs with real-time critique.", n: "5 drills queued" },
    { c: "sage", title: "Technical / coding", d: "Mid-level DSA + API design, at your level.", n: "10 drills queued" },
    { c: "sage", title: "Behavioural", d: "Your stories, sharpened. Pulled from your diary + resume.", n: "12 drills queued" },
  ];
  return (
    <div className="frame" id="s13">
      <Chrome url="linkright.in/prepare" />
      <div className="frame-body">
        <AppTopNav current="prepare" />
        <div style={{ padding: "40px 48px 64px", maxWidth: 1100, marginInline: "auto" }}>
          <div style={{ marginBottom: 28, maxWidth: 680 }}>
            <div className="eyebrow" style={{ color: "#4A5D32" }}>Interview prep</div>
            <h1 style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.015em", margin: "8px 0 8px" }}>What are you practicing today?</h1>
            <p style={{ color: "var(--color-muted)", fontSize: 15, margin: 0 }}>Pick what's thin. Drills tailor to your profile and target roles.</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
            {cards.map(c => (
              <div key={c.title} className="card" style={{ padding: 18, background: "#F3F6EA", borderColor: "rgba(107,131,70,0.2)" }}>
                <div className="iconTile iconTile-sage" style={{ background: "rgba(107,131,70,0.14)" }}><Icon d={I.chat}/></div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: "12px 0 6px", color: "#2E3B1E" }}>{c.title}</h3>
                <p style={{ fontSize: 12.5, color: "#4A5D32", margin: 0, lineHeight: 1.5 }}>{c.d}</p>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, paddingTop: 12, borderTop: "1px dashed rgba(107,131,70,0.3)" }}>
                  <span style={{ fontSize: 11, color: "#4A5D32" }}>{c.n}</span>
                  <button style={{ fontSize: 12, fontWeight: 600, color: "#4A5D32", background: "transparent", border: "none", cursor: "default" }}>Start</button>
                </div>
              </div>
            ))}
          </div>

          {/* Coming soon. AI panel roundtable */}
          <div style={{ marginTop: 28, padding: 24, background: "#F8FAFC", border: "1px dashed #CBD5E0", borderRadius: 16, display: "flex", alignItems: "center", gap: 18, opacity: 0.85 }}>
            <div className="iconTile" style={{ width: 56, height: 56, borderRadius: 14, background: "#EDF2F7", color: "#94A3B8" }}><Icon d={I.chat} size={26}/></div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: "#64748B" }}>Multi-persona recruiter roundtable</h3>
                <span className="chip chip-soon">Soon</span>
              </div>
              <p style={{ fontSize: 13, color: "var(--color-muted)", margin: "4px 0 0" }}>Three personas (hiring manager, recruiter, cross-functional partner) grill you in parallel. Feedback from each angle in one session.</p>
            </div>
            <button className="pill pill-ghost pill-sm" disabled>Notify me</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen14_Applications() {
  const cols = [
    { name: "Wishlist", n: 6, color: "#CBD5E0", items: [
      { co: "Stripe", role: "Senior PM, Growth", date: "added 2 days ago", tag: "Interested" },
      { co: "Linear", role: "PM, Platform", date: "added 5 days ago", tag: "Researching" },
    ]},
    { name: "Drafting", n: 3, color: "#8B5CF6", items: [
      { co: "Cred", role: "PM, Cred Pay", date: "72% complete", tag: "Resume", tagC: "purple" },
      { co: "Groww", role: "Principal PM", date: "Layout set", tag: "Resume", tagC: "purple" },
    ]},
    { name: "Applied", n: 8, color: "#0FBEAF", items: [
      { co: "Razorpay", role: "Senior PM, Payments", date: "Applied Apr 14", tag: "3 days ago" },
      { co: "Zepto", role: "Product Lead", date: "Applied Apr 12", tag: "5 days ago" },
      { co: "Meesho", role: "Senior PM", date: "Applied Apr 10", tag: "7 days ago" },
    ]},
    { name: "Interview", n: 2, color: "#6B8346", items: [
      { co: "PhonePe", role: "Senior PM, Lending", date: "Round 2 on Apr 22", tag: "Prep 3 drills", tagC: "sage" },
    ]},
    { name: "Offer", n: 1, color: "#E5B80B", items: [
      { co: "Swiggy", role: "PM, Instamart", date: "Offered ₹68L", tag: "Decide by Apr 26", tagC: "gold" },
    ]},
    { name: "Rejected", n: 4, color: "#94A3B8", items: [
      { co: "Cure.fit", role: "PM, Fitness", date: "Rejected Apr 8", tag: "+ log outcome", tagC: "outline" },
    ]},
  ];
  return (
    <div className="frame" id="s14">
      <Chrome url="linkright.in/apply/pipeline" />
      <div className="frame-body">
        <AppTopNav current="apply" />
        <div style={{ padding: "28px 32px 56px", maxWidth: "100%", overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24, padding: "0 16px" }}>
            <div>
              <div className="eyebrow">Search &amp; apply</div>
              <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.015em", margin: "6px 0 0" }}>Applications pipeline</h1>
              <p style={{ color: "var(--color-muted)", margin: "4px 0 0", fontSize: 14 }}><b style={{ color: "var(--color-foreground)", fontWeight: 700 }}>24</b> active · avg. <b style={{ color: "var(--color-foreground)", fontWeight: 700 }}>3.2 days</b> to first response</p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="pill pill-ghost pill-sm"><Icon d={I.chartBar} size={14}/> Analytics</button>
              <button className="pill pill-cta pill-sm"><Icon d={I.plus} size={14}/> Add application</button>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(190px, 1fr))", gap: 10, padding: "0 16px" }}>
            {cols.map(col => (
              <div key={col.name}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 4px", marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: col.color }}/>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{col.name}</span>
                    <span style={{ fontSize: 11, color: "var(--color-muted)" }}>{col.n}</span>
                  </div>
                  <Icon d={I.plus} size={14} style={{ color: "var(--color-muted)" }}/>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8, background: "#F7FAFC", padding: 8, borderRadius: 12, minHeight: 200 }}>
                  {col.items.map((it, i) => (
                    <div key={i} className="card" style={{ padding: 12 }}>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>{it.co}</div>
                      <div style={{ fontSize: 11.5, color: "var(--color-foreground)", marginTop: 2 }}>{it.role}</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 6 }}>{it.date}</div>
                      {it.tag && <span className={`chip chip-${it.tagC || "outline"}`} style={{ marginTop: 8, fontSize: 10, padding: "3px 8px" }}>{it.tag}</span>}
                    </div>
                  ))}
                  {col.items.length === 0 && (
                    <div style={{ padding: 16, fontSize: 12, color: "var(--color-muted)", textAlign: "center", border: "1px dashed var(--color-border)", borderRadius: 8 }}>Drop here</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen15_BroadcastConnect() {
  return (
    <div className="frame" id="s15">
      <Chrome url="linkright.in/broadcast/connect" />
      <div className="frame-body">
        <AppTopNav current="broadcast" />
        <div style={{ padding: "64px 48px 80px", maxWidth: 720, marginInline: "auto", textAlign: "center" }}>
          <div className="iconTile iconTile-pink" style={{ width: 64, height: 64, borderRadius: 18, marginInline: "auto" }}><Icon d={I.linkedin} size={30}/></div>
          <div className="eyebrow" style={{ color: "#B13355", marginTop: 20 }}>Broadcast</div>
          <h1 style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.015em", margin: "8px 0 14px" }}>Connect LinkedIn to draft posts from your wins.</h1>
          <p style={{ color: "var(--color-muted)", fontSize: 15, lineHeight: 1.6, margin: 0 }}>
            Drafts pull from your diary and profile. Nothing posts without your click.
          </p>

          <button className="pill pill-cta pill-lg" style={{ marginTop: 32 }}>
            <Icon d={I.linkedin} size={16}/> Connect LinkedIn
          </button>
          <p style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 14 }}>Opens LinkedIn in a popup · takes 20 seconds</p>

          <div className="card card-lg" style={{ marginTop: 56, textAlign: "left", padding: 24, background: "#FDF6F0", borderColor: "#F8E6D4" }}>
            <p style={{ fontSize: 14, margin: 0, lineHeight: 1.6, color: "#5F4632" }}>
              You click Send. Nothing posts without you. Revoke access anytime from LinkedIn settings. <a style={{ color: "var(--color-accent)", fontWeight: 500 }}>Why we need LinkedIn access.</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen16_InsightsBrowser() {
  const filters = ["Wins", "Learnings", "Takes", "Failures", "Shipped"];
  const insights = [
    { c: "teal", src: "from your diary · 3 days ago", t: "The reason-code drop-off insight", d: "Users couldn't map their issue to our 14-option taxonomy. Compressed it to three, completion jumped 18%.", type: "Win" },
    { c: "gold", src: "from your Amex role", t: "What Walmart taught me about escalations", d: "3 weeks embedded changed how I think about legal UX forever. A policy engine is a language translator, not a rulebook.", type: "Learning" },
    { c: "pink", src: "from your diary · yesterday", t: "My roadmap template is broken", d: "Realised today we're tracking outputs, not bets. Rewriting for Q2.", type: "Take" },
    { c: "purple", src: "from your Sprinklr role", t: "Why 6 of 36 enterprise shipments slipped", d: "Every one missed discovery depth. The pattern is obvious in retrospect.", type: "Failure" },
    { c: "teal", src: "shipped 2 weeks ago", t: "Refund SLA automation is live", d: "5 days → 8 hours across 14,200 merchants. Three weeks from spec to ship.", type: "Shipped" },
    { c: "gold", src: "from your diary · 5 days ago", t: "Interview answer I keep using", d: "The 'why product vs. eng' question. I have a good answer now, built over 20 interviews.", type: "Learning" },
  ];
  return (
    <div className="frame" id="s16">
      <Chrome url="linkright.in/broadcast" />
      <div className="frame-body">
        <AppTopNav current="broadcast" />
        <div style={{ padding: "32px 48px 56px", maxWidth: 1200, marginInline: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
            <div>
              <div className="eyebrow" style={{ color: "#B13355" }}>Broadcast</div>
              <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: "6px 0 4px" }}>Pick something worth posting.</h1>
              <p style={{ color: "var(--color-muted)", margin: 0, fontSize: 14 }}>From your diary, profile, and application outcomes.</p>
            </div>
            <button className="pill pill-ghost pill-sm"><Icon d={I.calendar} size={14}/> Schedule · 2 queued</button>
          </div>

          {/* Filter chips */}
          <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
            <span className="chip chip-pink" style={{ padding: "6px 14px", fontWeight: 600 }}>All · 48</span>
            {["Shipped", "Learned", "Took"].map(f => <span key={f} className="chip chip-outline" style={{ padding: "6px 14px" }}>{f}</span>)}
          </div>

          {/* Insights grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
            {insights.map((n, i) => (
              <div key={i} className="card" style={{ padding: 20, display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                  <span className="chip chip-pink">{n.type}</span>
                  <span style={{ fontSize: 11, color: "var(--color-muted)" }}>{n.src}</span>
                </div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: "6px 0 8px", lineHeight: 1.35, letterSpacing: "-0.005em" }}>{n.t}</h3>
                <p style={{ fontSize: 12.5, color: "var(--color-muted)", margin: "0 0 16px", lineHeight: 1.55, flex: 1 }}>{n.d}</p>
                <button className="pill pill-sm" style={{ alignSelf: "flex-start", background: "#F05A79", color: "#fff", border: "none", padding: "8px 14px" }}>Write a post about this →</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen17_Compose() {
  return (
    <div className="frame" id="s17">
      <Chrome url="linkright.in/broadcast/compose" />
      <div className="frame-body">
        <AppTopNav current="broadcast" />
        <div style={{ padding: "24px 48px 56px", maxWidth: 1200, marginInline: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <button className="pill pill-ghost pill-sm"><Icon d={I.arrowLeft} size={14}/> Back</button>
            <span className="chip chip-pink">Drafting a post</span>
            <span className="chip chip-outline">Based on: the reason-code drop-off insight</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
            {/* Compose */}
            <div>
              <div className="card card-lg" style={{ padding: 24 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, paddingBottom: 14, borderBottom: "1px solid var(--color-border)" }}>
                  <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--color-accent)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>SJ</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>Satvik Jain</div>
                    <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Senior PM · posts to LinkedIn</div>
                  </div>
                </div>

                <textarea disabled style={{ width: "100%", padding: "16px 0", border: "none", fontSize: 15, lineHeight: 1.65, fontFamily: "inherit", resize: "none", height: 320, background: "transparent" }} defaultValue={`40% of our users were dropping off on a dropdown.

Not at payment. Not at auth. At the reason-code step of the returns flow.

We had 14 options. Users couldn't map their issue to any of them, so they abandoned.

The fix wasn't a smarter algorithm. It was compressing 14 options to 3: "Item issue", "Delivery issue", "Changed my mind". Everything else became a follow-up.

Completion jumped 18%. Support tickets dropped 22%.

The hardest product decision is usually: what do we remove?`} />

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 14, borderTop: "1px solid var(--color-border)" }}>
                  <div style={{ fontSize: 12, color: "var(--color-muted)" }}>632 / 3000 characters</div>
                  <span style={{ fontSize: 11, color: "var(--color-muted)" }}>Draft</span>
                </div>
              </div>

              {/* Tone toggles */}
              <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
                <span style={{ fontSize: 12, color: "var(--color-muted)", fontWeight: 500, alignSelf: "center", marginRight: 4 }}>Adjust:</span>
                {["Shorter", "Punchier", "More personal", "Add a question at the end", "Sharper takeaway"].map(t => (
                  <span key={t} className="chip chip-outline" style={{ padding: "6px 12px", fontSize: 12, cursor: "default" }}>{t}</span>
                ))}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
                <button className="pill pill-ghost">Save as draft</button>
                <div style={{ display: "flex", gap: 10 }}>
                  <button className="pill pill-ghost"><Icon d={I.calendar} size={14}/> Schedule</button>
                  <button className="pill" style={{ background: "#F05A79", color: "#fff", border: "none" }}>Post now</button>
                </div>
              </div>
            </div>

            {/* Source + LinkedIn preview */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Source panel */}
              <div className="card card-lg" style={{ padding: 20, background: "#FDF6F0", borderColor: "#F8E6D4" }}>
                <div className="eyebrow" style={{ color: "#8A6E53" }}>Source</div>
                <p style={{ fontSize: 13, margin: "8px 0 10px", fontWeight: 600 }}>The reason-code drop-off insight</p>
                <p style={{ fontSize: 12.5, color: "#5F4632", margin: 0, lineHeight: 1.55 }}>
                  "Users couldn't map their issue to our 14-option taxonomy. Compressed it to three, completion jumped 18%."
                </p>
                <div style={{ fontSize: 11, color: "#8A6E53", marginTop: 10 }}>From your diary · 3 days ago</div>
              </div>

              {/* LinkedIn preview */}
              <div className="card card-lg" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "10px 14px", background: "#F3F2EF", fontSize: 11, color: "#666", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", gap: 6 }}>
                  <Icon d={I.eye} size={12}/><span>Preview on LinkedIn</span>
                </div>
                <div style={{ padding: 16, background: "#fff" }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--color-accent)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 14 }}>SJ</div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Satvik Jain <span style={{ color: "#666", fontWeight: 400, fontSize: 11 }}>· You</span></div>
                      <div style={{ fontSize: 11, color: "#666" }}>Senior PM · American Express</div>
                      <div style={{ fontSize: 11, color: "#666" }}>Now · 🌐</div>
                    </div>
                  </div>
                  <p style={{ fontSize: 13, color: "#000", lineHeight: 1.55, margin: "12px 0 0", whiteSpace: "pre-line" }}>
                    40% of our users were dropping off on a dropdown.{"\n\n"}Not at payment. Not at auth. At the reason-code step of the returns flow.{"\n\n"}We had 14 options. Users couldn't…
                  </p>
                  <div style={{ display: "flex", gap: 16, marginTop: 14, paddingTop: 10, borderTop: "1px solid #E2E8F0", fontSize: 11, color: "#666" }}>
                    <span>👍 React</span><span>💬 Comment</span><span>🔁 Repost</span><span>↗ Share</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen18_ScheduleTracker() {
  return (
    <div className="frame" id="s18">
      <Chrome url="linkright.in/broadcast/schedule" />
      <div className="frame-body">
        <AppTopNav current="broadcast" />
        <div style={{ padding: "32px 48px 56px", maxWidth: 1200, marginInline: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
            <div>
              <div className="eyebrow" style={{ color: "#B13355" }}>Broadcast · schedule</div>
              <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: "6px 0 4px" }}>Your voice, on a schedule.</h1>
              <p style={{ color: "var(--color-muted)", margin: 0, fontSize: 14 }}>Avg. 47 reactions on your last 7 posts. +18% vs. last month.</p>
            </div>
            <button className="pill pill-cta pill-sm"><Icon d={I.plus} size={14}/> New post</button>
          </div>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 24, borderBottom: "1px solid var(--color-border)", marginBottom: 20 }}>
            {[["Scheduled", 2, true], ["Posted", 14, false], ["Drafts", 3, false]].map(([l, n, on]) => (
              <a key={l} style={{ padding: "10px 0", color: on ? "var(--color-foreground)" : "var(--color-muted)", fontWeight: on ? 600 : 500, fontSize: 14, borderBottom: on ? "2px solid var(--color-accent)" : "none", marginBottom: -1 }}>
                {l} <span style={{ color: "var(--color-muted)", marginLeft: 4, fontSize: 12 }}>({n})</span>
              </a>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>
            {/* Upcoming */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { date: "Tomorrow · 9:30 AM", title: "The reason-code drop-off insight", body: "40% of our users were dropping off on a dropdown…", status: "scheduled" },
                { date: "Friday · 5:00 PM", title: "What Walmart taught me about escalations", body: "3 weeks embedded changed how I think about legal UX…", status: "scheduled" },
                { date: "Apr 12 · posted", title: "Refund SLA automation shipped", body: "Five days → eight hours. Three weeks spec-to-ship…", status: "posted", stats: { reactions: 142, comments: 23, reposts: 9 } },
                { date: "Apr 8 · posted", title: "Why 6 of 36 shipments slipped", body: "Every one missed discovery depth. The pattern was…", status: "posted", stats: { reactions: 89, comments: 31, reposts: 4 } },
              ].map((p, i) => (
                <div key={i} className="card" style={{ padding: 18 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      {p.status === "scheduled" ? (
                        <span className="chip chip-gold"><Icon d={I.calendar} size={12}/> {p.date}</span>
                      ) : (
                        <span className="chip chip-teal">✓ {p.date}</span>
                      )}
                    </div>
                    <Icon d={I.ellipsis} size={16} style={{ color: "var(--color-muted)" }}/>
                  </div>
                  <h3 style={{ fontSize: 14, fontWeight: 600, margin: "6px 0 4px" }}>{p.title}</h3>
                  <p style={{ fontSize: 12.5, color: "var(--color-muted)", margin: 0, lineHeight: 1.5 }}>{p.body}</p>
                  {p.stats && (
                    <div style={{ display: "flex", gap: 16, marginTop: 10, paddingTop: 10, borderTop: "1px dashed var(--color-border)", fontSize: 12, color: "var(--color-muted)" }}>
                      <span>👍 {p.stats.reactions}</span>
                      <span>💬 {p.stats.comments}</span>
                      <span>🔁 {p.stats.reposts}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Analytics */}
            <div className="card card-lg" style={{ padding: 22 }}>
              <div className="eyebrow" style={{ color: "#B13355" }}>Last 30 days</div>
              <div style={{ fontSize: 36, fontWeight: 700, letterSpacing: "-0.02em", margin: "8px 0 2px", color: "var(--color-foreground)" }}>2,847</div>
              <div style={{ fontSize: 12, color: "var(--color-muted)" }}>total impressions · <span style={{ color: "#09766D", fontWeight: 600 }}>+28%</span></div>

              <div style={{ height: 60, display: "flex", alignItems: "flex-end", gap: 3, marginTop: 20 }}>
                {[20, 35, 28, 42, 58, 45, 38, 52, 68, 48, 55, 42, 72, 58].map((h, i) => (
                  <div key={i} style={{ flex: 1, height: `${h}%`, background: i === 12 ? "#F05A79" : "rgba(240,90,121,0.3)", borderRadius: 2 }}/>
                ))}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 24 }}>
                {[["47", "avg. reactions"], ["14", "posts shipped"]].map(([n, l]) => (
                  <div key={l}>
                    <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.015em" }}>{n}</div>
                    <div style={{ fontSize: 11, color: "var(--color-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 2 }}>{l}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen19_Diary() {
  return (
    <div className="frame" id="s19">
      <Chrome url="linkright.in/dashboard" />
      <div className="frame-body" style={{ position: "relative", minHeight: 720 }}>
        {/* Base dashboard behind */}
        <AppTopNav current="dashboard" />
        <div style={{ padding: 48, opacity: 0.4 }}>
          <div style={{ height: 28, width: 300, background: "#E2E8F0", borderRadius: 6, marginBottom: 14 }}/>
          <div style={{ height: 16, width: 400, background: "#EDF2F7", borderRadius: 6 }}/>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginTop: 32 }}>
            {[1,2,3].map(i => <div key={i} style={{ height: 120, background: "#fff", border: "1px solid var(--color-border)", borderRadius: 12 }}/>)}
          </div>
        </div>

        {/* Dim overlay */}
        <div style={{ position: "absolute", inset: 0, top: 60, background: "rgba(45,35,80,0.55)" }}/>

        {/* Diary modal — full-height, purple-accented */}
        <div style={{ position: "absolute", top: 80, left: "50%", transform: "translateX(-50%)", width: 640, bottom: 28, background: "#fff", borderRadius: 20, boxShadow: "0 24px 64px rgba(0,0,0,0.25)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "20px 28px", background: "linear-gradient(180deg, rgba(139,92,246,0.08) 0%, #fff 100%)", borderBottom: "1px solid var(--color-border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div className="eyebrow" style={{ color: "#5A36AB" }}>Daily diary · your memory layer</div>
                <h3 style={{ fontSize: 20, fontWeight: 700, margin: "4px 0 0", letterSpacing: "-0.01em" }}>What happened today?</h3>
              </div>
              <Icon d={I.x} size={18} style={{ color: "var(--color-muted)" }}/>
            </div>
          </div>

          <div style={{ padding: 28, flex: 1, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 16, padding: 4, background: "#F7FAFC", borderRadius: 10, width: "fit-content" }}>
              <span className="pill pill-sm" style={{ padding: "6px 14px", background: "#8B5CF6", color: "#fff", border: "none" }}>Type</span>
              <span style={{ padding: "6px 14px", fontSize: 12, fontWeight: 500, color: "var(--color-muted)" }}><Icon d={I.mic} size={12} style={{ display: "inline", verticalAlign: -1, marginRight: 4 }}/>Record</span>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
              {["What did you ship?", "What did you learn?", "What pissed you off?", "Who surprised you?"].map(h => (
                <span key={h} className="chip chip-outline" style={{ fontSize: 11, cursor: "default" }}>{h}</span>
              ))}
            </div>

            <textarea disabled placeholder="Just write. Doesn't have to be polished." defaultValue="Figured out why merchants hate the reason-code step, they can't map their issue to any of the 14 options. Suggested we compress to 3 umbrella categories with follow-ups. Sent a mini-doc to Aarav for review." style={{ width: "100%", padding: "16px 18px", border: "1px solid rgba(139,92,246,0.25)", borderRadius: 12, fontSize: 14, lineHeight: 1.65, fontFamily: "inherit", resize: "none", flex: 1, background: "#FAF8FF", outline: "none" }}/>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
              <span style={{ fontSize: 12, color: "var(--color-muted)" }}>Folds into your profile.</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="pill pill-ghost pill-sm">Close</button>
                <button className="pill pill-sm" style={{ background: "#8B5CF6", color: "#fff", border: "none" }}>Save & continue</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen20_Profile() {
  return (
    <div className="frame" id="s20">
      <Chrome url="linkright.in/settings" />
      <div className="frame-body">
        <AppTopNav current="settings" />
        <div style={{ padding: "32px 48px 56px", maxWidth: 1000, marginInline: "auto" }}>
          <div className="eyebrow" style={{ color: "#64748B" }}>Opened from your avatar</div>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: "6px 0 24px" }}>Account &amp; settings</h1>

          {/* Identity */}
          <div className="card card-lg" style={{ padding: 24, marginBottom: 20 }}>
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#E2E8F0", color: "#334155", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 22 }}>SJ</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 18, fontWeight: 700 }}>Satvik Jain</div>
                <div style={{ fontSize: 13, color: "var(--color-muted)", marginTop: 2 }}>satvik.jain@gmail.com · Pro plan</div>
                <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
                  <span className="chip">47 highlights in your memory</span>
                  <span className="chip">Active since Mar 12</span>
                </div>
              </div>
              <button className="pill pill-ghost pill-sm">Edit</button>
            </div>
          </div>

          {/* Bulk upload */}
          <div className="card card-lg" style={{ padding: 24, marginBottom: 20, background: "rgba(139,92,246,0.04)", borderColor: "rgba(139,92,246,0.2)" }}>
            <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
              <div className="iconTile iconTile-purple"><Icon d={I.document}/></div>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>Bulk upload a career file</h3>
                <p style={{ fontSize: 13, color: "var(--color-muted)", margin: 0, lineHeight: 1.55 }}>
                  Already have everything written up? Upload a JSON file, we'll fold it into your profile and skip the click-by-click work.
                </p>
                <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
                  <button className="pill pill-ghost pill-sm"><Icon d={I.arrowDown} size={14}/> Download template</button>
                  <button className="pill pill-sm" style={{ background: "#8B5CF6", color: "#fff", border: "none" }}><Icon d={I.upload} size={14}/> Upload file</button>
                </div>
              </div>
            </div>
          </div>

          {/* Integrations */}
          <div className="card card-lg" style={{ padding: 24, marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px" }}>Connected accounts</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { icon: I.linkedin, name: "LinkedIn", st: "Connected · linkedin.com/in/satvikj", c: "purple", on: true },
                { icon: I.github, name: "GitHub", st: "Connected · for Pages hosting", c: "purple", on: true },
                { icon: I.globe, name: "Personal website", st: "Not connected", c: "outline", on: false },
              ].map(r => (
                <div key={r.name} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 14px", border: "1px solid var(--color-border)", borderRadius: 12 }}>
                  <Icon d={r.icon} size={20} style={{ color: r.on ? "var(--color-accent)" : "var(--color-muted)" }}/>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{r.name}</div>
                    <div style={{ fontSize: 12, color: "var(--color-muted)" }}>{r.st}</div>
                  </div>
                  <button className="pill pill-ghost pill-sm">{r.on ? "Disconnect" : "Connect"}</button>
                </div>
              ))}
            </div>
          </div>

          {/* Danger zone */}
          <div className="card card-lg" style={{ padding: 24, borderColor: "rgba(255,87,51,0.2)" }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px", color: "#B3341C" }}>Danger zone</h3>
            <p style={{ fontSize: 13, color: "var(--color-muted)", margin: "0 0 14px" }}>Permanently delete your account and all data. This cannot be undone.</p>
            <button className="pill pill-ghost pill-sm" style={{ borderColor: "rgba(255,87,51,0.3)", color: "#B3341C" }}>Delete account</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen21_Notifications() {
  const items = [
    { c: "teal", t: "3 new roles matched today", s: "Razorpay, Zepto, Groww. All 79%+ fit.", time: "Just now" },
    { c: "pink", t: "Post went live", s: "\"Refund SLA automation shipped\" · 47 reactions", time: "3h ago" },
    { c: "sage", t: "Interview prep reminder", s: "Your Razorpay round is in 3 days. 5 drills queued.", time: "Yesterday" },
    { c: "teal", t: "PhonePe moved you to round 2", s: "Scheduled Apr 22. Application tracker updated.", time: "2 days ago" },
    { c: "teal", t: "Cred resume draft timed out", s: "We saved your progress. Pick up anytime.", time: "3 days ago" },
  ];
  return (
    <div className="frame" id="s21">
      <Chrome url="linkright.in/dashboard" />
      <div className="frame-body" style={{ position: "relative", minHeight: 720 }}>
        <AppTopNav current="dashboard" />
        <div style={{ padding: 48, opacity: 0.4 }}>
          <div style={{ height: 28, width: 300, background: "#E2E8F0", borderRadius: 6 }}/>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginTop: 32 }}>
            {[1,2,3].map(i => <div key={i} style={{ height: 120, background: "#fff", border: "1px solid var(--color-border)", borderRadius: 12 }}/>)}
          </div>
        </div>

        {/* Drawer */}
        <div style={{ position: "absolute", top: 60, right: 0, bottom: 0, width: 400, background: "#fff", borderLeft: "1px solid var(--color-border)", boxShadow: "-12px 0 32px rgba(0,0,0,0.08)" }}>
          <div style={{ padding: "18px 20px", borderBottom: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Notifications</h3>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <a style={{ fontSize: 12, color: "var(--color-accent)", fontWeight: 500 }}>Mark all read</a>
              <Icon d={I.x} size={16} style={{ color: "var(--color-muted)" }}/>
            </div>
          </div>

          <div>
            {items.map((it, i) => (
              <div key={i} style={{ padding: "14px 20px", borderBottom: i === items.length - 1 ? "none" : "1px solid var(--color-border)", display: "flex", gap: 12, cursor: "default", background: i < 2 ? "rgba(15,190,175,0.03)" : "transparent" }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 6, flexShrink: 0, background: it.c === "teal" ? "#0FBEAF" : it.c === "purple" ? "#8B5CF6" : it.c === "pink" ? "#F05A79" : it.c === "sage" ? "#6B8346" : it.c === "gold" ? "#E5B80B" : "#CBD5E0" }}/>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.4 }}>{it.t}</div>
                  <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2, lineHeight: 1.5 }}>{it.s}</div>
                  <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 6 }}>{it.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Screen12_Dashboard, Screen13_InterviewPrep, Screen14_Applications, Screen15_BroadcastConnect, Screen16_InsightsBrowser, Screen17_Compose, Screen18_ScheduleTracker, Screen19_Diary, Screen20_Profile, Screen21_Notifications });
