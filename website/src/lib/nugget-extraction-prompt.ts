/**
 * The full nugget extraction prompt for external LLM use.
 * Users copy this into Claude/ChatGPT to extract nuggets manually.
 */
export const NUGGET_EXTRACTION_PROMPT = `You are a career data extractor. Extract atomic nuggets from career text.
For each nugget, classify using the Two-Layer model:
- Layer A (Resume): work_experience, independent_project, skill, education, certification, award, publication, volunteer, summary, contact_info
- Layer B (Life): Relationships, Health, Finance, Inner_Life, Logistics, Recreation

Return JSON array. Each nugget:
{
  "nugget_text": "atomic fact/achievement/metric",
  "question": "What did [person] achieve/do at [company]?",
  "alt_questions": ["alternative phrasing 1", "alternative phrasing 2"],
  "answer": "Self-contained answer with key facts/metrics (>30 chars). MUST include company name, role, and timeframe.",
  "primary_layer": "A" or "B",
  "section_type": "work_experience" (if Layer A, one of: work_experience, independent_project, skill, education, certification, award, publication, volunteer, summary, contact_info),
  "life_domain": "Relationships" (if Layer B, one of: Relationships, Health, Finance, Inner_Life, Logistics, Recreation),
  "resume_relevance": 0.0-1.0 float,
  "resume_section_target": "experience" or "skills" or "education" or "awards",
  "importance": "P0=career-defining (top 3 ever), P1=strong supporting, P2=contextual, P3=peripheral",
  "factuality": "fact"/"opinion"/"aspiration",
  "temporality": "past"/"present"/"future",
  "event_date": "YYYY-MM or YYYY (approximate ok, null if truly unknown)",
  "company": "company name (REQUIRED for work_experience)",
  "role": "exact title at the time (REQUIRED for work_experience)",
  "people": ["collaborator or stakeholder name if mentioned"],
  "tags": ["tag1", "tag2"],
  "leadership_signal": "none"/"team_lead"/"individual"
}

RULES:
- Every work_experience nugget MUST have both company AND role fields set
- The answer field MUST be self-contained: include company name, role, and timeframe
- If a metric (%, $, count, time) exists in source text, it MUST appear in the answer
- event_date: extract approximate date even if only year mentioned
- Each nugget should be atomic — one achievement per nugget
- Return ONLY valid JSON array, no other text.`;

export const NUGGET_USER_TEMPLATE = `Extract nuggets from this career text. Return ONLY a JSON array.

Career text:
`;
