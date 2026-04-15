# Goal: Flex — Social Media Automation Agency

Build a multi-agent social media automation agency that orchestrates end-to-end content creation, scheduling, and publishing across LinkedIn, X (Twitter), YouTube, Instagram, and Facebook. Uses AI agents with multi-agent orchestration for each stage of the pipeline. Publishing and scheduling are handled via Postiz integration.

## Content Ideation & Research
- AI agent that monitors trending topics, industry news, and user's career/professional context
- Ideation scoring system to prioritize content opportunities (relevance, timeliness, audience fit)
- Content brief generation with suggested angles, hooks, and target platform
- Integration with LifeOS for authentic content sourcing from career achievements and learnings

## Content Drafting & Writing
- Multi-agent drafting: specialist agents per platform (LinkedIn long-form, X threads, YouTube scripts, Instagram captions, Facebook posts)
- Platform-specific formatting rules (LinkedIn staircase format, X 280-char limit, YouTube description SEO)
- Tone and voice consistency engine — learns user's writing style from past posts
- Draft versioning with A/B variant generation

## Review & Editing Pipeline
- QA agent for grammar, readability (FK Grade 7 target), and brand voice compliance
- Pixel-perfect preview rendering per platform before approval
- Human-in-the-loop approval checkpoint — nothing publishes without user sign-off
- Feedback loop: user edits feed back into the style model

## Publishing & Scheduling via Postiz
- Postiz integration for cross-platform publishing (LinkedIn, X, YouTube, Instagram, Facebook)
- Intelligent scheduling: optimal posting times per platform based on audience analytics
- Queue management with drag-and-drop reordering
- Auto-retry on publish failures with notification

## Analytics & Optimization
- Post-publish performance tracking (impressions, engagement, clicks, shares)
- Per-platform analytics dashboard
- Content performance patterns: which topics, formats, times perform best
- Automated recommendations for future content based on historical performance

## Agent Orchestration
- Coordinator agent that routes work through the pipeline stages
- Parallel agent execution where stages are independent
- Agent-to-agent communication via message passing
- Checkpoint system: each stage produces artifacts the next stage consumes
- Error handling: failed agent tasks get retried or escalated to human
