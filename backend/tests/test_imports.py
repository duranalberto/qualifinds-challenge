def test_langgraph_import() -> None:
    from langgraph.graph import StateGraph
    assert StateGraph is not None


def test_langchain_ollama_import() -> None:
    from langchain_ollama import ChatOllama
    assert ChatOllama is not None


def test_simpleeval_import() -> None:
    from simpleeval import EvalWithCompoundTypes
    assert EvalWithCompoundTypes is not None
