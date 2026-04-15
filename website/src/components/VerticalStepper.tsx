"use client";

interface SubStep {
  label: string;
  done: boolean;
}

interface StepDef {
  label: string;
  subSteps?: SubStep[];
}

interface VerticalStepperProps {
  steps: StepDef[];
  currentStep: number;
  onStepClick?: (index: number) => void; // [PSA5-8y3.3.1.1]
}

export function VerticalStepper({ steps, currentStep, onStepClick }: VerticalStepperProps) {
  return (
    <>
      {/* Desktop vertical sidebar */}
      <aside className="hidden w-60 shrink-0 border-r border-border bg-surface/50 px-6 py-8 lg:block" data-testid="resume-wizard-step-indicator">
        <nav>
          {steps.map((s, i) => {
            const isDone = i < currentStep;
            const isActive = i === currentStep;
            const isLast = i === steps.length - 1;

            return (
              <div key={s.label} className="relative">
                {/* Connecting line (behind the dot) */}
                {!isLast && (
                  <div
                    className={`absolute left-3 top-6 w-px ${
                      isDone ? "bg-accent" : "bg-border"
                    }`}
                    style={{
                      height:
                        isActive && s.subSteps && s.subSteps.length > 0
                          ? `calc(100% - 0.75rem)`
                          : "calc(100% - 0.75rem)",
                    }}
                  />
                )}

                {/* Step row — done steps are clickable if onStepClick provided [PSA5-8y3.3.1.1] */}
                {isDone && onStepClick ? (
                  <button
                    onClick={() => onStepClick(i)}
                    className="relative flex w-full items-center gap-3 py-2.5 cursor-pointer hover:opacity-80 transition-opacity"
                  >
                    <div
                      className="relative z-10 flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold transition-colors bg-accent text-white"
                    >
                      {"\u2713"}
                    </div>
                    <span className="text-sm text-foreground">{s.label}</span>
                  </button>
                ) : (
                  <div className="relative flex items-center gap-3 py-2.5">
                    <div
                      className={`relative z-10 flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                        isDone
                          ? "bg-accent text-white"
                          : isActive
                            ? "bg-accent text-white ring-2 ring-accent/30 ring-offset-2"
                            : "bg-border text-muted"
                      }`}
                    >
                      {isDone ? "\u2713" : i + 1}
                    </div>
                    <span
                      className={`text-sm ${
                        isActive
                          ? "font-medium text-foreground"
                          : isDone
                            ? "text-foreground"
                            : "text-muted"
                      }`}
                    >
                      {s.label}
                    </span>
                  </div>
                )}

                {/* Sub-steps (expanded when active) */}
                {isActive && s.subSteps && s.subSteps.length > 0 && (
                  <div className="relative ml-3 border-l border-border pl-5 pb-1">
                    {s.subSteps.map((sub) => (
                      <div
                        key={sub.label}
                        className="flex items-center gap-2 py-1.5"
                      >
                        <div
                          className={`h-1.5 w-1.5 rounded-full ${
                            sub.done ? "bg-accent" : "bg-border"
                          }`}
                        />
                        <span
                          className={`text-xs ${
                            sub.done ? "text-foreground" : "text-muted"
                          }`}
                        >
                          {sub.label}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </aside>

      {/* Mobile horizontal top bar */}
      <div className="flex items-center justify-center gap-3 border-b border-border bg-surface/50 px-4 py-3 lg:hidden" data-testid="resume-wizard-step-indicator-mobile">
        {steps.map((s, i) => {
          const isDone = i < currentStep;
          const isActive = i === currentStep;
          const isLast = i === steps.length - 1;
          return (
            <div key={s.label} className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${
                    isDone
                      ? "bg-accent text-white"
                      : isActive
                        ? "bg-accent text-white ring-2 ring-accent/30 ring-offset-2"
                        : "bg-border text-muted"
                  }`}
                >
                  {isDone ? "\u2713" : i + 1}
                </div>
                {isActive && (
                  <span className="text-sm font-medium text-foreground">
                    {s.label}
                  </span>
                )}
              </div>
              {!isLast && (
                <div
                  className={`h-px w-6 sm:w-8 ${isDone ? "bg-accent" : "bg-border"}`}
                />
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
