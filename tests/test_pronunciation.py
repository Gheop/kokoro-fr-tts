from tts_engine import FRENCH_FIXES, _fix_pronunciation


def test_dos_is_corrected():
    assert _fix_pronunciation("J'ai mal au dos") == "J'ai mal au deau"


def test_pull_is_corrected():
    assert _fix_pronunciation("Il porte un pull rouge") == "Il porte un pul rouge"


def test_case_insensitive():
    """La casse du remplacement n'est pas préservée, mais c'est OK pour le TTS."""
    assert _fix_pronunciation("Dos à dos") == "deau à deau"


def test_no_partial_match():
    """Ne doit pas corriger les mots contenant 'dos' ou 'pull' comme sous-chaîne."""
    assert _fix_pronunciation("endosser") == "endosser"
    assert _fix_pronunciation("pullover") == "pullover"


def test_no_correction_needed():
    text = "Bonjour, comment allez-vous ?"
    assert _fix_pronunciation(text) == text


def test_french_fixes_dict_has_entries():
    assert len(FRENCH_FIXES) > 0
