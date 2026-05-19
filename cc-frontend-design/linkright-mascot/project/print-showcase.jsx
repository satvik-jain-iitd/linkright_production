/* =========================================================================
   print-showcase.jsx — print-ready version of the showcase.
   Renders every artboard in its natural size on its own page, paginated
   via CSS @page, with auto-print on font-ready.
   ========================================================================= */

function PrintPage({ width, height, children, label }) {
  return (
    <div className="print-page" style={{ width, height }}>
      {label && (
        <div className="print-label">{label}</div>
      )}
      <div className="print-content" style={{ width, height }}>
        {children}
      </div>
    </div>
  );
}

function PrintShowcase() {
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try { await document.fonts.ready; } catch {}
      // Give the artboards' own animations one tick to render initial state.
      setTimeout(() => { if (!cancelled) window.print(); }, 800);
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      <PrintPage width={1480} height={1100} label="00 · Designer's critique">
        <CritiqueArtboard />
      </PrintPage>
      <PrintPage width={1480} height={880}  label="01 · Hero">
        <HeroArtboard />
      </PrintPage>
      <PrintPage width={1480} height={460}  label="02 · Career journey">
        <JourneyArtboard />
      </PrintPage>
      <PrintPage width={720}  height={880}  label="03 · Persona">
        <PersonaArtboard />
      </PrintPage>
      <PrintPage width={720}  height={880}  label="04 · Anatomy">
        <AnatomyArtboard />
      </PrintPage>
      <PrintPage width={1480} height={720}  label="05 · Voice">
        <VoiceArtboard />
      </PrintPage>
      <PrintPage width={1480} height={980}  label="06 · CLI behaviour atlas">
        <BehavioursArtboard />
      </PrintPage>
      <PrintPage width={1480} height={720}  label="07 · Sprite sheet">
        <SpriteSheetArtboard />
      </PrintPage>
      <PrintPage width={1480} height={720}  label="08 · Direction options">
        <VariantsArtboard />
      </PrintPage>
      <PrintPage width={1480} height={880}  label="09 · Future forms">
        <FutureFormsArtboard />
      </PrintPage>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<PrintShowcase />);
