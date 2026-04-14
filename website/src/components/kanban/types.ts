export interface Application {
  id: string;
  company: string;
  role: string;
  status: string;
  jd_text: string | null;
  jd_url: string | null;
  location: string | null;
  salary_range: string | null;
  excitement: number | null;
  notes: string | null;
  tags: string[];
  applied_at: string | null;
  interview_at: string | null;
  deadline: string | null;
  created_at: string;
  updated_at: string;
  resume_jobs?: { id: string; status: string; version_number: number; is_active_version: boolean; created_at: string }[];
}

export interface JobScoreData {
  id: string;
  application_id: string;
  overall_grade: string;
  overall_score: number;
  dimensions: Record<string, {
    score: number;
    weight: number;
    reasoning: string;
    evidence: string[];
    gaps?: string[];
    hard_blockers?: string[];
  }>;
  role_archetype: string;
  recommended_action: string;
  skill_gaps: string[];
  hard_blockers: string[];
  keywords_matched: string[];
  legitimacy_tier: string;
}

export interface KanbanColumn {
  id: string;
  label: string;
  statuses: string[];
  color: string;
}

export const KANBAN_COLUMNS: KanbanColumn[] = [
  { id: "wishlist", label: "Wishlist", statuses: ["not_started"], color: "border-gray-300" },
  { id: "drafting", label: "Drafting", statuses: ["resume_draft"], color: "border-blue-300" },
  { id: "applied", label: "Applied", statuses: ["applied"], color: "border-indigo-300" },
  { id: "interviewing", label: "Interviewing", statuses: ["screening", "interview"], color: "border-purple-300" },
  { id: "offer", label: "Offer", statuses: ["offer"], color: "border-green-300" },
  { id: "closed", label: "Closed", statuses: ["accepted", "rejected", "withdrawn"], color: "border-gray-400" },
];

export function getColumnForStatus(status: string): string {
  for (const col of KANBAN_COLUMNS) {
    if (col.statuses.includes(status)) return col.id;
  }
  return "wishlist";
}

export function getStatusForColumn(columnId: string): string {
  const col = KANBAN_COLUMNS.find((c) => c.id === columnId);
  return col ? col.statuses[0] : "not_started";
}
