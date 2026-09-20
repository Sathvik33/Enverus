from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_llm = None


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        settings = get_settings()
        logger.info("initializing_llm", model=settings.LLM_MODEL, base_url=settings.OLLAMA_BASE_URL)
        _llm = ChatOllama(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1,
        )
    return _llm


async def generate_response(system_prompt: str, user_prompt: str) -> str:
    llm = get_llm()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    try:
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.error("llm_generation_failed", error=str(e))
        raise


async def generate_simple(prompt: str) -> str:
    llm = get_llm()
    messages = [HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    return response.content


async def stream_response(system_prompt: str, user_prompt: str):
    llm = get_llm()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield chunk.content
    except Exception as e:
        logger.error("llm_stream_failed", error=str(e))
        yield f"\n\n[Error generating response: {str(e)}]"
