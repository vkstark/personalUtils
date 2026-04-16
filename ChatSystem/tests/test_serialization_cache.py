import pytest
from ChatSystem.core.conversation import Message
from datetime import datetime

def test_to_openai_format_caching():
    m = Message(role="user", content="hello")

    # First call
    fmt1 = m.to_openai_format()
    assert fmt1 == {"role": "user", "content": "hello"}
    assert m._cached_openai_format is not None

    # Second call (should be from cache)
    fmt2 = m.to_openai_format()
    assert fmt1 is not fmt2  # Should be a copy
    assert fmt1 == fmt2

    # Modify attribute should invalidate cache
    m.content = "world"
    assert m._cached_openai_format is None

    fmt3 = m.to_openai_format()
    assert fmt3 == {"role": "user", "content": "world"}

def test_model_dump_caching():
    m = Message(role="assistant", content="test")

    # First call
    dump1 = m.model_dump()
    assert dump1["content"] == "test"
    assert m._cached_dump is not None

    # Second call (should be from cache)
    dump2 = m.model_dump()
    assert dump1 is not dump2  # Should be a copy
    assert dump1 == dump2

    # Modify attribute should invalidate cache
    m.role = "user"
    assert m._cached_dump is None

    dump3 = m.model_dump()
    assert dump3["role"] == "user"

def test_cache_invalidation_tokens():
    m = Message(role="user", content="hi")
    from tiktoken import get_encoding
    encoding = get_encoding("o200k_base")

    # Populate tokens cache
    count1 = m.get_token_count(encoding)
    assert m.tokens is not None

    # Modify should clear tokens
    m.content = "bye" * 100
    assert m.tokens is None

    count2 = m.get_token_count(encoding)
    assert count1 != count2

def test_private_attr_modification_does_not_invalidate():
    m = Message(role="user", content="hi")
    m.to_openai_format()
    assert m._cached_openai_format is not None

    # Modifying private attr (starting with _) should NOT invalidate
    m._cached_dump = {"dummy": "data"}
    assert m._cached_openai_format is not None

    # Modifying tokens should NOT invalidate (it is public but handled separately)
    m.tokens = 10
    assert m._cached_openai_format is not None
