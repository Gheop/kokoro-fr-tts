from tts_engine import (
    EN_TO_FR,
    FRENCH_FIXES,
    _fix_en_switches,
    _fix_pronunciation,
    _map_en_to_fr,
)


# --- Tests Layer 1 : _fix_pronunciation (text-level) ---


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


def test_blockchain_is_corrected():
    assert _fix_pronunciation("La blockchain est décentralisée") == (
        "La bloktchène est décentralisée"
    )


def test_blockchains_plural_is_corrected():
    assert _fix_pronunciation("Les blockchains publiques") == (
        "Les bloktchène publiques"
    )


def test_no_correction_needed():
    text = "Bonjour, comment allez-vous ?"
    assert _fix_pronunciation(text) == text


def test_french_fixes_dict_has_entries():
    assert len(FRENCH_FIXES) > 0


# --- Tests Layer 2 : _fix_en_switches (phoneme-level) ---


def test_fix_en_switches_dos():
    """Le mot 'dos' phonémisé en anglais est corrigé."""
    # espeak-ng produit : (^e^n)dˈɒs(^f^r)
    ps = "ʒˈi ˈe mˈal o (^e^n)dˈɒs(^f^r)"
    result = _fix_en_switches(ps)
    assert "(^e^n)" not in result
    assert "(^f^r)" not in result
    assert "ɒ" not in result  # voyelle anglaise remplacée
    assert "dˈɔs" in result  # ɒ → ɔ


def test_fix_en_switches_football():
    """'football' avec switch anglais est corrigé."""
    ps = "(^e^n)fˈʊtbɔːl(^f^r)"
    result = _fix_en_switches(ps)
    assert "ʊ" not in result  # ʊ → u
    assert "ː" not in result  # longueur supprimée
    assert "(^e^n)" not in result
    assert "fˈutbɔl" in result


def test_fix_en_switches_jogging():
    """'jogging' avec switch anglais et affriquée est corrigé."""
    ps = "(^e^n)d^ʒˈɒɡɪŋ(^f^r)"
    result = _fix_en_switches(ps)
    assert "ɒ" not in result
    assert "ɪ" not in result
    assert "(^e^n)" not in result


def test_fix_en_switches_pull():
    """'pull' avec switch anglais est corrigé."""
    ps = "(^e^n)pˈʊl(^f^r)"
    result = _fix_en_switches(ps)
    assert "ʊ" not in result
    assert "pˈul" in result


def test_fix_en_switches_multiple():
    """Plusieurs switches dans la même phrase sont tous corrigés."""
    ps = "ʒˈɛm lə- (^e^n)fˈʊtbɔːl(^f^r) e lə- (^e^n)d^ʒˈɒɡɪŋ(^f^r)"
    result = _fix_en_switches(ps)
    assert "(^e^n)" not in result
    assert "(^f^r)" not in result
    assert "ʊ" not in result
    assert "ɒ" not in result


def test_fix_en_switches_no_switch():
    """Du texte français sans switch n'est pas modifié."""
    ps = "bɔ̃ʒˈuʁ kɔmˈɑ̃ ale vˈu"
    assert _fix_en_switches(ps) == ps


def test_fix_en_switches_weekend():
    """'weekend' avec switch anglais est corrigé."""
    ps = "(^e^n)wiːkˈɛnd(^f^r)"
    result = _fix_en_switches(ps)
    assert "ː" not in result
    assert "(^e^n)" not in result
    assert "wikˈɛnd" in result


# --- Tests _map_en_to_fr ---


def test_map_en_to_fr_diphthongs():
    """Les diphthongues anglaises sont converties."""
    assert _map_en_to_fr("a^ɪ") == "aj"
    assert _map_en_to_fr("a^ʊ") == "o"
    assert _map_en_to_fr("e^ɪ") == "e"


def test_map_en_to_fr_vowels():
    """Les voyelles anglaises sont converties."""
    assert _map_en_to_fr("ɒ") == "ɔ"
    assert _map_en_to_fr("ʊ") == "u"
    assert _map_en_to_fr("ɪ") == "i"
    assert _map_en_to_fr("æ") == "a"


def test_map_en_to_fr_consonants():
    """Les consonnes anglaises sont converties."""
    assert _map_en_to_fr("θ") == "s"
    assert _map_en_to_fr("ð") == "z"
    assert _map_en_to_fr("ɹ") == "ʁ"


def test_map_en_to_fr_length_removed():
    """Les marques de longueur sont supprimées."""
    assert _map_en_to_fr("iː") == "i"
    assert _map_en_to_fr("ɔː") == "ɔ"


def test_en_to_fr_table_not_empty():
    assert len(EN_TO_FR) > 0
