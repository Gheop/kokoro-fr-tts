from tts_engine import (
    EN_TO_FR,
    FRENCH_FIXES,
    PROPER_NAMES,
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


# --- Tests sigles ---


def test_api_sigle():
    assert _fix_pronunciation("L'API REST") == "L'a-pé-i REST"


def test_url_sigle():
    assert _fix_pronunciation("Ouvrez l'URL") == "Ouvrez l'u-erre-elle"


def test_html_sigle():
    assert _fix_pronunciation("Le code HTML") == "Le code ache-té-emme-elle"


def test_css_sigle():
    assert _fix_pronunciation("Du CSS moderne") == "Du cé-esse-esse moderne"


def test_gpu_sigle():
    assert _fix_pronunciation("Un GPU puissant") == "Un gé-pé-u puissant"


def test_cpu_sigle():
    assert _fix_pronunciation("Le CPU chauffe") == "Le cé-pé-u chauffe"


def test_ia_sigle():
    assert _fix_pronunciation("L'IA générative") == "L'i-a générative"


def test_sql_sigle():
    assert _fix_pronunciation("Une requête SQL") == "Une requête esse-ku-elle"


def test_pdf_sigle():
    assert _fix_pronunciation("Un fichier PDF") == "Un fichier pé-dé-effe"


def test_usb_sigle():
    assert _fix_pronunciation("Une clé USB") == "Une clé u-esse-bé"


# --- Tests anglicismes tech ---


def test_email():
    assert _fix_pronunciation("Envoyez un email") == "Envoyez un imèle"


def test_emails_plural():
    assert _fix_pronunciation("Les emails reçus") == "Les imèle reçus"


def test_software():
    assert _fix_pronunciation("Ce software est libre") == "Ce softwère est libre"


def test_hardware():
    assert _fix_pronunciation("Le hardware est neuf") == "Le ardwère est neuf"


def test_startup():
    assert _fix_pronunciation("Une startup innovante") == "Une starteupe innovante"


def test_cloud():
    assert _fix_pronunciation("Dans le cloud") == "Dans le claoude"


def test_feedback():
    assert _fix_pronunciation("Donnez du feedback") == "Donnez du fidbak"


def test_deadline():
    assert _fix_pronunciation("La deadline approche") == "La dèdlaille approche"


def test_bug():
    assert _fix_pronunciation("Un bug critique") == "Un beugue critique"


def test_feature():
    assert _fix_pronunciation("Une nouvelle feature") == "Une nouvelle fitcheure"


def test_token():
    assert _fix_pronunciation("Le token expire") == "Le tokène expire"


def test_streaming():
    assert _fix_pronunciation("En streaming live") == "En strimingue live"


def test_prompt():
    assert _fix_pronunciation("Un bon prompt") == "Un bon prompte"


def test_open_source():
    assert _fix_pronunciation("Un projet open source") == "Un projet opène-source"


def test_machine_learning():
    assert _fix_pronunciation("Le machine learning") == "Le machinn-leurnigne"


def test_deep_learning():
    assert _fix_pronunciation("Le deep learning") == "Le dip-leurnigne"


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


# --- Tests noms propres (case-sensitive) ---


def test_proper_names_dict_has_entries():
    assert len(PROPER_NAMES) > 0


def test_bill_gates_full():
    assert _fix_pronunciation("Bill Gates a dit que") == "Bil Guéïtse a dit que"


def test_elon_musk_full():
    assert (
        _fix_pronunciation("Elon Musk lance une fusée") == "Ilone Mosk lance une fusée"
    )


def test_steve_jobs_full():
    assert (
        _fix_pronunciation("Steve Jobs a créé Apple") == "Stive Djobze a créé Apeulle"
    )


def test_jeff_bezos_full():
    assert (
        _fix_pronunciation("Jeff Bezos dirige Amazon") == "Djef Bézosse dirige Amazone"
    )


def test_mark_zuckerberg_full():
    result = _fix_pronunciation("Mark Zuckerberg")
    assert result == "Mark Zokeurbergue"


def test_sam_altman_full():
    assert (
        _fix_pronunciation("Sam Altman dirige OpenAI")
        == "Sam Altmane dirige Opène-a-aille"
    )


def test_gates_last_name_only():
    assert _fix_pronunciation("Gates a investi") == "Guéïtse a investi"


def test_musk_last_name_only():
    assert _fix_pronunciation("Musk a tweeté") == "Mosk a tweeté"


def test_jobs_last_name_only():
    assert _fix_pronunciation("Jobs était visionnaire") == "Djobze était visionnaire"


def test_google():
    assert _fix_pronunciation("Google a annoncé") == "Gougueule a annoncé"


def test_microsoft():
    assert _fix_pronunciation("Microsoft rachète") == "Maïkrossofte rachète"


def test_openai():
    assert (
        _fix_pronunciation("OpenAI publie un modèle")
        == "Opène-a-aille publie un modèle"
    )


def test_nvidia():
    assert _fix_pronunciation("Nvidia domine le marché") == "Ènvidia domine le marché"


def test_spacex():
    assert _fix_pronunciation("SpaceX lance Starship") == "Spèïce-X lance Starship"


def test_proper_names_case_sensitive():
    """Les noms propres ne doivent pas matcher en minuscules."""
    # "gates" en minuscule ne doit pas être remplacé
    assert _fix_pronunciation("les gates du château") == "les gates du château"


def test_proper_names_in_sentence():
    """Plusieurs noms propres dans la même phrase."""
    result = _fix_pronunciation("Bill Gates et Elon Musk investissent dans OpenAI")
    assert "Bil Guéïtse" in result
    assert "Ilone Mosk" in result
    assert "Opène-a-aille" in result
