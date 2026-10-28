from app.service import nonempty_properties, title_matches

def test_nonempty_properties_omits_blank_values():
    result = nonempty_properties({"firstname": "Ada", "lastname": "", "phone": None},
                                 {"firstname": "firstname", "lastname": "lastname", "phone": "phone"})
    assert result == {"firstname": "Ada"}

def test_title_filter_matches_case_insensitively():
    assert title_matches("Chief Technology Officer", ["technology officer"])
    assert not title_matches("Marketing Manager", ["technology officer"])

def test_empty_filter_allows_all():
    assert title_matches("Any Title", [])
