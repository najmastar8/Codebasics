from tubetutor.graph import build_graph, smoke_state


def test_build_graph_has_expected_nodes() -> None:
    graph = build_graph()
    assert "route_request" in graph["nodes"]
    assert ("ingest", "load_memory") in graph["edges"]


def test_smoke_state_sets_basic_fields() -> None:
    state = smoke_state()
    assert state.intent == "summarize"
    assert state.confidence > 0.9
    assert state.trace_id
