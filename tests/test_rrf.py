import pytest
from app.retrieval.rrf import reciprocal_rank_fusion
from app.schemas.retrieval import RetrievalResult


def _result(id: str, score: float, source: str = "text"):
    return RetrievalResult(id=id, content=f"Content {id}", score=score, page_number=1, source_type=source)


def test_rrf_single_list():
    results = [_result("a", 0.9), _result("b", 0.8)]
    fused = reciprocal_rank_fusion(results, k=60)
    assert len(fused) == 2
    assert fused[0].id == "a"
    assert fused[0].rrf_score > fused[1].rrf_score


def test_rrf_multiple_lists_boost_shared():
    list1 = [_result("a", 0.9), _result("b", 0.8)]
    list2 = [_result("b", 0.95), _result("c", 0.7)]
    fused = reciprocal_rank_fusion(list1, list2, k=60)
    b_result = next(f for f in fused if f.id == "b")
    a_result = next(f for f in fused if f.id == "a")
    assert b_result.rrf_score > a_result.rrf_score  # b appears in both lists


def test_rrf_preserves_all_items():
    list1 = [_result("a", 0.9)]
    list2 = [_result("b", 0.8)]
    list3 = [_result("c", 0.7)]
    fused = reciprocal_rank_fusion(list1, list2, list3, k=60)
    ids = {f.id for f in fused}
    assert ids == {"a", "b", "c"}


def test_rrf_empty_lists():
    fused = reciprocal_rank_fusion([], k=60)
    assert fused == []


def test_rrf_image_and_text_combined():
    text_results = [_result("t1", 0.9, "text"), _result("t2", 0.8, "text")]
    image_results = [_result("i1", 0.7, "image")]
    fused = reciprocal_rank_fusion(text_results, image_results, k=60)
    assert len(fused) == 3
    types = {f.source_type for f in fused}
    assert "text" in types and "image" in types
