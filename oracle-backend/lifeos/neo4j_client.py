"""Neo4j client — schema setup + Cypher helpers."""
from __future__ import annotations

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return _driver


def setup_schema():
    """Idempotent: create constraints + vector index on first startup."""
    driver = get_driver()
    with driver.session() as session:
        session.run(
            "CREATE CONSTRAINT achievement_id IF NOT EXISTS "
            "FOR (n:Achievement) REQUIRE n.id IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT experience_id IF NOT EXISTS "
            "FOR (n:Experience) REQUIRE n.id IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT skill_name IF NOT EXISTS "
            "FOR (n:Skill) REQUIRE n.name IS UNIQUE"
        )
        session.run("""
            CREATE VECTOR INDEX achievement_embeddings IF NOT EXISTS
            FOR (n:Achievement) ON n.embedding
            OPTIONS {
              indexConfig: {
                `vector.dimensions`: 768,
                `vector.similarity_function`: 'cosine'
              }
            }
        """)


def find_similar_achievements(user_id: str, embedding: list[float], threshold: float = 0.85) -> list[dict]:
    """Return achievements with cosine similarity above threshold (conflict detection)."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a:Achievement {user_id: $user_id})
            WHERE a.embedding IS NOT NULL
            WITH a, vector.similarity.cosine(a.embedding, $embedding) AS score
            WHERE score > $threshold
            RETURN a.id AS id, a.action_detail AS action_detail, score
            ORDER BY score DESC
            LIMIT 3
            """,
            user_id=user_id,
            embedding=embedding,
            threshold=threshold,
        )
        return [dict(r) for r in result]


def merge_achievement(achievement_id: str, props: dict) -> None:
    """MERGE Achievement node — idempotent."""
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (a:Achievement {id: $id})
            SET a += $props
            """,
            id=achievement_id,
            props=props,
        )


def merge_experience(experience_id: str, company: str, role: str, user_id: str) -> None:
    """MERGE Experience node."""
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (e:Experience {id: $id})
            SET e.company = $company, e.role = $role, e.user_id = $user_id
            """,
            id=experience_id,
            company=company,
            role=role,
            user_id=user_id,
        )


def link_achievement_to_experience(achievement_id: str, experience_id: str) -> None:
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MATCH (a:Achievement {id: $aid})
            MATCH (e:Experience {id: $eid})
            MERGE (a)-[:AT]->(e)
            """,
            aid=achievement_id,
            eid=experience_id,
        )


def merge_skill_and_link(skill_name: str, achievement_id: str, user_id: str) -> None:
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (s:Skill {name: $name})
            SET s.user_id = $user_id
            WITH s
            MATCH (a:Achievement {id: $aid})
            MERGE (a)-[:DEMONSTRATES]->(s)
            """,
            name=skill_name,
            user_id=user_id,
            aid=achievement_id,
        )


def merge_metric_and_link(metric_id: str, metric_props: dict, achievement_id: str) -> None:
    driver = get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (m:Metric {id: $id})
            SET m += $props
            WITH m
            MATCH (a:Achievement {id: $aid})
            MERGE (a)-[:RESULTED_IN]->(m)
            """,
            id=metric_id,
            props=metric_props,
            aid=achievement_id,
        )


def search_achievements_by_jd(user_id: str, jd_embedding: list[float], limit: int = 12) -> list[dict]:
    """Vector search: return top-N achievements matching a JD embedding."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a:Achievement {user_id: $user_id})
            WHERE a.embedding IS NOT NULL
            WITH a, vector.similarity.cosine(a.embedding, $embedding) AS score
            WHERE score > 0.55
            MATCH (a)-[:AT]->(exp:Experience)
            OPTIONAL MATCH (a)-[:RESULTED_IN]->(m:Metric)
            OPTIONAL MATCH (a)-[:DEMONSTRATES]->(s:Skill)
            RETURN a, exp,
                   collect(DISTINCT m) AS metrics,
                   collect(DISTINCT s.name) AS skills,
                   score
            ORDER BY score DESC
            LIMIT $limit
            """,
            user_id=user_id,
            embedding=jd_embedding,
            limit=limit,
        )
        rows = []
        for r in result:
            a = dict(r["a"])
            exp = dict(r["exp"])
            a.pop("embedding", None)  # don't send embedding back over wire
            rows.append({
                "achievement": a,
                "experience": exp,
                "metrics": [dict(m) for m in r["metrics"]],
                "skills": r["skills"],
                "score": r["score"],
            })
        return rows


def list_existing_atoms(user_id: str) -> list[dict]:
    """Summary of already-captured atoms — for Custom GPT session start."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a:Achievement {user_id: $user_id})-[:AT]->(exp:Experience)
            RETURN a.action_verb AS action_verb,
                   a.action_detail AS action_detail,
                   exp.company AS company,
                   exp.role AS role,
                   a.timeframe AS timeframe
            ORDER BY a.created_at DESC
            """,
            user_id=user_id,
        )
        return [dict(r) for r in result]
