from price_analyst.normalization.query_normalizer import normalize_query, normalize_text


def test_normalize_text_handles_persian_digits_and_arabic_letters() -> None:
    assert normalize_text("كالا ۱۲۳ ي") == "کالا 123 ی"


def test_normalize_query_extracts_common_product_attributes() -> None:
    query = normalize_query("سامسونگ Galaxy S24 Ultra ۲۵۶ گیگ تیتانیوم مشکی")

    assert query.brand == "samsung"
    assert query.capacity == "256GB"
    assert query.color == "titanium black"
    assert query.model == "galaxy s24 ultra"
    assert query.attributes == {
        "brand": "samsung",
        "capacity": "256GB",
        "color": "titanium black",
    }
    assert query.variants == [query.normalized_text]


def test_normalize_query_rejects_blank_input() -> None:
    try:
        normalize_query("  ")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("blank query should fail")
