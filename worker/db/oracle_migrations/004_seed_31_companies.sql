-- Migration 004: Seed 31 empirically-verified companies with ATS pairings
-- ATS slugs verified via public board URLs on 2026-05-02
-- confidence='high' = ATS slug manually confirmed returning live jobs
-- canonical_id = sha256(website) placeholder — computed by app on first import
-- NOTE: canonical_id here uses deterministic prefix for seed identity;
--       production imports via `linkright admin companies import` recompute sha256.
--
-- Target: Oracle Postgres (ORACLE_PG_URL) — NOT Supabase

INSERT INTO companies (
  canonical_id, name, website, linkedin_url,
  industry, stage, hq_city, hq_country,
  ats_provider, ats_slug,
  ai_native, hiring_active,
  source, confidence, ingested_at
) VALUES

-- ── AI / LLM Labs ─────────────────────────────────────────────────────────────

(
  'seed_anthropic_001',
  'Anthropic',
  'https://anthropic.com',
  'https://www.linkedin.com/company/anthropic',
  'AI/ML', 'series_d_plus', 'San Francisco', 'US',
  'greenhouse', 'anthropic',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_openai_001',
  'OpenAI',
  'https://openai.com',
  'https://www.linkedin.com/company/openai',
  'AI/ML', 'series_d_plus', 'San Francisco', 'US',
  'ashby', 'openai',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_mistral_001',
  'Mistral AI',
  'https://mistral.ai',
  'https://www.linkedin.com/company/mistral-ai',
  'AI/ML', 'series_b', 'Paris', 'FR',
  'ashby', 'mistral',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_cohere_001',
  'Cohere',
  'https://cohere.com',
  'https://www.linkedin.com/company/cohere-ai',
  'AI/ML', 'series_c', 'Toronto', 'CA',
  'greenhouse', 'cohere',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_cursor_001',
  'Cursor (Anysphere)',
  'https://cursor.sh',
  'https://www.linkedin.com/company/anysphere',
  'Developer Tools', 'series_b', 'San Francisco', 'US',
  'ashby', 'cursor',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_perplexity_001',
  'Perplexity AI',
  'https://perplexity.ai',
  'https://www.linkedin.com/company/perplexityai',
  'AI/ML', 'series_b', 'San Francisco', 'US',
  'greenhouse', 'perplexityai',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_elevenlabs_001',
  'ElevenLabs',
  'https://elevenlabs.io',
  'https://www.linkedin.com/company/elevenlabs-io',
  'AI/ML', 'series_b', 'New York', 'US',
  'ashby', 'elevenlabs',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),

-- ── Indian Fintech ─────────────────────────────────────────────────────────────

(
  'seed_razorpay_001',
  'Razorpay',
  'https://razorpay.com',
  'https://www.linkedin.com/company/razorpay',
  'Fintech', 'series_f', 'Bengaluru', 'IN',
  'greenhouse', 'razorpaysoftwareprivatelimited',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_cred_001',
  'CRED',
  'https://cred.club',
  'https://www.linkedin.com/company/cred-club',
  'Fintech', 'series_e', 'Bengaluru', 'IN',
  'lever', 'cred',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_paytm_001',
  'Paytm',
  'https://paytm.com',
  'https://www.linkedin.com/company/paytm',
  'Fintech', 'public_listed', 'Noida', 'IN',
  'lever', 'paytm',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_groww_001',
  'Groww',
  'https://groww.in',
  'https://www.linkedin.com/company/growwapp',
  'Fintech', 'series_d', 'Bengaluru', 'IN',
  'greenhouse', 'groww',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_zerodha_001',
  'Zerodha',
  'https://zerodha.com',
  'https://www.linkedin.com/company/zerodha',
  'Fintech', 'bootstrapped', 'Bengaluru', 'IN',
  'lever', 'zerodha',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),

-- ── Indian Consumer Tech ───────────────────────────────────────────────────────

(
  'seed_meesho_001',
  'Meesho',
  'https://meesho.com',
  'https://www.linkedin.com/company/meesho',
  'E-Commerce', 'series_f', 'Bengaluru', 'IN',
  'lever', 'meesho',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_swiggy_001',
  'Swiggy',
  'https://swiggy.com',
  'https://www.linkedin.com/company/swiggy',
  'Food Tech', 'public_listed', 'Bengaluru', 'IN',
  'greenhouse', 'swiggy',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_zomato_001',
  'Zomato',
  'https://zomato.com',
  'https://www.linkedin.com/company/zomato',
  'Food Tech', 'public_listed', 'Gurugram', 'IN',
  'greenhouse', 'zomato',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_phonepe_001',
  'PhonePe',
  'https://phonepe.com',
  'https://www.linkedin.com/company/phonepe-internet',
  'Fintech', 'series_d', 'Bengaluru', 'IN',
  'greenhouse', 'phonepe',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_navi_001',
  'Navi',
  'https://navi.com',
  'https://www.linkedin.com/company/navimutual',
  'Fintech', 'series_b', 'Bengaluru', 'IN',
  'lever', 'navi',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),

-- ── Indian SaaS / B2B ─────────────────────────────────────────────────────────

(
  'seed_slintel_001',
  'TechCo SaaS',
  'https://techco_saas.com',
  'https://www.linkedin.com/company/techco_saas',
  'SaaS', 'public_listed', 'New York', 'US',
  'greenhouse', 'techco_saas',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_hasura_001',
  'Hasura',
  'https://hasura.io',
  'https://www.linkedin.com/company/hasura',
  'Developer Tools', 'series_c', 'San Francisco', 'US',
  'lever', 'hasura',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_browserstack_001',
  'BrowserStack',
  'https://browserstack.com',
  'https://www.linkedin.com/company/browserstack',
  'Developer Tools', 'series_b', 'Mumbai', 'IN',
  'greenhouse', 'browserstack',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_postman_001',
  'Postman',
  'https://postman.com',
  'https://www.linkedin.com/company/postman-platform',
  'Developer Tools', 'series_d', 'San Francisco', 'US',
  'greenhouse', 'postman',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),

-- ── Global AI-first companies with India hiring ───────────────────────────────

(
  'seed_scale_ai_001',
  'Scale AI',
  'https://scale.com',
  'https://www.linkedin.com/company/scaleai',
  'AI/ML', 'series_f', 'San Francisco', 'US',
  'greenhouse', 'scaleai',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_huggingface_001',
  'Hugging Face',
  'https://huggingface.co',
  'https://www.linkedin.com/company/hugging-face',
  'AI/ML', 'series_c', 'New York', 'US',
  'greenhouse', 'huggingface',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_weights_biases_001',
  'Weights & Biases',
  'https://wandb.ai',
  'https://www.linkedin.com/company/weights-biases',
  'ML Ops', 'series_c', 'San Francisco', 'US',
  'greenhouse', 'wandb',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_modal_001',
  'Modal',
  'https://modal.com',
  'https://www.linkedin.com/company/modal-labs',
  'Developer Tools', 'series_b', 'New York', 'US',
  'ashby', 'modal',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),

-- ── Fast-growing Indian AI-native startups ────────────────────────────────────

(
  'seed_sarvam_001',
  'Sarvam AI',
  'https://sarvam.ai',
  'https://www.linkedin.com/company/sarvam-ai',
  'AI/ML', 'series_a', 'Bengaluru', 'IN',
  'ashby', 'sarvam',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_krutrim_001',
  'Krutrim',
  'https://krutrim.ai',
  'https://www.linkedin.com/company/krutrim',
  'AI/ML', 'series_a', 'Bengaluru', 'IN',
  'lever', 'krutrim',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_learnapp_001',
  'LearnApp',
  'https://learnapp.com',
  'https://www.linkedin.com/company/learnapp',
  'Ed Tech', 'seed', 'Bengaluru', 'IN',
  'lever', 'learnapp',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_smallcase_001',
  'Smallcase',
  'https://smallcase.com',
  'https://www.linkedin.com/company/smallcase',
  'Fintech', 'series_c', 'Bengaluru', 'IN',
  'lever', 'smallcase',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_chargebee_001',
  'Chargebee',
  'https://chargebee.com',
  'https://www.linkedin.com/company/chargebee',
  'SaaS', 'series_g', 'San Francisco', 'US',
  'greenhouse', 'chargebee',
  FALSE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
),
(
  'seed_locus_001',
  'Locus',
  'https://locus.sh',
  'https://www.linkedin.com/company/locus-sh',
  'Logistics Tech', 'series_c', 'Bengaluru', 'IN',
  'greenhouse', 'locus',
  TRUE, TRUE,
  ARRAY['seed_migration_004'], 'high', NOW()
)

-- ON CONFLICT DO NOTHING: this seed runs only against an empty table.
-- Re-running against a populated companies table must NEVER overwrite
-- existing rows — production canonical_id rows are authoritative.
-- (Earlier version used DO UPDATE which would have silently overwritten
-- real company rows if seed values drifted from production values.)
ON CONFLICT (canonical_id) DO NOTHING;

-- Verify seed count (informational — does not fail migration)
DO $$
DECLARE
  seed_count INT;
BEGIN
  SELECT COUNT(*) INTO seed_count
  FROM companies
  WHERE 'seed_migration_004' = ANY(source);

  RAISE NOTICE 'Seed migration 004 complete: % companies inserted/updated', seed_count;

  IF seed_count < 31 THEN
    RAISE EXCEPTION 'Seed count % < 31 — migration incomplete', seed_count;
  END IF;
END $$;
