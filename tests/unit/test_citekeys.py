from scholartools.services.citekeys import generate, resolve_collision


def _ref(family=None, year=None, authors=None):
    ref = {"type": "article-journal"}
    if authors is not None:
        ref["author"] = authors
    elif family:
        ref["author"] = [{"family": family, "given": "J."}]
    if year:
        ref["issued"] = {"date-parts": [[year]]}
    return ref


def test_generate_standard():
    assert generate(_ref("Smith", 2020)) == "smith2020"


def test_generate_normalizes_diacritics():
    # García → garcia (diacríticos eliminados, no preservados)
    assert generate(_ref("García", 2019)) == "garcia2019"


def test_generate_normalizes_compound():
    assert generate(_ref("García-Méndez", 2021)) == "garciamendez2021"


def test_generate_missing_author_returns_ref_prefix():
    key = generate(_ref(year=2020))
    assert key.startswith("ref")
    assert len(key) == 9  # "ref" + 6 hex chars


def test_generate_missing_year_returns_ref_prefix():
    key = generate(_ref(family="Smith"))
    assert key.startswith("ref")


def test_generate_missing_both_returns_ref_prefix():
    key = generate({})
    assert key.startswith("ref")


def test_generate_two_authors():
    ref = _ref(authors=[{"family": "Star"}, {"family": "Griesemer"}], year=1989)
    assert generate(ref) == "star_griesemer1989"


def test_generate_three_plus_authors():
    ref = _ref(
        authors=[{"family": "Anand"}, {"family": "Gupta"}, {"family": "Appel"}],
        year=2018,
    )
    assert generate(ref) == "anand_etal2018"


def test_generate_literal_author():
    ref = {
        "type": "book",
        "author": [{"literal": "John Smith"}],
        "issued": {"date-parts": [[2020]]},
    }
    assert generate(ref) == "smith2020"


def test_generate_issued_none():
    ref = {"type": "article-journal", "author": [{"family": "Smith"}], "issued": None}
    key = generate(ref)
    assert key.startswith("ref")


def test_resolve_collision_no_collision():
    assert resolve_collision("smith2020", set()) == "smith2020"


def test_resolve_collision_appends_suffix():
    existing = {"smith2020"}
    assert resolve_collision("smith2020", existing) == "smith2020a"


def test_resolve_collision_chains():
    existing = {"smith2020", "smith2020a", "smith2020b"}
    assert resolve_collision("smith2020", existing) == "smith2020c"


def test_resolve_collision_exhausts_letters():
    existing = {"smith2020"} | {f"smith2020{c}" for c in "abcdefghijklmnopqrstuvwxyz"}
    result = resolve_collision("smith2020", existing)
    assert result.startswith("smith2020a")
