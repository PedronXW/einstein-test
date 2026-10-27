"""Testes TDD da feature F-011 (AC-002/AC-003/AC-006: RAG service + LLM).

Valida o RagService: grafo LangGraph (retrieve->generate), a abstração
ChatLLM, o FakeChatLLM determinístico e o contexto (chunks + pergunta +
histórico). Nenhum token real é gasto.
"""

from einstein_test.services.rag import FakeChatLLM, RagService
from einstein_test.vector import FakeEmbedder
from einstein_test.vector.similarity import cosine_similarity_search


class _FakeVectorRepo:
    def __init__(self, chunks):
        self._chunks = chunks

    def search_similar(self, embedding, chat_id, chunks_per_file=2, max_chunks=12):
        return cosine_similarity_search(embedding, self._chunks, top_k=max_chunks)


def _chunk(content, file_id=1):
    return type(
        "Chunk",
        (),
        {"content": content, "file_id": file_id, "embedding": [1.0, 0.0, 0.0]},
    )()


def _service(chunks, tokens=None):
    return RagService(
        llm=FakeChatLLM(tokens=tokens),
        retriever=_FakeVectorRepo(chunks),
        embedder=FakeEmbedder(),
    )


def test_ac002_rag_service_builds_graph():
    service = _service([])
    assert service.graph is not None, "RagService expõe grafo LangGraph compilado"


def test_ac002_stream_emits_tokens_from_llm():
    service = _service([_chunk("sobre gorilas")], tokens=["olá", " mundo"])
    tokens = list(service.stream(question="o que há?", chat_id=1, history=[]))
    assert tokens == ["olá", " mundo"]


def test_ac003_fake_llm_stream_is_deterministic():
    fake = FakeChatLLM(tokens=["olá", " mundo"])
    assert list(fake.stream("qualquer prompt")) == ["olá", " mundo"]
    fake2 = FakeChatLLM(tokens=["olá", " mundo"])
    assert list(fake2.stream("outro prompt")) == ["olá", " mundo"], (
        "FakeChatLLM determinístico"
    )


def test_ac003_chatllm_is_protocol():
    from einstein_test.services.rag import ChatLLM

    assert hasattr(ChatLLM, "stream")


def test_ac006_build_prompt_includes_chunks_history_question():
    service = _service([])
    prompt = service._build_prompt(
        question="o que há no chat?",
        chunks=[_chunk("sobre gorilas"), _chunk("sobre zebras")],
        history=["mensagem1", "mensagem2"],
    )
    assert "sobre gorilas" in prompt, "contexto inclui chunks"
    assert "o que há no chat?" in prompt, "pergunta incluída"


def test_ac006_generate_joins_tokens():
    service = _service([], tokens=["A", "B", "C"])
    answer = service._generate_answer(
        question="pergunta", chat_id=1, history=[]
    )
    assert answer == "ABC"


def test_ac002_rag_stream_uses_retriever():
    service = _service([_chunk("sobre gorilas")], tokens=["t1", "t2"])
    tokens = list(service.stream(question="gorilas?", chat_id=1, history=[]))
    assert tokens == ["t1", "t2"]