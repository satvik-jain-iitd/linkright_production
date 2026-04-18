// BUILD phase: Screens 4-7 (Resume upload, Profile highlights, Highlight modal, Preferences)

function Screen04_Upload() {
  return (
    <div className="frame" id="s04">
      <Chrome url="linkright.in/onboarding" />
      <div className="frame-body">
        <div style={{ padding: "18px 48px", borderBottom: "1px solid var(--color-border)", background: "#fff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Wordmark size={20} />
          <div className="steps">
            <span className="step active">1 Resume</span><span className="sep"/>
            <span className="step">2 Profile</span><span className="sep"/>
            <span className="step">3 Preferences</span><span className="sep"/>
            <span className="step">4 First match</span>
          </div>
          <span className="muted" style={{ fontSize: 13 }}>Skip →</span>
        </div>

        {/* Split layout, after parse */}
        <div style={{ padding: "32px 48px 48px", maxWidth: 1200, marginInline: "auto" }}>
          <div style={{ marginBottom: 20 }}>
            <div className="eyebrow">Step 1 of 4 · this is the only required input</div>
            <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: "-0.015em", margin: "8px 0 6px" }}>Here's what we understood from your resume.</h1>
            <p style={{ color: "var(--color-muted)", margin: 0, fontSize: 15 }}>Edit anything that's off.</p>
          </div>

          {/* Resume loaded chip */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", border: "1px solid var(--color-border)", borderRadius: 12, background: "#fff", marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div className="iconTile" style={{ width: 36, height: 36 }}><Icon d={I.document} size={18}/></div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>Satvik_Jain_Resume_2026.pdf</div>
                <div style={{ fontSize: 12, color: "var(--color-muted)" }}>Parsed in 4.2s · 247 KB</div>
              </div>
            </div>
            <button className="pill pill-ghost pill-sm">Swap resume</button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            {/* Structured outline */}
            <div className="card card-lg">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Outline</h3>
                <span className="chip chip-outline">Click any field to edit</span>
              </div>

              <div style={{ marginBottom: 18 }}>
                <div style={{ fontSize: 11, color: "var(--color-muted)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>Experience</div>
                {[
                  { co: "American Express", role: "Product Manager", dates: "Jul 2024, Present", proj: ["Returns flow redesign (18% lift)", "Refund SLA automation", "Merchant onboarding v3"] },
                  { co: "Sprinklr", role: "Senior PM, Enterprise", dates: "2021, 2024", proj: ["36 customer implementations", "Content moderation launch"] },
                ].map(e => (
                  <div key={e.co} style={{ padding: "12px 14px", borderLeft: "2px solid var(--color-accent)", background: "rgba(15,190,175,0.04)", borderRadius: "0 10px 10px 0", marginBottom: 8 }}>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{e.role} <span style={{ color: "var(--color-muted)", fontWeight: 400 }}>· {e.co}</span></div>
                    <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>{e.dates}</div>
                    <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {e.proj.map(p => <span key={p} className="chip chip-teal">{p}</span>)}
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 11, color: "var(--color-muted)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>Education</div>
                <div style={{ fontSize: 13 }}>B.Tech, Computer Science · <span className="muted">IIT Delhi · 2019</span></div>
              </div>

              <div>
                <div style={{ fontSize: 11, color: "var(--color-muted)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>Skills</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {["Product strategy", "SQL", "A/B testing", "Roadmapping", "Figma", "Stakeholder management"].map(s => <span key={s} className="chip">{s}</span>)}
                </div>
              </div>
            </div>

            {/* First-person narration */}
            <div className="card card-lg" style={{ background: "linear-gradient(180deg, #FDF6F0 0%, #FFFFFF 60%)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div>
                  <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Your story, in your words</h3>
                  <p style={{ fontSize: 12, color: "var(--color-muted)", margin: "2px 0 0" }}>Rewrite anything that doesn't sound like you.</p>
                </div>
              </div>

              <div style={{ fontSize: 13.5, lineHeight: 1.7, color: "var(--color-foreground)" }}>
                <p style={{ margin: "0 0 12px", borderLeft: "2px solid rgba(139,92,246,0.3)", paddingLeft: 12 }}>
                  <b>At Amex,</b> I led a 12-person team redesigning the returns flow for Indian merchants. The core problem was a 40% drop-off at the reason-code step. I ran 8 user interviews, rebuilt the UX around three primary reasons instead of fourteen, and shipped the rollout in six weeks. <b>The outcome was an 18% lift in completion and a 22% reduction in support tickets.</b>
                </p>
                <p style={{ margin: "0 0 12px", borderLeft: "2px solid rgba(139,92,246,0.3)", paddingLeft: 12 }}>
                  <b>Before that at Sprinklr,</b> I was the PM for enterprise content moderation. My favourite ship was the real-time policy engine. I spent three weeks embedded with the Walmart legal team to understand their escalation tree, then built a decision layer that cut moderator overhead by 34%.
                </p>
                <p style={{ margin: 0, color: "var(--color-muted)", fontStyle: "italic" }}>
                  + 3 more roles expanded below…
                </p>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24 }}>
            <p style={{ fontSize: 13, color: "var(--color-muted)", margin: 0 }}>Backend keeps learning in the background. You don't need to wait.</p>
            <button className="pill pill-cta pill-lg">Save and continue <Icon d={I.arrowRight} size={16}/></button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen05_Profile() {
  const highlights = [
    { type: "role", src: "from your Amex role", t: "Led 12-person redesign of the returns flow", d: "18% conversion lift, 22% fewer support tickets" },
    { type: "role", src: "from your Amex role", t: "Shipped refund SLA automation", d: "Cut merchant wait time from 5 days to 8 hours" },
    { type: "role", src: "from your Sprinklr role", t: "36 enterprise implementations", d: "Walmart, Samsung, Cisco, Marriott, Shell" },
    { type: "role", src: "from your Sprinklr role", t: "Built the real-time policy engine", d: "Cut moderator overhead by 34%" },
    { type: "project", src: "from your projects", t: "Open-sourced a Chrome extension", d: "LinkedIn filter for applied roles. 2k active users." },
    { type: "education", src: "from your education", t: "IIT Delhi, CS Dept Gold Medal", d: "Class of 2019, top 0.5% of cohort" },
    { type: "skill", src: "from your skills", t: "SQL, deep proficiency", d: "Window functions, query optimization, migration work" },
    { type: "skill", src: "from your certifications", t: "Pragmatic Marketing PMC-III", d: "Product-market-fit specialisation" },
    { type: "project", src: "from your early projects", t: "Built a college feedback platform", d: "Adopted by 4 IITs, handled 40k student responses" },
    { type: "skill", src: "from your skills", t: "A/B testing with statistical rigor", d: "CUPED variance reduction, stratified sampling" },
    { type: "role", src: "from your Sprinklr role", t: "Led Walmart legal escalation rebuild", d: "3 weeks embedded with their team" },
    { type: "skill", src: "from your languages", t: "Hindi, English, basic French", d: "Fluent presenter in first two" },
  ];
  return (
    <div className="frame" id="s05">
      <Chrome url="linkright.in/onboarding/profile" />
      <div className="frame-body">
        <div style={{ padding: "18px 48px", borderBottom: "1px solid var(--color-border)", background: "#fff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Wordmark size={20} />
          <div className="steps">
            <span className="step done">1 Resume ✓</span><span className="sep"/>
            <span className="step active">2 Profile</span><span className="sep"/>
            <span className="step">3 Preferences</span><span className="sep"/>
            <span className="step">4 First match</span>
          </div>
          <span className="muted" style={{ fontSize: 13 }}>Skip. I'll add later.</span>
        </div>

        <div style={{ padding: "32px 48px 64px", maxWidth: 1200, marginInline: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
            <div style={{ maxWidth: 640 }}>
              <div className="eyebrow" style={{ color: "#8B5CF6" }}>Your profile</div>
              <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: "-0.015em", margin: "8px 0 6px" }}>Here's what stood out from your resume.</h1>
              <p style={{ color: "var(--color-muted)", margin: 0, fontSize: 15 }}>Click any card to add more depth.</p>
            </div>
            <div style={{ textAlign: "right" }}>
              <button className="pill pill-cta">Continue to find jobs <Icon d={I.arrowRight} size={14}/></button>
              <p style={{ fontSize: 12, color: "var(--color-muted)", margin: "8px 0 0" }}>You can always come back to this.</p>
            </div>
          </div>

          {/* Progress strip */}
          <div className="card" style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 18px", marginBottom: 20, background: "rgba(139,92,246,0.05)", borderColor: "rgba(139,92,246,0.2)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#5A36AB", fontSize: 13, fontWeight: 600 }}>
              <Icon d={I.sparkles} size={16} />Getting your profile ready
            </div>
            <div style={{ flex: 1, height: 6, background: "rgba(139,92,246,0.15)", borderRadius: 9999, overflow: "hidden" }}>
              <div style={{ width: "36%", height: "100%", background: "#8B5CF6", borderRadius: 9999 }} />
            </div>
            <span style={{ fontSize: 13, color: "var(--color-muted)" }}>12 of 33 highlights processed</span>
          </div>

          {/* Grid of highlight cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
            {highlights.map((h, i) => (
              <div key={i} className="card" style={{ padding: 18, cursor: "default", position: "relative" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                  <span className="chip" style={{ background: "#F7FAFC", color: "var(--color-muted)", border: "1px solid var(--color-border)", fontWeight: 500 }}>{h.src}</span>
                  <Icon d={I.plus} size={14} style={{ color: "var(--color-muted)" }} />
                </div>
                <h4 style={{ fontSize: 14, fontWeight: 600, margin: "10px 0 6px", lineHeight: 1.35 }}>{h.t}</h4>
                <p style={{ fontSize: 12.5, color: "var(--color-muted)", margin: 0, lineHeight: 1.5 }}>{h.d}</p>
              </div>
            ))}
          </div>

          {/* Bulk upload soft CTA */}
          <div style={{ marginTop: 28, padding: "14px 18px", border: "1px dashed var(--color-border)", borderRadius: 12, display: "flex", justifyContent: "space-between", alignItems: "center", background: "#fff" }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>Have everything written up already?</div>
              <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>Upload a career file. We'll fold it into your profile.</div>
            </div>
            <button className="pill pill-ghost pill-sm">Upload a file →</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen06_HighlightModal() {
  return (
    <div className="frame" id="s06">
      <Chrome url="linkright.in/onboarding/profile" />
      <div className="frame-body" style={{ position: "relative", minHeight: 700, background: "#FAFBFC" }}>
        {/* Dimmed page behind */}
        <div style={{ position: "absolute", inset: 0, background: "rgba(26,32,44,0.45)" }} />

        {/* Modal */}
        <div style={{ position: "absolute", top: 60, left: "50%", transform: "translateX(-50%)", width: 640, background: "#fff", borderRadius: 20, boxShadow: "0 24px 64px rgba(74,46,146,0.35)", overflow: "hidden", border: "1px solid rgba(139,92,246,0.2)" }}>
          {/* Header */}
          <div style={{ padding: "20px 24px", borderBottom: "1px solid rgba(139,92,246,0.18)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "linear-gradient(180deg, rgba(139,92,246,0.06), transparent)" }}>
            <div>
              <span className="chip" style={{ background: "rgba(139,92,246,0.12)", color: "#5A36AB", border: "1px solid rgba(139,92,246,0.3)" }}>from your Amex role</span>
              <h3 style={{ fontSize: 16, fontWeight: 600, margin: "10px 0 0", letterSpacing: "-0.01em" }}>Led 12-person redesign of the returns flow</h3>
            </div>
            <button style={{ width: 32, height: 32, border: "none", background: "transparent", color: "var(--color-muted)", cursor: "default" }}><Icon d={I.x}/></button>
          </div>

          {/* Tree of follow-ups */}
          <div style={{ padding: 24, background: "linear-gradient(180deg, rgba(139,92,246,0.04), rgba(139,92,246,0.01))" }}>
            <p style={{ fontSize: 13, color: "var(--color-muted)", margin: "0 0 20px", display: "flex", alignItems: "center", gap: 6 }}><span style={{ color: "#5A36AB" }}>✦</span> Three quick questions. Answer any, all, or none.</p>

            {[
              { q: "What was the biggest challenge?", hint: "The thing that almost killed the ship", filled: "The 40% drop-off at the reason-code step. Users couldn't map their issue to our taxonomy.", done: true },
              { q: "What outcome are you proudest of?", hint: "Metric, or qualitative. Either works.", filled: "", done: false, open: true },
              { q: "Who else worked on this with you?", hint: "Names are optional, roles are helpful", filled: "", done: false },
            ].map((f, i) => (
              <div key={i} style={{ position: "relative", paddingLeft: 24, marginBottom: 16 }}>
                {/* Tree connector */}
                <div style={{ position: "absolute", left: 7, top: 14, bottom: -16, width: 1, background: "var(--color-border)", display: i === 2 ? "none" : "block" }} />
                <div style={{ position: "absolute", left: 0, top: 8, width: 16, height: 16, borderRadius: "50%", background: f.done ? "#8B5CF6" : "#fff", border: f.done ? "none" : "1px solid rgba(139,92,246,0.3)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 10 }}>
                  {f.done ? "✓" : ""}
                </div>
                <div className="card" style={{ padding: 16, borderColor: f.open ? "#8B5CF6" : undefined, boxShadow: f.open ? "0 0 0 3px rgba(139,92,246,0.12)" : undefined }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>{f.q}</div>
                  <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 2 }}>{f.hint}</div>
                  {f.filled && <p style={{ fontSize: 13, color: "var(--color-foreground)", marginTop: 10, lineHeight: 1.55, background: "rgba(139,92,246,0.07)", padding: 10, borderRadius: 8, marginBottom: 0, borderLeft: "2px solid #8B5CF6" }}>{f.filled}</p>}
                  {f.open && (
                    <div style={{ marginTop: 10 }}>
                      <textarea disabled placeholder="A few sentences is plenty…" style={{ width: "100%", padding: "10px 12px", border: "1px solid rgba(139,92,246,0.3)", borderRadius: 8, fontSize: 13, fontFamily: "inherit", resize: "none", height: 68, background: "#fff" }} />
                      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
                        <button className="pill pill-ghost pill-sm">Skip</button>
                        <button className="pill pill-sm" style={{ background: "#8B5CF6", color: "#fff", border: "none" }}>Save</button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div style={{ padding: "14px 24px", background: "#FAF7FF", borderTop: "1px solid rgba(139,92,246,0.18)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#5A36AB", fontWeight: 500 }}>1 of 3 answered</span>
            <button className="pill pill-sm" style={{ background: "#8B5CF6", color: "#fff", border: "none" }}>Done</button>
          </div>
        </div>

        {/* Toast */}
        <div style={{ position: "absolute", bottom: 28, right: 28, background: "#fff", border: "1px solid rgba(139,92,246,0.3)", borderRadius: 12, padding: "12px 16px", display: "flex", gap: 10, alignItems: "center", boxShadow: "0 12px 32px rgba(0,0,0,0.12)", maxWidth: 340, zIndex: 30 }}>
          <div className="iconTile iconTile-purple" style={{ width: 32, height: 32 }}><Icon d={I.sparkles} size={16}/></div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Saved to your profile</div>
            <div style={{ fontSize: 12, color: "var(--color-muted)" }}>We'll pull from this when you apply.</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Screen07_Preferences() {
  return (
    <div className="frame" id="s07">
      <Chrome url="linkright.in/onboarding/preferences" />
      <div className="frame-body">
        <div style={{ padding: "18px 48px", borderBottom: "1px solid var(--color-border)", background: "#fff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Wordmark size={20} />
          <div className="steps">
            <span className="step done">1 ✓</span><span className="sep"/>
            <span className="step done">2 ✓</span><span className="sep"/>
            <span className="step active">3 Preferences</span><span className="sep"/>
            <span className="step">4 First match</span>
          </div>
          <span className="muted" style={{ fontSize: 13 }}>I'll decide later →</span>
        </div>

        <div style={{ padding: "40px 48px 56px", maxWidth: 820, marginInline: "auto" }}>
          <div className="eyebrow">One minute, then we show you roles.</div>
          <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: "-0.015em", margin: "8px 0 28px" }}>What kind of role are you actually looking for?</h1>

          <div className="card card-lg" style={{ padding: 28 }}>
            <div style={{ marginBottom: 22 }}>
              <label style={{ fontSize: 13, fontWeight: 600 }}>Target roles <span style={{ color: "var(--color-cta)" }}>*</span></label>
              <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>Multi-select. We'll match against all of them.</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                {[
                  ["Senior Product Manager", true],
                  ["Principal PM", true],
                  ["Group Product Manager", false],
                  ["Product Lead", true],
                  ["Director of Product", false],
                ].map(([t, on]) => (
                  <span key={t} className={on ? "chip chip-teal" : "chip chip-outline"} style={{ padding: "6px 12px", fontSize: 12 }}>{t} {on && "✕"}</span>
                ))}
                <span className="chip chip-outline" style={{ padding: "6px 12px", fontSize: 12, color: "var(--color-muted)" }}>+ add another</span>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 22 }}>
              <div>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Location preference</label>
                <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
                  {[["Remote", false], ["Hybrid", true], ["Onsite", false], ["Any", false]].map(([t, on]) => (
                    <span key={t} className={on ? "chip chip-teal" : "chip chip-outline"} style={{ padding: "6px 12px", fontSize: 12 }}>{t}</span>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Cities</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                  {[["Bangalore", true], ["Delhi NCR", true], ["Remote-India", true], ["Mumbai", false]].map(([t, on]) => (
                    <span key={t} className={on ? "chip chip-teal" : "chip chip-outline"} style={{ padding: "6px 12px", fontSize: 12 }}>{t} {on && "✕"}</span>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 22 }}>
              <div>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Company stage</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                  {[["Seed", false], ["Series A, B", true], ["Series C+", true], ["Public", false]].map(([t, on]) => (
                    <span key={t} className={on ? "chip chip-teal" : "chip chip-outline"} style={{ padding: "6px 12px", fontSize: 12 }}>{t}</span>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ fontSize: 13, fontWeight: 600 }}>Notice period</label>
                <div style={{ marginTop: 10 }}>
                  <select disabled style={{ width: "100%", padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: 10, background: "#fff", fontSize: 14, fontFamily: "inherit" }}>
                    <option>60 days</option>
                  </select>
                </div>
              </div>
            </div>

            <div>
              <label style={{ fontSize: 13, fontWeight: 600 }}>Compensation target</label>
              <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>Annual CTC · ₹ lakhs. Hidden from recruiters.</div>
              <div style={{ display: "flex", gap: 10, marginTop: 10, alignItems: "center" }}>
                <input disabled defaultValue="45" style={{ width: 120, padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: 10, background: "#fff", fontSize: 14, fontFamily: "inherit" }} />
                <span style={{ color: "var(--color-muted)" }}>to</span>
                <input disabled defaultValue="70" style={{ width: 120, padding: "10px 14px", border: "1px solid var(--color-border)", borderRadius: 10, background: "#fff", fontSize: 14, fontFamily: "inherit" }} />
                <span style={{ color: "var(--color-muted)", fontSize: 13 }}>L / year</span>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24 }}>
            <button className="pill pill-ghost"><Icon d={I.arrowLeft} size={14}/> Back</button>
            <button className="pill pill-cta pill-lg">Search &amp; apply <Icon d={I.arrowRight} size={16}/></button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Screen04_Upload, Screen05_Profile, Screen06_HighlightModal, Screen07_Preferences });
