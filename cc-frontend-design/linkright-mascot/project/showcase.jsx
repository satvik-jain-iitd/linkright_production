/* =========================================================================
   showcase.jsx — final board, reorganised for implementers.

   SECTION ORDER (logical, not chronological):
   ─────────────────────────────────────────────────────────────────────────
   00 · READ THIS FIRST  — crosswalk of what to change + stack decision
   01 · IMPLEMENT: FOUNDATION  — shell skeleton (B) + input triggers (C)
   02 · IMPLEMENT: STREAMING   — braille spinner + 191-verb pool (D)
   03 · IMPLEMENT: TOOL SURFACES  — tool cards (E) + permissions (F) + plan (G)
   04 · IMPLEMENT: CONFIG & COMMANDS  — settings (H) + slash (I) + polish (J)
   05 · PIP — THE MASCOT  — character bible + 18 poses + journey
   06 · PIP IN PLACES  — 8 future surfaces (IDE, git, web, email…)
   07 · ARCHIVE  — earlier design directions kept for reference
   ─────────────────────────────────────────────────────────────────────────
   The CC-true surfaces (sections 00–04) are the implementation spec.
   The ASCII direction (sections 05–07) is the mascot system + history.
   ========================================================================= */

function Showcase() {
  return (
    <DesignCanvas>

      {/* ═══════════════════════════════════════════════════════════════
          00 · READ THIS FIRST
          What changes from LR house style to CC-true, and which stack.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="read-first" title="00 · Read this first · implementation rulebook">
        <DCArtboard id="cc-crosswalk"
          label="Primitive crosswalk — what to change in 3 files"
          width={1480} height={1420}>
          <CCCrosswalkArtboard />
        </DCArtboard>
        <DCArtboard id="cc-stack"
          label="A · Stack decision — Python+Rich now, Bun+Ink target"
          width={1480} height={960}>
          <CCStackArtboard />
        </DCArtboard>
      </DCSection>

      {/* ═══════════════════════════════════════════════════════════════
          01 · IMPLEMENT: FOUNDATION
          The app shell skeleton and input trigger system.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="impl-foundation" title="01 · Implement: foundation · shell + input">
        <DCArtboard id="cc-skeleton"
          label="B · Shell skeleton — banner → committed log → live tail → input → status"
          width={1480} height={1100}>
          <CCSkeletonArtboard />
        </DCArtboard>
        <DCArtboard id="cc-input"
          label="C · Input triggers — / palette · @ picker · ! bash · multi-line"
          width={1480} height={1060}>
          <CCInputArtboard />
        </DCArtboard>
      </DCSection>

      {/* ═══════════════════════════════════════════════════════════════
          02 · IMPLEMENT: STREAMING
          Replace coral working-verb with braille spinner + 191 verbs.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="impl-streaming" title="02 · Implement: streaming · ⠋ braille + 191-verb pool">
        <DCArtboard id="cc-streaming"
          label="D · Braille spinner — 10 frames · 4s verb rotation · tip line"
          width={1480} height={1060}>
          <CCStreamingArtboard />
        </DCArtboard>
      </DCSection>

      {/* ═══════════════════════════════════════════════════════════════
          03 · IMPLEMENT: TOOL SURFACES
          Tool cards, permission prompts, and plan mode.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="impl-tools" title="03 · Implement: tool surfaces · cards · permissions · plan mode">
        <DCArtboard id="cc-tools"
          label="E · Tool cards — ● ⎿ diff subagent AskUserQuestion"
          width={1480} height={1200}>
          <CCToolCardsArtboard />
        </DCArtboard>
        <DCArtboard id="cc-perms"
          label="F · Permissions — 6 modes · radio prompt · PreToolUse veto"
          width={1480} height={1060}>
          <CCPermissionArtboard />
        </DCArtboard>
        <DCArtboard id="cc-plan"
          label="G · Plan mode — magenta banner · ExitPlanMode approval card"
          width={1480} height={1040}>
          <CCPlanModeArtboard />
        </DCArtboard>
      </DCSection>

      {/* ═══════════════════════════════════════════════════════════════
          04 · IMPLEMENT: CONFIG & COMMANDS
          Settings cascade, 8 hook events, slash palette, polish.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="impl-config" title="04 · Implement: config + commands · settings · hooks · slash · polish">
        <DCArtboard id="cc-settings"
          label="H · Settings + hooks — 8 lifecycle events + statusLine subprocess"
          width={1480} height={1100}>
          <CCSettingsArtboard />
        </DCArtboard>
        <DCArtboard id="cc-slash"
          label="I · Slash palette — built-in + skills + custom · 4 sources"
          width={1480} height={1060}>
          <CCSlashArtboard />
        </DCArtboard>
        <DCArtboard id="cc-polish"
          label="J · Polish — NO_COLOR · daltonized · interrupt · context budget"
          width={1480} height={1000}>
          <CCPolishArtboard />
        </DCArtboard>
      </DCSection>

      {/* ═══════════════════════════════════════════════════════════════
          05 · PIP — THE MASCOT
          Character bible, all 18 poses, career journey.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="pip-mascot" title="05 · Pip · the mascot · ASCII character system">
        <DCArtboard id="ascii-hero"
          label="Pip is 11 characters — the pitch"
          width={1480} height={880}>
          <AsciiHeroArtboard />
        </DCArtboard>
        <DCArtboard id="bible"
          label="Character bible — persona · anatomy · accent rules"
          width={1480} height={760}>
          <AsciiCharacterBibleArtboard />
        </DCArtboard>
        <DCArtboard id="ascii-poses"
          label="18 poses — all strings"
          width={1480} height={880}>
          <AsciiPosesArtboard />
        </DCArtboard>
        <DCArtboard id="journey"
          label="Pip across the career lifecycle"
          width={1480} height={540}>
          <AsciiJourneyArtboard />
        </DCArtboard>
        <DCArtboard id="primitives"
          label="LR-house CLI primitive atlas (reference)"
          width={1480} height={1180}>
          <PrimitivesAtlasArtboard />
        </DCArtboard>
      </DCSection>

      {/* ═══════════════════════════════════════════════════════════════
          06 · PIP IN PLACES
          8 future surfaces — all the same 4-line string.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="pip-future" title="06 · Pip in places · same string, 8 surfaces">
        <DCArtboard id="future-surfaces"
          label="VS Code · git hook · Chrome ext · dashboard · email · Slack · README · 404"
          width={1480} height={860}>
          <AsciiFutureFormsArtboard />
        </DCArtboard>
      </DCSection>

      {/* ═══════════════════════════════════════════════════════════════
          07 · ARCHIVE — earlier design directions
          Kept for context and comparison. Not implementation spec.
          ═══════════════════════════════════════════════════════════════ */}
      <DCSection id="archive" title="07 · Archive · earlier directions · reference only">
        <DCArtboard id="ascii-terminal"
          label="ASCII Pip beside the LINKRIGHT banner"
          width={1480} height={640}>
          <AsciiTerminalArtboard />
        </DCArtboard>
        <DCArtboard id="ascii-maintenance"
          label="Cost of one new state — ASCII vs blob"
          width={1480} height={880}>
          <AsciiMaintenanceArtboard />
        </DCArtboard>
        <DCArtboard id="ascii-compare"
          label="ASCII vs blob vs stickman — same six moments"
          width={1480} height={980}>
          <AsciiComparisonArtboard />
        </DCArtboard>
      </DCSection>

    </DesignCanvas>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<Showcase />);
