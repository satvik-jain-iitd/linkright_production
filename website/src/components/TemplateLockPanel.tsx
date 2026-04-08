"use client";

interface TemplateLockPanelProps {
  lockedSections: string[];
  onToggle: (section: string) => void;
}

const LOCKABLE_SECTIONS = [
  { id: "education", label: "Education", icon: "🎓", description: "Degrees, institutions, years" },
  { id: "skills", label: "Skills", icon: "⚡", description: "Technical and soft skills" },
  { id: "certifications", label: "Certifications", icon: "📜", description: "Professional certifications" },
  { id: "interests", label: "Interests", icon: "🎯", description: "Hobbies and interests" },
  { id: "achievements", label: "Achievements", icon: "🏆", description: "Scholastic and awards" },
];

export function TemplateLockPanel({ lockedSections, onToggle }: TemplateLockPanelProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="font-semibold mb-1">Section Locks</h3>
      <p className="text-sm text-muted mb-3">Locked sections are frozen — not regenerated on next resume</p>
      <div className="space-y-2">
        {LOCKABLE_SECTIONS.map((section) => {
          const isLocked = lockedSections.includes(section.id);
          return (
            <button
              key={section.id}
              onClick={() => onToggle(section.id)}
              className={`w-full flex items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                isLocked
                  ? "border-accent/50 bg-accent/10 text-foreground"
                  : "border-border bg-transparent text-muted hover:text-foreground"
              }`}
            >
              <span>{section.icon}</span>
              <div className="flex-1">
                <div className="font-medium">{section.label}</div>
                <div className="text-xs opacity-70">{section.description}</div>
              </div>
              <span className="text-xs">{isLocked ? "🔒 Locked" : "🔓 Unlocked"}</span>
            </button>
          );
        })}
        {/* [PSA5-8y3.4.1.1] Experience not lockable — tooltip explaining why */}
        <div className="flex items-center gap-3 rounded-lg border border-border/40 bg-muted/5 px-3 py-2.5 opacity-60">
          <span className="text-base">💼</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-muted">Experience</p>
            <p className="text-xs text-muted/70 mt-0.5">Re-tailored for each job description to maximize relevance</p>
          </div>
          <span className="text-xs text-muted whitespace-nowrap">Not lockable</span>
        </div>
      </div>
    </div>
  );
}
