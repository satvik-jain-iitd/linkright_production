"""Graph-based subliminal context retrieval for step_10 bullet generation.

Queries the career graph (built by `linkright profile graph`) to extract
the implicit brand signals associated with a company. Injected into step_10
prompt so the LLM frames bullets with the right unconscious impression.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


def get_subliminal_context(company_name: str, profile_dir: Path) -> str:
    """BFS from company node in career graph -> community label + brand signals.

    Returns a formatted text block for injection into step_10 prompt.
    Returns empty string if graph.json missing or company not found (graceful fallback).
    """
    graph_path = profile_dir / "graph.json"
    if not graph_path.exists():
        return ""

    try:
        from networkx.readwrite import json_graph
        import networkx as nx

        data = json.loads(graph_path.read_text())
        G = json_graph.node_link_graph(data, edges="links")

        if G.number_of_nodes() == 0:
            return ""

        # Find best-matching node for company_name
        company_lower = company_name.lower()
        scored = sorted(
            [
                (sum(1 for w in company_lower.split() if w in G.nodes[n].get("label", "").lower()), n)
                for n in G.nodes()
            ],
            reverse=True,
        )
        if not scored or scored[0][0] == 0:
            return ""

        company_node = scored[0][1]
        company_label = G.nodes[company_node].get("label", company_name)

        # BFS 2 hops to get neighbors
        neighbors = set()
        frontier = {company_node}
        for _ in range(2):
            next_frontier = set()
            for n in frontier:
                for nb in G.neighbors(n):
                    if nb != company_node and nb not in neighbors:
                        next_frontier.add(nb)
            neighbors.update(next_frontier)
            frontier = next_frontier

        # Get community label from node data
        community_label = ""
        for node_data in data.get("nodes", []):
            if node_data.get("id") == company_node:
                cid = node_data.get("community")
                if cid is not None:
                    community_label = data.get("community_labels", {}).get(str(cid), "")
                break

        # Top 6 neighbor labels as brand signals
        neighbor_labels = [
            G.nodes[n].get("label", n)
            for n in list(neighbors)[:6]
            if G.nodes[n].get("label", "")
        ]

        if not neighbor_labels and not community_label:
            return ""

        lines = ["## Subliminal Signal Context"]
        lines.append(f"Company cluster: {community_label or 'Unknown'}")
        if neighbor_labels:
            lines.append(f"Associated signals: {', '.join(neighbor_labels)}")
        lines.append(
            "Frame bullets to reinforce the implicit impression this company cluster sends "
            "to a recruiter scanning in 6 seconds. Leverage brand associations above to "
            "signal credibility, scale, and fit without stating them explicitly."
        )
        return "\n".join(lines)

    except Exception:
        return ""
