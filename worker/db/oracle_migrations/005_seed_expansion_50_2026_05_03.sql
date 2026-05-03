-- Migration 005: Seed expansion — 50 additional companies (2026-05-03)
-- Source: worker/db/oracle_seed_inputs/seed_expansion_50_2026_05_03.json
-- Discovery method: linkright admin slug-discovery batch (Sprint B Layer 1)
-- 28/50 companies got ATS pairings auto-discovered live against the providers
-- (greenhouse/ashby brute-force majority); the remaining 22 (mostly Indian-
-- market SaaS) had no Greenhouse/Lever/Ashby/Keka match and stay ats=NULL
-- pending Naukri/internal-portal coverage in a future sprint.
--
-- confidence='high' = ATS slug verified returning live jobs from the API
-- confidence='medium' = imported but no ATS pairing found (still useful as
--                       company-knowledge row; user can manually link later)
--
-- Target: Oracle Postgres (ORACLE_PG_URL) — NOT Supabase

INSERT INTO companies (
  canonical_id, name, website, linkedin_url,
  industry, stage, hq_city, hq_country,
  ats_provider, ats_slug,
  ai_native, hiring_active,
  source, confidence, ingested_at
) VALUES

-- ── AI/ML ──
(
  '4456884be5f2694b8639700c61827611ef4dcdce',
  'Anyscale',
  'https://anyscale.com',
  NULL,
  'AI/ML', NULL, 'San Francisco', 'US',
  'ashby', 'anyscale',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '66298e9e0956d3d2b843d6d1e8f867bb07b0ba6f',
  'Character.AI',
  'https://character.ai',
  NULL,
  'AI/ML', NULL, 'Menlo Park', 'US',
  NULL, NULL,
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  '4dcbaf0237aae3ec76b815b418445e3db47bd64d',
  'Glean',
  'https://glean.com',
  NULL,
  'AI/ML', NULL, 'Palo Alto', 'US',
  NULL, NULL,
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  'da932a7ac89b75bd7fa55ad77c75b3233e975d2d',
  'Harvey',
  'https://harvey.ai',
  NULL,
  'AI/ML', NULL, 'San Francisco', 'US',
  'ashby', 'harvey',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '04d6bbcacce3bce05703152bdea521d6ab42e1f5',
  'Jasper',
  'https://jasper.ai',
  NULL,
  'AI/ML', NULL, 'Austin', 'US',
  NULL, NULL,
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  '0be8fe5648fe66e15a4bc86796ee11694fe657f7',
  'Lambda Labs',
  'https://lambdalabs.com',
  NULL,
  'AI/ML', NULL, 'San Francisco', 'US',
  'ashby', 'lambda',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '11fd0386a3806f995bcd6af77049e0d7703f0d5a',
  'OctoAI',
  'https://octo.ai',
  NULL,
  'AI/ML', NULL, 'Seattle', 'US',
  NULL, NULL,
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  '1ab5308ce3f3064b6d2d0da754720b78d82422da',
  'Pika',
  'https://pika.art',
  NULL,
  'AI/ML', NULL, 'Palo Alto', 'US',
  'ashby', 'pika',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  'a3610f01ba6bc3845675eac08ae91a240e6179d4',
  'Pinecone',
  'https://pinecone.io',
  NULL,
  'AI/ML', NULL, 'New York', 'US',
  'ashby', 'pinecone',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '1727cc913132a098e715918a968ee2dd26fbe523',
  'Replicate',
  'https://replicate.com',
  NULL,
  'AI/ML', NULL, 'San Francisco', 'US',
  NULL, NULL,
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  '45039f992058f1714848c3529caf63fe9d393421',
  'Runway',
  'https://runwayml.com',
  NULL,
  'AI/ML', NULL, 'New York', 'US',
  'ashby', 'runway',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  'a5f4846a84d4b4c7d79ca91ab59cdeb4368f5d5e',
  'Stability AI',
  'https://stability.ai',
  NULL,
  'AI/ML', NULL, 'London', 'GB',
  'greenhouse', 'stabilityai',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '5773d7fb7df7c564e2758d85f76ae36be13f6a3e',
  'Suno',
  'https://suno.com',
  NULL,
  'AI/ML', NULL, 'Cambridge', 'US',
  'ashby', 'suno',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '5ad2133cc840655f9cc4aec7bb8f7cda5c4d34eb',
  'Together AI',
  'https://together.ai',
  NULL,
  'AI/ML', NULL, 'San Francisco', 'US',
  'greenhouse', 'togetherai',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '0a4167686ef092281a4d2b9405bb82b0e43fda35',
  'Writer',
  'https://writer.com',
  NULL,
  'AI/ML', NULL, 'San Francisco', 'US',
  'ashby', 'writer',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '6558fb82d73a95e17f07b09346c7f1adae4633e2',
  'xAI',
  'https://x.ai',
  NULL,
  'AI/ML', NULL, 'San Francisco', 'US',
  'greenhouse', 'xai',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Cloud Infra ──
(
  '5e7c83cd07176407c9b7775ca7540c28a89baa27',
  'Cloudflare',
  'https://cloudflare.com',
  NULL,
  'Cloud Infra', NULL, 'San Francisco', 'US',
  'greenhouse', 'cloudflare',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Communications ──
(
  '79b78dba22f3d5710cb6a1f5e211c445d07a1db0',
  'Twilio',
  'https://twilio.com',
  NULL,
  'Communications', NULL, 'San Francisco', 'US',
  'greenhouse', 'twilio',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Consumer ──
(
  '924316f0fdd901221b949767be8437848f450978',
  'boAt',
  'https://boat-lifestyle.com',
  NULL,
  'Consumer', NULL, 'Mumbai', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  'b1dbe7ed7d92ca49601bfd74e1899e9ed4f5501a',
  'Mamaearth',
  'https://mamaearth.in',
  NULL,
  'Consumer', NULL, 'Gurugram', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Database ──
(
  'c061fe5b751dc49be2a15efe958d5eb106c904bb',
  'MongoDB',
  'https://mongodb.com',
  NULL,
  'Database', NULL, 'New York', 'US',
  'greenhouse', 'mongodb',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Data Platform ──
(
  '32a4b7c73118822f1267cb90f41a0023cb72dc0e',
  'Confluent',
  'https://confluent.io',
  NULL,
  'Data Platform', NULL, 'Mountain View', 'US',
  'ashby', 'confluent',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '2b27ed8c42c86081ef38d799b17fc2485666cb76',
  'Databricks',
  'https://databricks.com',
  NULL,
  'Data Platform', NULL, 'San Francisco', 'US',
  'greenhouse', 'databricks',
  TRUE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '149bd494bbfd859912d62a1d7825b22119f3faab',
  'Snowflake',
  'https://snowflake.com',
  NULL,
  'Data Platform', NULL, 'Bozeman', 'US',
  'ashby', 'snowflake',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Design Tools ──
(
  '0e00e402f4cc9c26cc16ade9dcd94dc48cd770f5',
  'Figma',
  'https://figma.com',
  NULL,
  'Design Tools', NULL, 'San Francisco', 'US',
  'greenhouse', 'figma',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Developer Tools ──
(
  'ccbcbe58d17174fbd1ed4aebb77b0207003d9f62',
  'HashiCorp',
  'https://hashicorp.com',
  NULL,
  'Developer Tools', NULL, 'San Francisco', 'US',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  '44cb5a404ad045703fc7ffd273a3f4ec570e8d91',
  'Vercel',
  'https://vercel.com',
  NULL,
  'Developer Tools', NULL, 'San Francisco', 'US',
  'greenhouse', 'vercel',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── E-Commerce ──
(
  '4b194821797bfcaca27591c7e67f2f3b4ba9b6f2',
  'Lenskart',
  'https://lenskart.com',
  NULL,
  'E-Commerce', NULL, 'Faridabad', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  'cb198869e57ee31b21fc9a3a19faff4fd25347e3',
  'Nykaa',
  'https://nykaa.com',
  NULL,
  'E-Commerce', NULL, 'Mumbai', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  'f3381a5b9dcbb2494690235454cb81bc75698ce2',
  'Shopify',
  'https://shopify.com',
  NULL,
  'E-Commerce', NULL, 'Ottawa', 'CA',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Ed Tech ──
(
  'af7c961f31f4cd56fc8c6dcb87326f4a7138bf4e',
  'Unacademy',
  'https://unacademy.com',
  NULL,
  'Ed Tech', NULL, 'Bengaluru', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Fintech ──
(
  'b9efb80dcd148479921b3d7f0d61266d96c1040d',
  'BharatPe',
  'https://bharatpe.com',
  NULL,
  'Fintech', NULL, 'New Delhi', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  'd74400109fe896cff4f2df9fdd4c57c8deb2a089',
  'Block',
  'https://block.xyz',
  NULL,
  'Fintech', NULL, 'San Francisco', 'US',
  'greenhouse', 'block',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  'ace5122047b38838405a2c9d23f50ff2eae270d0',
  'Coinbase',
  'https://coinbase.com',
  NULL,
  'Fintech', NULL, 'San Francisco', 'US',
  'greenhouse', 'coinbase',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  'caaae495626f8a73f3b223a68582f13830f14023',
  'Pine Labs',
  'https://pinelabs.com',
  NULL,
  'Fintech', NULL, 'Noida', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  'ed87349704f1f90912f1adecf2c263f7491f9748',
  'Plaid',
  'https://plaid.com',
  NULL,
  'Fintech', NULL, 'San Francisco', 'US',
  'ashby', 'plaid',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  '9ababc9aff17ac87c7a2ab2d48f49e015b5edcb9',
  'Stripe',
  'https://stripe.com',
  NULL,
  'Fintech', NULL, 'San Francisco', 'US',
  'greenhouse', 'stripe',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Food Tech ──
(
  '133c46b22745ffff24d6c557766090c21a13d91c',
  'DoorDash',
  'https://doordash.com',
  NULL,
  'Food Tech', NULL, 'San Francisco', 'US',
  'greenhouse', 'doordashindia',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── Gaming ──
(
  '23dfa9a2471aca38200402ec00dc07562311d350',
  'Dream11',
  'https://dream11.com',
  NULL,
  'Gaming', NULL, 'Mumbai', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── InsurTech ──
(
  'a07b48f315719dcadcb34d6b9c74c0b744b3c7d2',
  'Acko',
  'https://acko.com',
  NULL,
  'InsurTech', NULL, 'Bengaluru', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Marketplace ──
(
  'fe71fb4f1c868db6b10c44d0dcd3b0d32ff03fc2',
  'Urban Company',
  'https://urbancompany.com',
  NULL,
  'Marketplace', NULL, 'Gurugram', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Observability ──
(
  '267809874370463ae028d0fce79559c377ae664a',
  'Datadog',
  'https://datadoghq.com',
  NULL,
  'Observability', NULL, 'New York', 'US',
  'greenhouse', 'datadog',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),

-- ── SaaS ──
(
  'cc51b9b510188587d006c3369bae334f1c30ec7c',
  'Freshworks',
  'https://freshworks.com',
  NULL,
  'SaaS', NULL, 'Chennai', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  '3bccbda41093fa186a13be206607b08c88a6cced',
  'Linear',
  'https://linear.app',
  NULL,
  'SaaS', NULL, 'San Francisco', 'US',
  'ashby', 'linear',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  'f96b1b86bc29156ad42ca9af0c54744b8ac2e61c',
  'Notion',
  'https://notion.so',
  NULL,
  'SaaS', NULL, 'San Francisco', 'US',
  'ashby', 'notion',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
),
(
  'fb525677911197b7525ecb60467c38ba9e4d57bb',
  'Zoho',
  'https://zoho.com',
  NULL,
  'SaaS', NULL, 'Chennai', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Social ──
(
  'd230a9e6fa876557c28a7ed7c5954d65399af60a',
  'ShareChat',
  'https://sharechat.com',
  NULL,
  'Social', NULL, 'Bengaluru', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Space Tech ──
(
  '0fe514505299e114218d72fcb1e18ed5d9fa0bfe',
  'Pixxel',
  'https://pixxel.space',
  NULL,
  'Space Tech', NULL, 'Bengaluru', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),
(
  'd8ab285e7f823d499d011e567b51c128a8c8181e',
  'Skyroot Aerospace',
  'https://skyroot.in',
  NULL,
  'Space Tech', NULL, 'Hyderabad', 'IN',
  NULL, NULL,
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'medium', NOW()
),

-- ── Web3 ──
(
  'f1a89dba2f2002566200cdf7f447160c7322f90f',
  'Polygon Labs',
  'https://polygon.technology',
  NULL,
  'Web3', NULL, 'Bengaluru', 'IN',
  'ashby', 'polygon-labs',
  FALSE, TRUE,
  ARRAY['seed_expansion_2026_05_03'], 'high', NOW()
)

ON CONFLICT (canonical_id) DO NOTHING;
