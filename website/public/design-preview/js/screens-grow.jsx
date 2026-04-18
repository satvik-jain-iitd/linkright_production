// GROW phase: Screens 12-21 (Dashboard, Interview prep, Apps tracker, Broadcast x4, Diary, Profile, Notifications)

function Screen12_Dashboard() {
  return (
    <div className="frame" id="s12">
      <Chrome url="linkright.in/dashboard" />
      <div className="frame-body">
        <AppTopNav current="dashboard" />
        <div style={{ padding: "32px 48px 56px", maxWidth: 1200, marginInline: "auto" }}>
          {/* Welcome */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 28 }}>
            <div>
              <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: 0 }}>Good morning, Satvik.</h1>
              <p style={{ color: "var(--color-muted)", margin: "6px 0 0", fontSize: 14 }}>5 new matches since Tuesday · You're on a 4-day streak</p>
            </div>
            <span className="chip chip-gold" style={{ padding: "6px 12px" }}><Icon d={I.fire} size={14}/> 4-day streak · don't break it</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24 }}>
            {/* Main column */}
            <div>
              {/* Today's matches */}
              <div style={{ marginBottom: 28 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                  <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>Today's matches</h2>
                  <a style={{ fontSize: 13, color: "var(--color-accent)", fontWeight: 500 }}>See all 20 →</a>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                  {[
                    { co: "Razorpay", role: "Senior PM, Payments", score: 87, loc: "Bangalore" },
                    { co: "Zepto", role: "Product Lead, Merchant", score: 82, loc: "Mumbai" },
                    { co: "Groww", role: "Principal PM, Investing", score: 79, loc: "Bangalore" },
                  ].map(r => (
                    <div key={r.co} className="card" style={{ padding: 16 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{r.co}</span>
                        <span style={{ fontSize: 14, fontWeight: 700, color: r.score >= 80 ? "var(--color-accent)" : "#C49B09" }}>{r.score}%</span>
                      </div>
                      <div style={{ fontSize: 13, margin: "6px 0 2px" }}>{r.role}</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)" }}>{r.loc}</div>
                      <button className="pill pill-outline-teal pill-sm" style={{ marginTop: 12, width: "100%" }}>Start application</button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Keep going */}
              <div style={{ marginBottom: 28 }}>
                <h2 style={{ fontSize: 17, fontWeight: 600, margin: "0 0 14px" }}>Keep going</h2>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div className="card" style={{ padding: 16, display: "flex", alignItems: "center", gap: 14, borderColor: "rgba(139,92,246,0.3)", background: "rgba(139,92,246,0.04)" }}>
                    <div className="iconTile iconTile-purple"><Icon d={I.document}/></div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>Pick up where you left off</div>
                      <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Draft resume for Cred — Product Manager, Cred Pay · 72% done</div>
                    </div>
                    <button className="pill pill-teal pill-sm">Resume</button>
                  </div>
                  <div className="card" style={{ padding: 16, display: "flex", alignItems: "center", gap: 14 }}>
                    <div className="iconTile iconTile-sage"><Icon d={I.chat}/></div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>5 behavioural drills for Razorpay</div>
                      <div style={{ fontSize: 12, color: "var(--color-muted)" }}>15 minutes · based on their past interview questions</div>
                    </div>
                    <button className="pill pill-ghost pill-sm">Start →</button>
                  </div>
                </div>
              </div>

              {/* Scout watchlist */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                  <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>Scout · companies you're watching</h2>
                  <a style={{ fontSize: 13, color: "var(--color-accent)", fontWeight: 500 }}>Manage →</a>
                </div>
                <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                  {[
                    { co: "Stripe", upd: "2 new roles posted this week", dot: "teal" },
                    { co: "Linear", upd: "Hired their first India PM · signal ↑", dot: "purple" },
                    { co: "Vercel", upd: "No new activity for 12 days", dot: "gray" },
                  ].map((w, i) => (
                    <div key={w.co} style={{ padding: "14px 18px", borderBottom: i === 2 ? "none" : "1px solid var(--color-border)", display: "flex", alignItems: "center", gap: 14 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: w.dot === "teal" ? "#0FBEAF" : w.dot === "purple" ? "#8B5CF6" : "#CBD5E0" }}/>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{w.co}</div>
                        <div style={{ fontSize: 12, color: "var(--color-muted)" }}>{w.upd}</div>
                      </div>
                      <a style={{ fontSize: 13, color: "var(--color-muted)" }}>View →</a>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right column — Profile card */}
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div className="card card-lg" style={{ padding: 24, background: "linear-gradient(180deg, rgba(139,92,246,0.06) 0%, #FFFFFF 100%)" }}>
                <div className="eyebrow" style={{ color: "#8B5CF6" }}>Your profile</div>
                <h3 style={{ fontSize: 18, fontWeight: 700, margin: "6px 0 12px", letterSpacing: "-0.01em" }}>Still growing.</h3>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginTop: 6 }}>
                  {[["47", "highlights"], ["4", "companies"], ["6", "weeks active"], ["12", "diary entries"]].map(([n, l]) => (
                    <div key={l}>
                      <div style={{ fontSize: 22, fontWeight: 700, color: "#5A36AB", letterSpacing: "-0.02em" }}>{n}</div>
                      <div style={{ fontSize: 11, color: "var(--color-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 2 }}>{l}</div>
                    </div>
                  ))}
                </div>

                <button className="pill pill-outline-teal pill-sm" style={{ marginTop: 18, width: "100%" }}>Add more → sharpens every match</button>
              </div>

              {/* Diary quick-log */}
              <div className="card card-lg" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div className="eyebrow">Daily diary</div>
                  <span style={{ fontSize: 11, color: "var(--color-muted)" }}>60 seconds</span>
                </div>
                <textarea disabled placeholder="What did you ship today?" style={{ width: "100%", padding: 12, border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 13, fontFamily: "inherit", resize: "none", height: 64 }}/>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
                  <button className="pill pill-ghost pill-sm"><Icon d={I.mic} size={12}/> Record instead</button>
                  <button className="pill pill-teal pill-sm">Log</button>
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
    { c: "sage", title: "Product sense", d: "Frame, prioritise, design. Tailored to your target roles.", n: "8 drills queued" },
    { c: "sage", title: "System design", d: "Whiteboard walkthroughs with real-time critique.", n: "5 drills queued" },
    { c: "sage", title: "Behavioural", d: "Your stories, sharpened. Pulled from your diary + resume.", n: "12 drills queued" },
    { c: "sage", title: "Case", d: "Consulting-style market-size and profitability cases.", n: "6 drills queued" },
    { c: "sage", title: "Technical / coding", d: "Mid-level DSA + API design, at your level.", n: "10 drills queued" },
    { c: "sage", title: "SQL", d: "Window functions, joins, query optimisation.", n: "7 drills queued" },
    { c: "sage", title: "Growth", d: "Funnel diagnosis, experiment design, activation work.", n: "4 drills queued" },
    { c: "sage", title: "Telephonic screen", d: "The 20-minute recruiter call, practiced.", n: "6 drills queued" },
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
            <p style={{ color: "var(--color-muted)", fontSize: 15, margin: 0 }}>We know what you're good at. We also know where you're thin. Pick something — drills are tailored to your profile and target roles.</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
            {cards.map(c => (
              <div key={c.title} className="card" style={{ padding: 18, background: "#F3F6EA", borderColor: "rgba(107,131,70,0.2)" }}>
                <div className="iconTile iconTile-sage" style={{ background: "rgba(107,131,70,0.14)" }}><Icon d={I.chat}/></div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: "12px 0 6px", color: "#2E3B1E" }}>{c.title}</h3>
                <p style={{ fontSize: 12.5, color: "#4A5D32", margin: 0, lineHeight: 1.5 }}>{c.d}</p>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, paddingTop: 12, borderTop: "1px dashed rgba(107,131,70,0.3)" }}>
                  <span style={{ fontSize: 11, color: "#4A5D32" }}>{c.n}</span>
                  <button style={{ fontSize: 12, fontWeight: 600, color: "#4A5D32", background: "transparent", border: "none", cursor: "default" }}>Start →</button>
                </div>
              </div>
            ))}
          </div>

          {/* Coming soon — Oracle roundtable */}
          <div style={{ marginTop: 28, padding: 24, background: "#fff", border: "1px dashed var(--color-border)", borderRadius: 16, display: "flex", alignItems: "center", gap: 18 }}>
            <div className="iconTile iconTile-purple" style={{ width: 56, height: 56, borderRadius: 14 }}><Icon d={I.sparkles} size={26}/></div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Oracle — multi-persona recruiter roundtable</h3>
                <span className="chip chip-gold">Soon</span>
              </div>
              <p style={{ fontSize: 13, color: "var(--color-muted)", margin: "4px 0 0" }}>Three AI personas — hiring manager, recruiter, cross-functional partner — grill you in parallel. Get feedback from each angle in one session.</p>
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
    { name: "Wishlist", n: 6, color: "#718096", items: [
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
    { name: "Interview", n: 2, color: "#E5B80B", items: [
      { co: "PhonePe", role: "Senior PM, Lending", date: "Round 2 on Apr 22", tag: "Prep 3 drills", tagC: "gold" },
    ]},
    { name: "Offer", n: 1, color: "#F05A79", items: [
      { co: "Swiggy", role: "PM, Instamart", date: "Offered ₹68L", tag: "Decide by Apr 26", tagC: "pink" },
    ]},
    { name: "Rejected", n: 4, color: "#B3341C", items: [
      { co: "Cure.fit", role: "PM, Fitness", date: "Rejected Apr 8", tag: "+ log outcome", tagC: "coral" },
    ]},
  ];
  return (
    <div className="frame" id="s14">
      <Chrome url="linkright.in/applications" />
      <div className="frame-body">
        <AppTopNav current="apps" />
        <div style={{ padding: "28px 32px 56px", maxWidth: "100%", overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24, padding: "0 16px" }}>
            <div>
              <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.015em", margin: 0 }}>Applications</h1>
              <p style={{ color: "var(--color-muted)", margin: "4px 0 0", fontSize: 14 }}>24 active · 4-week pipeline · avg. 3.2 days to first response</p>
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
          <h1 style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.015em", margin: "8px 0 14px" }}>Connect LinkedIn to draft posts from your actual wins.</h1>
          <p style={{ color: "var(--color-muted)", fontSize: 15, lineHeight: 1.6, margin: 0 }}>
            We pull from your diary and profile. Nothing goes live without you clicking Send. You stay in control.
          </p>

          <button className="pill pill-cta pill-lg" style={{ marginTop: 32 }}>
            <Icon d={I.linkedin} size={16}/> Connect LinkedIn
          </button>
          <p style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 14 }}>Opens LinkedIn in a popup · takes 20 seconds</p>

          <div className="card card-lg" style={{ marginTop: 56, textAlign: "left", padding: 28, background: "#FDF6F0", borderColor: "#F8E6D4" }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 16px" }}>What we will and won't do</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#09766D", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>We will</div>
                {["Draft posts from your own wins", "Let you edit every word before it ships", "Post only when you schedule it yourself"].map(t => (
                  <div key={t} style={{ display: "flex", gap: 8, fontSize: 13, marginBottom: 6, alignItems: "flex-start" }}>
                    <span style={{ color: "var(--color-accent)", marginTop: 2 }}>✓</span><span>{t}</span>
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#B3341C", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>We won't</div>
                {["Auto-post anything without your click", "Read your DMs or private messages", "Spam your connections with invites"].map(t => (
                  <div key={t} style={{ display: "flex", gap: 8, fontSize: 13, marginBottom: 6, alignItems: "flex-start" }}>
                    <span style={{ color: "#B3341C", marginTop: 2 }}>✕</span><span>{t}</span>
                  </div>
                ))}
              </div>
            </div>
            <p style={{ fontSize: 12, color: "var(--color-muted)", margin: "20px 0 0", paddingTop: 16, borderTop: "1px dashed rgba(26,32,44,0.1)" }}>Revoke access anytime from LinkedIn settings. <a style={{ color: "var(--color-accent)" }}>Why does LinkRight need LinkedIn?</a></p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen16_InsightsBrowser() {
  const filters = ["Wins", "Learnings", "Takes", "Failures", "Shipped"];
  const insights = [
    { c: "teal", src: "from your diary · 3 days ago", t: "The reason-code drop-off insight", d: "Users couldn't map their issue to our 14-option taxonomy. Compressed it to three — completion jumped 18%.", type: "Win" },
    { c: "gold", src: "from your Amex role", t: "What Walmart taught me about escalations", d: "3 weeks embedded changed how I think about legal UX forever. A policy engine is a language translator, not a rulebook.", type: "Learning" },
    { c: "pink", src: "from your diary · yesterday", t: "My roadmap template is broken", d: "Realised today we're tracking outputs, not bets. Rewriting for Q2.", type: "Take" },
    { c: "purple", src: "from your Sprinklr role", t: "Why 6 of 36 enterprise shipments slipped", d: "Every one missed discovery depth. The pattern is obvious in retrospect.", type: "Failure" },
    { c: "teal", src: "shipped 2 weeks ago", t: "Refund SLA automation is live", d: "5 days → 8 hours across 14,200 merchants. Three weeks from spec to ship.", type: "Shipped" },
    { c: "gold", src: "from your diary · 5 days ago", t: "Interview answer I keep using", d: "The 'why product vs. eng' question — I have a good answer now, built over 20 interviews.", type: "Learning" },
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
              <p style={{ color: "var(--color-muted)", margin: 0, fontSize: 14 }}>Drawn from your diary, profile, and application outcomes. All true.</p>
            </div>
            <button className="pill pill-ghost pill-sm"><Icon d={I.calendar} size={14}/> Schedule · 2 queued</button>
          </div>

          {/* Filter chips */}
          <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
            <span className="chip chip-pink" style={{ padding: "6px 14px", fontWeight: 600 }}>All · 48</span>
            {filters.map(f => <span key={f} className="chip chip-outline" style={{ padding: "6px 14px" }}>{f}</span>)}
          </div>

          {/* Insights grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
            {insights.map((n, i) => (
              <div key={i} className="card" style={{ padding: 20, display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                  <span className={`chip chip-${n.c}`}>{n.type}</span>
                  <span style={{ fontSize: 11, color: "var(--color-muted)" }}>{n.src}</span>
                </div>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: "6px 0 8px", lineHeight: 1.35, letterSpacing: "-0.005em" }}>{n.t}</h3>
                <p style={{ fontSize: 12.5, color: "var(--color-muted)", margin: "0 0 16px", lineHeight: 1.55, flex: 1 }}>{n.d}</p>
                <button className="pill pill-outline-teal pill-sm" style={{ alignSelf: "flex-start" }}>Write a post about this →</button>
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

We had 14 options. Users couldn't map their issue to any of them — so they abandoned.

The fix wasn't a smarter algorithm. It was compressing 14 options to 3: "Item issue", "Delivery issue", "Changed my mind". Everything else became a follow-up.

Completion jumped 18%. Support tickets dropped 22%.

The hardest product decision is usually: what do we remove?`} />

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 14, borderTop: "1px solid var(--color-border)" }}>
                  <div style={{ fontSize: 12, color: "var(--color-muted)" }}>632 / 3000 characters · LinkedIn-friendly length</div>
                  <span className="chip chip-purple"><Icon d={I.sparkles} size={12}/> 2 regens left</span>
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
                  <button className="pill pill-cta">Post now</button>
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
                  "Users couldn't map their issue to our 14-option taxonomy. Compressed it to three — completion jumped 18%."
                </p>
                <div style={{ fontSize: 11, color: "#8A6E53", marginTop: 10 }}>From your diary · 3 days ago</div>
              </div>

              {/* LinkedIn preview */}
              <div className="card card-lg" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "10px 14px", background: "#F3F2EF", fontSize: 11, color: "#666", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", borderBottom: "1px solid #E2E8F0" }}>
                  <Icon d={I.eye} size={12} style={{ display: "inline", marginRight: 6, verticalAlign: -1 }}/>Preview on LinkedIn
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
                    <span>👍 Like</span><span>💬 Comment</span><span>↗ Share</span>
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
              <p style={{ color: "var(--color-muted)", margin: 0, fontSize: 14 }}>Avg. 47 reactions across your last 7 posts · +18% vs. last month</p>
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
                { date: "Apr 12 · posted", title: "Refund SLA automation shipped", body: "Five days → eight hours. Three weeks spec-to-ship…", status: "posted", stats: { likes: 142, comments: 23, shares: 9 } },
                { date: "Apr 8 · posted", title: "Why 6 of 36 shipments slipped", body: "Every one missed discovery depth. The pattern was…", status: "posted", stats: { likes: 89, comments: 31, shares: 4 } },
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
                      <span>👍 {p.stats.likes}</span>
                      <span>💬 {p.stats.comments}</span>
                      <span>↗ {p.stats.shares}</span>
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
                {[["47", "avg. reactions"], ["8.2", "avg. comments"], ["14", "posts shipped"], ["3", "in queue"]].map(([n, l]) => (
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
        <div style={{ position: "absolute", inset: 0, top: 60, background: "rgba(26,32,44,0.4)" }}/>

        {/* Diary modal */}
        <div style={{ position: "absolute", top: 100, left: "50%", transform: "translateX(-50%)", width: 580, background: "#fff", borderRadius: 20, boxShadow: "0 24px 64px rgba(0,0,0,0.2)", overflow: "hidden" }}>
          <div style={{ padding: "18px 24px", background: "linear-gradient(180deg, #FDF6F0 0%, #fff 100%)", borderBottom: "1px solid var(--color-border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div className="eyebrow" style={{ color: "#E5B80B" }}>Daily diary · 60 seconds</div>
                <h3 style={{ fontSize: 18, fontWeight: 700, margin: "4px 0 0", letterSpacing: "-0.01em" }}>What happened today?</h3>
              </div>
              <span className="chip chip-gold"><Icon d={I.fire} size={12}/> 4-day streak</span>
            </div>
          </div>

          <div style={{ padding: 24 }}>
            {/* Mode toggle */}
            <div style={{ display: "flex", gap: 8, marginBottom: 16, padding: 4, background: "#F7FAFC", borderRadius: 10, width: "fit-content" }}>
              <span className="pill pill-teal pill-sm" style={{ padding: "6px 14px" }}>Type</span>
              <span style={{ padding: "6px 14px", fontSize: 12, fontWeight: 500, color: "var(--color-muted)" }}><Icon d={I.mic} size={12} style={{ display: "inline", verticalAlign: -1, marginRight: 4 }}/>Record 60s</span>
            </div>

            {/* Hints */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {["What did you ship?", "What did you learn?", "What pissed you off?", "Who surprised you?"].map(h => (
                <span key={h} className="chip chip-outline" style={{ fontSize: 11, cursor: "default" }}>{h}</span>
              ))}
            </div>

            <textarea disabled placeholder="Just write. Doesn't have to be polished." defaultValue="Figured out why merchants hate the reason-code step — they can't map their issue to any of the 14 options. Suggested we compress to 3 umbrella categories with follow-ups. Sent a mini-doc to Aarav for review." style={{ width: "100%", padding: "14px 16px", border: "1px solid var(--color-border)", borderRadius: 12, fontSize: 14, lineHeight: 1.6, fontFamily: "inherit", resize: "none", height: 160, background: "#fff" }}/>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}>
              <span style={{ fontSize: 12, color: "var(--color-muted)" }}>+1 highlight will be added to your profile</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="pill pill-ghost pill-sm">Close</button>
                <button className="pill pill-teal pill-sm">Save & continue</button>
              </div>
            </div>
          </div>
        </div>

        {/* Floating button (shows where the CTA lives) */}
        <div style={{ position: "absolute", bottom: 28, right: 28, width: 56, height: 56, borderRadius: "50%", background: "var(--color-cta)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", boxShadow: "0 12px 32px rgba(255,87,51,0.3)" }}>
          <Icon d={I.plus} size={24}/>
        </div>
      </div>
    </div>
  );
}

function Screen20_Profile() {
  return (
    <div className="frame" id="s20">
      <Chrome url="linkright.in/profile" />
      <div className="frame-body">
        <AppTopNav current="profile" />
        <div style={{ padding: "32px 48px 56px", maxWidth: 1000, marginInline: "auto" }}>
          <div className="eyebrow">Your profile</div>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.015em", margin: "6px 0 24px" }}>Account & settings</h1>

          {/* Identity */}
          <div className="card card-lg" style={{ padding: 24, marginBottom: 20 }}>
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "var(--color-accent)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 22 }}>SJ</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 18, fontWeight: 700 }}>Satvik Jain</div>
                <div style={{ fontSize: 13, color: "var(--color-muted)", marginTop: 2 }}>satvik.jain@gmail.com · Pro plan</div>
                <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
                  <span className="chip chip-teal">47 highlights</span>
                  <span className="chip">4 companies</span>
                  <span className="chip">6 weeks active</span>
                  <span className="chip">12 diary entries</span>
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
                  Already have everything written up? Upload a JSON file — we'll fold it into your profile and skip the click-by-click work.
                </p>
                <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
                  <button className="pill pill-outline-teal pill-sm"><Icon d={I.arrowDown} size={14}/> Download template</button>
                  <button className="pill pill-teal pill-sm"><Icon d={I.upload} size={14}/> Upload file</button>
                </div>
              </div>
            </div>
          </div>

          {/* Integrations */}
          <div className="card card-lg" style={{ padding: 24, marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px" }}>Connected accounts</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { icon: I.linkedin, name: "LinkedIn", st: "Connected · linkedin.com/in/satvikj", c: "teal", on: true },
                { icon: I.github, name: "GitHub", st: "Connected · for Pages hosting", c: "teal", on: true },
                { icon: I.globe, name: "Personal website", st: "Not connected", c: "outline", on: false },
              ].map(r => (
                <div key={r.name} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 14px", border: "1px solid var(--color-border)", borderRadius: 12 }}>
                  <Icon d={r.icon} size={20} style={{ color: r.on ? "var(--color-accent)" : "var(--color-muted)" }}/>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{r.name}</div>
                    <div style={{ fontSize: 12, color: "var(--color-muted)" }}>{r.st}</div>
                  </div>
                  <button className={`pill pill-${r.on ? "ghost" : "outline-teal"} pill-sm`}>{r.on ? "Disconnect" : "Connect"}</button>
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
    { c: "teal", t: "3 new roles matched today", s: "Razorpay, Zepto, Groww — all 79%+ fit", time: "Just now" },
    { c: "purple", t: "Your profile is ready", s: "All 47 highlights processed. Your matches just got sharper.", time: "1h ago" },
    { c: "pink", t: "Post went live", s: "\"Refund SLA automation shipped\" · already 47 reactions", time: "3h ago" },
    { c: "sage", t: "Interview prep reminder", s: "Your Razorpay round is in 3 days · 5 drills queued", time: "Yesterday" },
    { c: "gold", t: "Don't break your streak", s: "A 2-minute diary entry keeps the 4-day run alive.", time: "Yesterday" },
    { c: "teal", t: "PhonePe moved you to round 2", s: "Scheduled Apr 22 · application tracker updated", time: "2 days ago" },
    { c: "purple", t: "Cred resume draft timed out", s: "We saved your progress — pick up anytime.", time: "3 days ago" },
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
