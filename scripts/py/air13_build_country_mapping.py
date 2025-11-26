# -*- coding: utf-8 -*-
"""
AIR-13 — Mapping country → ISO alpha-2 → region

Objectif
--------
À partir du dataset brut avion-par-avion (source/dataset.xlsx, feuille 'data'),
extraire la liste des pays réellement utilisés et maintenir un
fichier de mapping éditable à la main :

    source/country_region_mapping.csv

Colonnes du mapping :
- country       : nom du pays tel qu'il apparaît dans les données
- country_code  : code ISO alpha-2 (FR, US, DE, BR, ...)
- region        : région du monde (Europe, Africa, Asia, Middle East,
                  North America, South America, Caribbean, Oceania)

Usage
-----
    python scripts/air13_build_country_mapping.py
"""

from pathlib import Path
import pandas as pd

# ----- Librairies optionnelles pour les codes ISO / traduction -----
try:
    import pycountry
except ImportError:  
    pycountry = None
    print("[AIR-13] Attention : la librairie 'pycountry' n'est pas installée.")
    print("         Le remplissage automatique de 'country_code' sera limité.")

try:
    from googletrans import Translator
except ImportError:
    Translator = None
    print("[AIR-13] Attention : la librairie 'googletrans' n'est pas installée.")
    print("         Aucun essai de traduction fr→en ne sera fait avant pycountry.")


# Fichiers d'entrée / sortie
SRC_RAW = Path("source/dataset.xlsx")              # dataset brut (feuille 'data')
SHEET_RAW = "data"
DST_MAP = Path("source/country_region_mapping.csv")


# -------------- Dictionnaire country -> code ISO alpha-2 --------------
MANUAL_ALPHA2 = {
    "Afghanistan": "AF",
    "Afrique du Sud": "ZA",
    "Albanie": "AL",
    "Algérie": "DZ",
    "Allemagne": "DE",
    "Angola": "AO",
    "Anguilla": "AI",
    "Antigua-et-Barbuda": "AG",
    "Arabie saoudite": "SA",
    "Argentine": "AR",
    "Arménie": "AM",
    "Aruba": "AW",
    "Autriche": "AT",
    "Azerbaïdjan": "AZ",
    "Bahamas": "BS",
    "Bahreïn": "BH",
    "Bangladesh": "BD",
    "Belgique": "BE",
    "Belize": "BZ",
    "Bermudes": "BM",
    "Bhoutan": "BT",
    "Birmanie": "MM", 
    "Biélorussie": "BY",
    "Bolivie": "BO",
    "Bosnie-Herzégovine": "BA",
    "Botswana": "BW",
    "Brunei": "BN",
    "Brésil": "BR",
    "Bulgarie": "BG",
    "Burkina Faso": "BF",
    "Bénin": "BJ",
    "Cambodge": "KH",
    "Cameroun": "CM",
    "Canada": "CA",
    "Cap-Vert": "CV",
    "Chili": "CL",
    "Chypre": "CY",
    "Colombie": "CO",
    "Corée du Nord": "KP",
    "Corée du Sud": "KR",
    "Costa Rica": "CR",
    "Croatie": "HR",
    "Côte d'Ivoire": "CI",
    "Espagne": "ES",
    "Estonie": "EE",
    "Eswatini": "SZ",
    "Fidji": "FJ",
    "Finlande": "FI",
    "France": "FR",
    "Gabon": "GA",
    "Gambie": "GM",
    "Ghana": "GH",
    "Grèce": "GR",
    "Guatemala": "GT",
    "Guernesey": "GG",
    "Guinée équatoriale": "GQ",
    "Guyana": "GY",
    "Géorgie": "GE",
    "Honduras": "HN",
    "Hong Kong": "HK",
    "Hongrie": "HU",
    "Inde": "IN",
    "Irak": "IQ",
    "Iran": "IR",
    "Irlande": "IE",
    "Islande": "IS",
    "Italie": "IT",
    "Japon": "JP",
    "Jordanie": "JO",
    "Kazakhstan": "KZ",
    "Kenya": "KE",
    "Kirghizistan": "KG",
    "Kiribati": "KI",
    "Koweït": "KW",
    "Laos": "LA",
    "Lettonie": "LV",
    "Liban": "LB",
    "Libye": "LY",
    "Lituanie": "LT",
    "Luxembourg": "LU",
    "Macao": "MO",
    "Madagascar": "MG",
    "Malaisie": "MY",
    "Malawi": "MW",
    "Maldives": "MV",
    "Mali": "ML",
    "Malte": "MT",
    "Maurice": "MU",
    "Mauritanie": "MR",
    "Mexique": "MX",
    "Moldavie": "MD",
    "Monaco": "MC",
    "Monténégro": "ME",
    "Mozambique": "MZ",
    "Namibie": "NA",
    "Nicaragua": "NI",
    "Nigeria": "NG",
    "Nouvelle-Zélande": "NZ",
    "Népal": "NP",
    "Oman": "OM",
    "Ouganda": "UG",
    "Ouzbékistan": "UZ",
    "Pakistan": "PK",
    "Panama": "PA",
    "Papouasie-Nouvelle-Guinée": "PG",
    "Paraguay": "PY",
    "Pays-Bas": "NL",
    "Pologne": "PL",
    "Polynésie française": "PF",
    "Porto Rico": "PR",
    "Portugal": "PT",
    "Pérou": "PE",
    "Qatar": "QA",
    "Roumanie": "RO",
    "Russie": "RU",
    "Rwanda": "RW",
    "République centrafricaine": "CF",
    "République dominicaine": "DO",
    "République du Congo": "CG",
    "République démocratique du Congo": "CD",
    "République tchèque": "CZ",
    "Saint-Marin": "SM",
    "Saint-Vincent-et-les-Grenadines": "VC",
    "Samoa": "WS",
    "Serbie": "RS",
    "Seychelles": "SC",
    "Singapour": "SG",
    "Slovaquie": "SK",
    "Slovénie": "SI",
    "Somalie": "SO",
    "Soudan": "SD",
    "Sri Lanka": "LK",
    "Suisse": "CH",
    "Suriname": "SR",
    "Suède": "SE",
    "Svalbard et ile Jan Mayen": "SJ",
    "Syrie": "SY",
    "Sénégal": "SN",
    "Tadjikistan": "TJ",
    "Tanzanie": "TZ",
    "Taïwan": "TW",
    "Territoire britannique de l'océan Indien": "IO",
    "Thaïlande": "TH",
    "Timor oriental": "TL",
    "Togo": "TG",
    "Tonga": "TO",
    "Trinité-et-Tobago": "TT",
    "Tunisie": "TN",
    "Turkménistan": "TM",
    "Turquie": "TR",
    "Ukraine": "UA",
    "Uruguay": "UY",
    "Vanuatu": "VU",
    "Venezuela": "VE",
    "Vietnam": "VN",
    "Yémen": "YE",
    "Zambie": "ZM",
    "Zimbabwe": "ZW",
    "Égypte": "EG",
    "Émirats arabes unis": "AE",
    "Équateur": "EC",
    "Éthiopie": "ET",
    "Île de Man": "IM",
    "Îles Caïmans": "KY",
    "Îles Cocos": "CC",
    "Îles Féroé": "FO",
    "Îles Salomon": "SB",
    "Îles Turques-et-Caïques": "TC",
}

# -------------- Dictionnaire country -> région --------------
MANUAL_REGION = {
    "Afghanistan": "Asia",
    "Afrique du Sud": "Africa",
    "Albanie": "Europe",
    "Algérie": "Africa",
    "Allemagne": "Europe",
    "Angola": "Africa",
    "Anguilla": "Caribbean",
    "Antigua-et-Barbuda": "Caribbean",
    "Arabie saoudite": "Middle East",
    "Argentine": "South America",
    "Arménie": "Asia",
    "Aruba": "Caribbean",
    "Autriche": "Europe",
    "Azerbaïdjan": "Asia",
    "Bahamas": "Caribbean",
    "Bahreïn": "Middle East",
    "Bangladesh": "Asia",
    "Belgique": "Europe",
    "Belize": "North America",
    "Bermudes": "North America",
    "Bhoutan": "Asia",
    "Birmanie": "Asia",
    "Biélorussie": "Europe",
    "Bolivie": "South America",
    "Bosnie-Herzégovine": "Europe",
    "Botswana": "Africa",
    "Brunei": "Asia",
    "Brésil": "South America",
    "Bulgarie": "Europe",
    "Burkina Faso": "Africa",
    "Bénin": "Africa",
    "Cambodge": "Asia",
    "Cameroun": "Africa",
    "Canada": "North America",
    "Cap-Vert": "Africa",
    "Chili": "South America",
    "Chypre": "Europe",
    "Colombie": "South America",
    "Corée du Nord": "Asia",
    "Corée du Sud": "Asia",
    "Costa Rica": "North America",
    "Croatie": "Europe",
    "Côte d'Ivoire": "Africa",
    "Espagne": "Europe",
    "Estonie": "Europe",
    "Eswatini": "Africa",
    "Fidji": "Oceania",
    "Finlande": "Europe",
    "France": "Europe",
    "Gabon": "Africa",
    "Gambie": "Africa",
    "Ghana": "Africa",
    "Grèce": "Europe",
    "Guatemala": "North America",
    "Guernesey": "Europe",
    "Guinée équatoriale": "Africa",
    "Guyana": "South America",
    "Géorgie": "Asia",
    "Honduras": "North America",
    "Hong Kong": "Asia",
    "Hongrie": "Europe",
    "Inde": "Asia",
    "Irak": "Middle East",
    "Iran": "Middle East",
    "Irlande": "Europe",
    "Islande": "Europe",
    "Italie": "Europe",
    "Japon": "Asia",
    "Jordanie": "Middle East",
    "Kazakhstan": "Asia",
    "Kenya": "Africa",
    "Kirghizistan": "Asia",
    "Kiribati": "Oceania",
    "Koweït": "Middle East",
    "Laos": "Asia",
    "Lettonie": "Europe",
    "Liban": "Middle East",
    "Libye": "Africa",
    "Lituanie": "Europe",
    "Luxembourg": "Europe",
    "Macao": "Asia",
    "Madagascar": "Africa",
    "Malaisie": "Asia",
    "Malawi": "Africa",
    "Maldives": "Asia",
    "Mali": "Africa",
    "Malte": "Europe",
    "Maurice": "Africa",
    "Mauritanie": "Africa",
    "Mexique": "North America",
    "Moldavie": "Europe",
    "Monaco": "Europe",
    "Monténégro": "Europe",
    "Mozambique": "Africa",
    "Namibie": "Africa",
    "Nicaragua": "North America",
    "Nigeria": "Africa",
    "Nouvelle-Zélande": "Oceania",
    "Népal": "Asia",
    "Oman": "Middle East",
    "Ouganda": "Africa",
    "Ouzbékistan": "Asia",
    "Pakistan": "Asia",
    "Panama": "North America",
    "Papouasie-Nouvelle-Guinée": "Oceania",
    "Paraguay": "South America",
    "Pays-Bas": "Europe",
    "Pologne": "Europe",
    "Polynésie française": "Oceania",
    "Porto Rico": "Caribbean",
    "Portugal": "Europe",
    "Pérou": "South America",
    "Qatar": "Middle East",
    "Roumanie": "Europe",
    "Russie": "Europe",
    "Rwanda": "Africa",
    "République centrafricaine": "Africa",
    "République dominicaine": "Caribbean",
    "République du Congo": "Africa",
    "République démocratique du Congo": "Africa",
    "République tchèque": "Europe",
    "Saint-Marin": "Europe",
    "Saint-Vincent-et-les-Grenadines": "Caribbean",
    "Samoa": "Oceania",
    "Serbie": "Europe",
    "Seychelles": "Africa",
    "Singapour": "Asia",
    "Slovaquie": "Europe",
    "Slovénie": "Europe",
    "Somalie": "Africa",
    "Soudan": "Africa",
    "Sri Lanka": "Asia",
    "Suisse": "Europe",
    "Suriname": "South America",
    "Suède": "Europe",
    "Svalbard et ile Jan Mayen": "Europe",
    "Syrie": "Middle East",
    "Sénégal": "Africa",
    "Tadjikistan": "Asia",
    "Tanzanie": "Africa",
    "Taïwan": "Asia",
    "Territoire britannique de l'océan Indien": "Asia",
    "Thaïlande": "Asia",
    "Timor oriental": "Asia",
    "Togo": "Africa",
    "Tonga": "Oceania",
    "Trinité-et-Tobago": "Caribbean",
    "Tunisie": "Africa",
    "Turkménistan": "Asia",
    "Turquie": "Middle East",
    "Ukraine": "Europe",
    "Uruguay": "South America",
    "Vanuatu": "Oceania",
    "Venezuela": "South America",
    "Vietnam": "Asia",
    "Yémen": "Middle East",
    "Zambie": "Africa",
    "Zimbabwe": "Africa",
    "Égypte": "Africa",
    "Émirats arabes unis": "Middle East",
    "Équateur": "South America",
    "Éthiopie": "Africa",
    "Île de Man": "Europe",
    "Îles Caïmans": "Caribbean",
    "Îles Cocos": "Asia",
    "Îles Féroé": "Europe",
    "Îles Salomon": "Oceania",
    "Îles Turques-et-Caïques": "Caribbean",
}

TRANSLATION_CACHE: dict[str, str] = {}  # fr → en


def get_translator():
    """Instancie un Translator googletrans une seule fois."""
    if Translator is None:
        return None
    return Translator()


def translate_country_to_english(country: str, translator) -> str:
    """
    Traduit le nom de pays du français vers l'anglais en utilisant googletrans.
    Utilise un cache pour éviter les appels répétés.
    """
    country = (country or "").strip()
    if not country or translator is None:
        return ""

    if country in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[country]

    try:
        result = translator.translate(country, src="fr", dest="en")
        text_en = (result.text or "").strip()
    except Exception:
        text_en = ""

    TRANSLATION_CACHE[country] = text_en
    return text_en


def guess_iso_code(country: str, translator=None) -> str:
    """
    Devine le code ISO alpha-2 à partir d'un nom de pays.
    Priorité :
    1) MANUAL_ALPHA2
    2) pycountry.search_fuzzy(country)
    3) traduction fr→en + pycountry
    """
    country = (country or "").strip()
    if not country:
        return ""

    # 1) Dictionnaire manuel
    if country in MANUAL_ALPHA2:
        return MANUAL_ALPHA2[country]

    # 2) pycountry direct
    if pycountry is not None:
        try:
            match = pycountry.countries.search_fuzzy(country)[0]
            return match.alpha_2
        except (LookupError, AttributeError):
            pass

    # 3) pycountry après traduction
    if translator is not None and pycountry is not None:
        country_en = translate_country_to_english(country, translator)
        if country_en:
            try:
                match_en = pycountry.countries.search_fuzzy(country_en)[0]
                return match_en.alpha_2
            except (LookupError, AttributeError):
                pass

    return ""


def main() -> None:
    # ---------- 1) Charger le dataset brut ----------
    if not SRC_RAW.exists():
        raise SystemExit(f"[AIR-13] Introuvable : {SRC_RAW.resolve()}")

    raw = pd.read_excel(SRC_RAW, sheet_name=SHEET_RAW)

    if "country" not in raw.columns:
        raise SystemExit(
            "[AIR-13] Colonne 'country' absente dans source/dataset.xlsx "
            "(feuille 'data'). Vérifie le nom exact de la colonne."
        )

    # Liste unique des pays, triés
    countries = (
        raw["country"]
        .dropna()
        .astype(str)
        .str.strip()
        .sort_values()
        .unique()
    )

    # ---------- 2) Charger l'ancien mapping s'il existe ----------
    if DST_MAP.exists():
        mapping_old = pd.read_csv(DST_MAP, dtype=str).fillna("")
        mapping_old["country"] = mapping_old["country"].astype(str).str.strip()
        mapping_old = mapping_old.set_index("country")
    else:
        mapping_old = None

    # ---------- 3) Construire le nouveau mapping ----------
    rows = []
    for c in countries:
        country = str(c).strip()
        country_code = ""
        region = ""

        if mapping_old is not None and country in mapping_old.index:
            # On conserve les valeurs déjà saisies
            country_code = mapping_old.at[country, "country_code"]
            region = mapping_old.at[country, "region"]

        rows.append(
            {
                "country": country,
                "country_code": country_code,
                "region": region,
            }
        )

    mapping_new = pd.DataFrame(rows, columns=["country", "country_code", "region"])

    # ---------- 3bis) Remplissage automatique code + région ----------
    translator = get_translator()
    filled_codes = 0
    filled_regions = 0

    for idx, row in mapping_new.iterrows():
        country = row["country"]

        # 1) Région
        if not str(row["region"]).strip() and country in MANUAL_REGION:
            mapping_new.at[idx, "region"] = MANUAL_REGION[country]
            filled_regions += 1

        # 2) Code ISO
        if not str(row["country_code"]).strip():
            code = guess_iso_code(country, translator=translator)
            if code:
                mapping_new.at[idx, "country_code"] = code
                filled_codes += 1

    print(f"[AIR-13] Codes ISO remplis/ajustés automatiquement : {filled_codes}")
    print(f"[AIR-13] Régions remplies automatiquement : {filled_regions}")

    # ---------- 4) Sauvegarder ----------
    DST_MAP.parent.mkdir(parents=True, exist_ok=True)
    mapping_new.to_csv(DST_MAP, index=False, encoding="utf-8-sig")

    print(f"[AIR-13] Mapping pays écrit dans : {DST_MAP.resolve()}")
    print("         Tu peux corriger à la main si besoin, mais normalement")
    print("         'country_code' et 'region' sont déjà remplis pour ta liste actuelle.")


if __name__ == "__main__":
    main()
