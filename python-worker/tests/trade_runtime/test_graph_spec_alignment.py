from trade_runtime.decision.graph import build_decision_graph


def test_graph_contains_spec_nodes():
    graph = build_decision_graph()
    node_names = set(graph.get_graph().nodes.keys())

    assert {
        "ingest_context",
        "build_feature_snapshot",
        "classify",
        "supervisor",
        "risk_gate",
        "execute_order",
        "audit",
    } <= node_names


def test_graph_contains_memory_retrieval_node():
    graph = build_decision_graph()
    node_names = set(graph.get_graph().nodes.keys())

    assert "retrieve_memory" in node_names
