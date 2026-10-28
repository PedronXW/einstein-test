"""Testes TDD da feature F-023 (refactor do RAG).

Valida: novo pacote services/rag/ com submódulos coesos, re-exportação via
services/rag.py (imports intactos), e eliminação da duplicação sync/async.
"""

import inspect


def test_ac001_rag_is_package_with_submodules():
    from einstein_test.services import rag

    assert hasattr(rag, "__path__"), "services/rag é um pacote"
    import einstein_test.services.rag.graph as graph
    import einstein_test.services.rag.llm as llm
    import einstein_test.services.rag.service as service

    assert hasattr(llm, "ChatOpenAIAdapter")
    assert hasattr(llm, "FakeChatLLM")
    assert hasattr(graph, "build_prompt")
    assert hasattr(graph, "compile_rag_graph")
    assert hasattr(service, "RagService")


def test_ac002_public_reexports_present():
    import einstein_test.services.rag as rag

    expected = [
        "ChatLLM", "FakeChatLLM", "ChatOpenAIAdapter", "RagService",
        "build_graph", "build_graph_async", "build_prompt",
        "get_rag_service", "set_rag_factory", "reset_rag_factory",
        "allowed_models",
    ]
    for name in expected:
        assert hasattr(rag, name), f"services.rag reexporta {name}"


def test_ac003_no_duplicated_graph_build():
    # a duplicação da MONTAGEM do grafo foi eliminada: o StateGraph é
    # construído/compilado em um único lugar (`_compile`), sem repetir
    # add_node/set_entry_point em cada variante.
    import einstein_test.services.rag.graph as graph

    source = inspect.getsource(graph)
    assert source.count("StateGraph(") == 1, "um único StateGraph"
    assert source.count("graph.add_node") == 2, "dois add_node (retrieve+generate) — uma vez"
    assert source.count("graph.compile()") == 1, "um único compile"
    assert "compile_rag_graph" in source, "construtor comum de grafo"


def test_ac003_async_uses_to_thread():
    import einstein_test.services.rag.graph as graph

    source = inspect.getsource(graph)
    assert "asyncio.to_thread" in source, "retrieve async usa to_thread"


def test_ac004_rag_service_still_streams():
    from einstein_test.services.rag import FakeChatLLM, RagService
    from einstein_test.vector import FakeEmbedder
    from einstein_test.vector.similarity import cosine_similarity_search

    class _Repo:
        def search_similar(self, embedding, chat_id, chunks_per_file=2, max_chunks=12):
            return cosine_similarity_search(embedding, [], top_k=max_chunks)

    svc = RagService(
        llm=FakeChatLLM(tokens=["t1", "t2"]),
        retriever=_Repo(),
        embedder=FakeEmbedder(),
    )
    assert list(svc.stream(question="q", chat_id=1, history=[])) == ["t1", "t2"]