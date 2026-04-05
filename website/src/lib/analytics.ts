/**
 * Analytics event tracking for Sync resume engine.
 *
 * Events map to PostHog dashboards:
 * - Growth: user_signup, page_view
 * - Funnel: resume_started → resume_completed → resume_downloaded → credit_purchased
 * - Quality: width_measurement, page_fit_check, ai_audit_result
 * - Revenue: credit_purchased
 */

import posthog from "posthog-js";

// Type-safe event tracking
type SyncEvent =
  | { event: "user_signup"; properties: { auth_provider: string } }
  | {
      event: "resume_started";
      properties: { template: string; jd_word_count: number };
    }
  | {
      event: "resume_completed";
      properties: {
        duration_seconds: number;
        bullet_count: number;
        trim_rounds_avg: number;
      };
    }
  | { event: "resume_downloaded"; properties: { format: "html" | "pdf" } }
  | {
      event: "credit_purchased";
      properties: { pack_type: string; amount_inr: number };
    }
  | {
      event: "application_qa_used";
      properties: { question_count: number };
    }
  | {
      event: "width_measurement";
      properties: {
        fill_pct: number;
        pass_fail: "PASS" | "TOO_SHORT" | "OVERFLOW";
        attempts: number;
      };
    }
  | {
      event: "page_fit_check";
      properties: { fits: boolean; overflow_px: number };
    }
  | {
      event: "ai_audit_result";
      properties: { violations: number; structural_issues: number };
    }
  | {
      event: "nps_submitted";
      properties: { score: number; feedback?: string };
    }
  | {
      event: "survey_submitted";
      properties: {
        would_pay: "yes" | "no" | "maybe";
        price_range: string;
        feature_count: number;
        has_feedback: boolean;
        is_authenticated: boolean;
      };
    };

export function track(eventData: SyncEvent) {
  if (typeof window !== "undefined" && posthog.__loaded) {
    posthog.capture(eventData.event, eventData.properties);
  }
}

export function identifyUser(userId: string, traits?: Record<string, unknown>) {
  if (typeof window !== "undefined" && posthog.__loaded) {
    posthog.identify(userId, traits);
  }
}
