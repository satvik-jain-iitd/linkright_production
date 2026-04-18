"use client";

// Wave 2 / S21 — Notifications drawer.
// Right-drawer overlay from the bell icon in AppNav. Pillar-coloured dots per
// notification type. "Mark all read". Designed to never pull the user away
// from their current context — opens over the app, closes with esc/outside-click.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

type NotificationType =
  | "new_match"
  | "profile_ready"
  | "post_scheduled"
  | "post_sent"
  | "interview_reminder"
  | "streak"
  | "resume_done"
  | "resume_failed"
  | "diary_nudge"
  | string;

type Notification = {
  id: string;
  type: NotificationType;
  title: string;
  body?: string | null;
  payload?: Record<string, unknown> | null;
  read_at?: string | null;
  created_at: string;
};

// v2 audit: dot colour maps to PILLAR, not notification-type. Four zones:
// teal = Search & Apply, purple = Memory, sage = Prepare, pink = Broadcast.
// Streak + diary-nudge categories removed along with the streak mechanic.
const DOT_COLOR: Record<string, string> = {
  new_match: "bg-accent",         // teal · search-and-apply
  resume_done: "bg-accent",
  resume_failed: "bg-cta",        // coral · action-required error
  profile_ready: "bg-purple-500", // purple · memory layer
  linkedin_expired: "bg-purple-500",
  interview_reminder: "bg-sage-500",
  post_scheduled: "bg-pink-500",
  post_sent: "bg-pink-500",
  post_failed: "bg-cta",
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "Just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  if (d === 1) return "Yesterday";
  if (d < 7) return `${d} days ago`;
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

function deepLink(n: Notification): string | null {
  const p = n.payload ?? {};
  if (n.type === "new_match" && typeof p.job_id === "string")
    return `/resume/new?job_id=${encodeURIComponent(p.job_id)}`;
  if (n.type === "profile_ready") return "/onboarding/profile";
  if (n.type === "post_scheduled" || n.type === "post_sent")
    return "/dashboard/broadcast";
  if (n.type === "interview_reminder") return "/dashboard/interview-prep";
  if (n.type === "resume_done" && typeof p.job_id === "string")
    return `/resume/new?job=${encodeURIComponent(p.job_id)}`;
  if (n.type === "resume_failed") return "/dashboard";
  if (n.type === "linkedin_expired") return "/dashboard/profile";
  return null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onUnreadChange?: (count: number) => void;
}

export function NotificationsDrawer({ open, onClose, onUnreadChange }: Props) {
  const [items, setItems] = useState<Notification[]>([]);

  const load = useCallback(async () => {
    const res = await fetch("/api/notifications?limit=30", { cache: "no-store" });
    const body = await res.json();
    setItems(body.notifications ?? body.data ?? []);
    const unread = (body.notifications ?? body.data ?? []).filter(
      (n: Notification) => !n.read_at,
    ).length;
    onUnreadChange?.(unread);
  }, [onUnreadChange]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const markAllRead = async () => {
    await fetch("/api/notifications/mark-read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ all: true }),
    });
    setItems((list) => list.map((n) => ({ ...n, read_at: new Date().toISOString() })));
    onUnreadChange?.(0);
  };

  const markOne = async (id: string) => {
    await fetch("/api/notifications/mark-read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    setItems((list) =>
      list.map((n) =>
        n.id === id ? { ...n, read_at: new Date().toISOString() } : n,
      ),
    );
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex" aria-hidden={!open}>
      <div
        className="flex-1 bg-foreground/30"
        onClick={onClose}
        aria-hidden
      />
      <aside
        className="flex h-full w-full max-w-md flex-col border-l border-border bg-white shadow-2xl"
        role="dialog"
        aria-label="Notifications"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-base font-bold tracking-tight">Notifications</h2>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={markAllRead}
              className="text-xs font-semibold text-accent transition hover:text-accent-hover"
            >
              Mark all read
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="text-muted transition hover:text-foreground"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {items.length === 0 && (
            <div className="p-10 text-center">
              <p className="text-sm font-semibold">No notifications yet.</p>
              <p className="mt-1 text-xs text-muted">
                We&apos;ll nudge when something new matters.
              </p>
            </div>
          )}
          {items.map((n, i, arr) => {
              const dot = DOT_COLOR[n.type] ?? "bg-border";
              const link = deepLink(n);
              const isUnread = !n.read_at;
              const rowInner = (
                <div
                  className={
                    "flex items-start gap-3 px-5 py-3.5 transition" +
                    (i === arr.length - 1 ? "" : " border-b border-border") +
                    (isUnread ? " bg-accent/5" : "") +
                    " hover:bg-accent/[0.04]"
                  }
                >
                  <span
                    className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${dot}`}
                  />
                  <div className="flex-1">
                    <div className="text-sm font-semibold leading-snug">
                      {n.title}
                    </div>
                    {n.body && (
                      <div className="mt-0.5 text-xs leading-relaxed text-muted">
                        {n.body}
                      </div>
                    )}
                    <div className="mt-1.5 text-[11px] text-muted">
                      {timeAgo(n.created_at)}
                    </div>
                  </div>
                </div>
              );
              if (link) {
                return (
                  <Link
                    key={n.id}
                    href={link}
                    onClick={() => {
                      if (isUnread) markOne(n.id);
                      onClose();
                    }}
                  >
                    {rowInner}
                  </Link>
                );
              }
              return (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => {
                    if (isUnread) markOne(n.id);
                  }}
                  className="w-full text-left"
                >
                  {rowInner}
                </button>
              );
            })}
        </div>
      </aside>
    </div>
  );
}
