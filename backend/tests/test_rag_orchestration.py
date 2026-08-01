import pytest

from api_helpers import generate_chat_response_async


@pytest.mark.asyncio
async def test_generate_chat_response_async_uses_rag_fallback_when_index_missing(monkeypatch):
    class FakeRetriever:
        def retrieve(self, *args, **kwargs):
            return []

    class FakeQueryRouter:
        def route(self, *args, **kwargs):
            return {"needs_retrieval": True, "needs_stats": False, "reason": "semantic"}

    class FakePromptBuilder:
        def build(self, *args, **kwargs):
            return "prompt"

    class FakeCitationBuilder:
        def build(self, *args, **kwargs):
            return []

    class FakeLLM:
        async def generate(self, *args, **kwargs):
            return "rag answer"

    monkeypatch.setattr("api_helpers.build_query_router", lambda: FakeQueryRouter())
    monkeypatch.setattr("api_helpers.build_retriever", lambda: FakeRetriever())
    monkeypatch.setattr("api_helpers.build_prompt_builder", lambda: FakePromptBuilder())
    monkeypatch.setattr("api_helpers.build_citation_builder", lambda: FakeCitationBuilder())
    monkeypatch.setattr("api_helpers.build_llm_service", lambda: FakeLLM())

    result = await generate_chat_response_async(
        question="What is in the data?",
        history=[],
        data_or_df=[{"name": "Alice", "age": 30}],
        filename="demo.csv",
        dataset_id="demo-dataset",
    )

    assert result["answer"] == "rag answer"
