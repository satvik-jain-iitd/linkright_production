"use client";

import { useState } from "react";

interface ConfirmDenyButtonsProps {
  originalAnswer: string;
  onConfirm: () => void;
  onCorrect: (correctedText: string) => void;
  disabled?: boolean;
}

export function ConfirmDenyButtons({
  originalAnswer,
  onConfirm,
  onCorrect,
  disabled = false,
}: ConfirmDenyButtonsProps) {
  const [editing, setEditing] = useState(false);
  const [correctionText, setCorrectionText] = useState(originalAnswer);

  if (editing) {
    return (
      <div className="mt-3 space-y-2">
        <textarea
          value={correctionText}
          onChange={(e) => setCorrectionText(e.target.value)}
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
          rows={3}
          placeholder="Edit your answer..."
        />
        <div className="flex gap-2">
          <button
            onClick={() => {
              if (correctionText.trim()) {
                onCorrect(correctionText.trim());
                setEditing(false);
              }
            }}
            disabled={disabled || !correctionText.trim()}
            className="flex-1 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Submit correction
          </button>
          <button
            onClick={() => {
              setEditing(false);
              setCorrectionText(originalAnswer);
            }}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted hover:bg-surface-hover transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 flex gap-2">
      <button
        onClick={onConfirm}
        disabled={disabled}
        className="flex-1 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Yes, correct
      </button>
      <button
        onClick={() => setEditing(true)}
        disabled={disabled}
        className="flex-1 rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        No, correct it
      </button>
    </div>
  );
}
