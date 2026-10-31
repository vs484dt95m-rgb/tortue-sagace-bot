
import json
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter


BASE_DIR = Path(__file__).parent
KNOWLEDGE_FILE = BASE_DIR / "knowledge.json"

UNKNOWN_ANSWER = (
    "Je ne connais pas la réponse à cette question "
    "dans ma documentation. Peux-tu préciser ta question, "
    "s'il te plaît ?"
)

# Expressions familières et synonymes
SYNONYMS = {
    "fric": "argent financement",
    "thune": "argent financement",
    "oseille": "argent financement",
    "blinde": "cout financement",
    "cher": "cout",
    "retraites": "retraite pension",
    "taf": "travail emploi",
    "boulot": "travail emploi",
    "bosser": "travail emploi",
    "patron": "entreprise employeur",
    "riche": "richesse fortune",
    "blindage": "protection",
    "climat": "ecologie environnement",
    "bagnole": "voiture transport",
    "hosto": "hopital sante",
    "toubib": "medecin sante",
    "baraque": "logement",
    "loyer": "logement immobilier",
    "impots": "fiscalite taxation",
    "taxer": "fiscalite taxation",
    "taxation": "fiscalite",
    "sixieme": "institutions constitution",
    "6e": "institutions constitution",
    "sixième": "institutions constitution",
    "reforme": "proposition changement",
    "galere": "difficulte",
    "comment": "fonctionnement explication",
    "pourquoi": "raison explication",
    "combien": "cout montant financement",
}

STOP_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de",
    "et", "ou", "mais", "donc", "que", "qui", "quoi",
    "est", "sont", "dans", "sur", "avec", "pour", "par",
    "ce", "cet", "cette", "ces", "mon", "ma", "mes",
    "ton", "ta", "tes", "son", "sa", "ses", "je", "tu",
    "il", "elle", "on", "nous", "vous", "ils", "elles",
    "a", "au", "aux", "en", "y", "ne", "pas", "plus",
    "comment", "pourquoi", "estce", "est-ce", "cest",
    "c'est", "ca", "cela", "fait", "faire", "truc",
    "votre", "vos", "leur", "leurs"
}


def normalize(text):
    """Normalise les textes pour faciliter leur comparaison."""

    text = text.lower().strip()

    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )

    text = text.replace("’", "'")
    text = re.sub(r"[^a-z0-9\s'-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def expand_synonyms(text):
    """Ajoute les synonymes et expressions familières."""

    words = normalize(text).split()
    expanded = list(words)

    for word in words:
        if word in SYNONYMS:
            expanded.extend(SYNONYMS[word].split())

    return expanded


def get_terms(text):
    """Extrait les termes significatifs."""

    words = expand_synonyms(text)

    return {
        word for word in words
        if len(word) > 2 and word not in STOP_WORDS
    }


def load_knowledge():
    """Charge la base documentaire."""

    if not KNOWLEDGE_FILE.exists():
        return []

    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            return []

        return [
            item for item in data
            if isinstance(item, dict)
            and item.get("title")
            and item.get("answer")
        ]

    except (json.JSONDecodeError, OSError):
        return []


def similarity(a, b):
    """Compare deux expressions."""

    return SequenceMatcher(
        None,
        normalize(a),
        normalize(b)
    ).ratio()


def score_document(question, document):
    """Calcule la pertinence d'un document."""

    question_terms = get_terms(question)

    if not question_terms:
        return 0

    keywords = document.get("keywords", [])
    title = document.get("title", "")
    answer = document.get("answer", "")
    category = document.get("category", "")

    keyword_terms = set()

    for keyword in keywords:
        keyword_terms.update(get_terms(str(keyword)))

    title_terms = get_terms(title)
    answer_terms = get_terms(answer)
    category_terms = get_terms(category)

    score = 0

    for term in question_terms:
        if term in keyword_terms:
            score += 4

        elif term in title_terms:
            score += 3

        elif term in category_terms:
            score += 2

        elif term in answer_terms:
            score += 1

        else:
            # Tolérance limitée aux petites fautes
            candidates = keyword_terms | title_terms

            if any(
                len(term) >= 5
                and similarity(term, candidate) >= 0.86
                for candidate in candidates
            ):
                score += 1

    # La précision augmente avec plusieurs mots concordants
    return score


def search(question, minimum_score=4):
    """
    Recherche une réponse dans la documentation.

    Retourne None si les éléments disponibles
    ne permettent pas une réponse suffisamment fiable.
    """

    documents = load_knowledge()

    if not documents:
        return None

    ranked = []

    for document in documents:
        score = score_document(question, document)

        if score >= minimum_score:
            ranked.append((score, document))

    if not ranked:
        return None

    ranked.sort(key=lambda item: item[0], reverse=True)

    best_score, best_document = ranked[0]

    # Si deux réponses sont presque aussi pertinentes,
    # on évite de choisir arbitrairement.
    if len(ranked) > 1:
        second_score, second_document = ranked[1]

        if (
            best_score == second_score
            and best_document.get("category")
            != second_document.get("category")
        ):
            return None

    return best_document


def format_answer(document):
    """Prépare une réponse structurée."""

    response = (
        f"📖 {document['title']}\n\n"
        f"{document['answer']}"
    )

    sources = document.get("sources", [])

    if sources:
        response += "\n\n📚 Sources :\n"

        for source in sources:
            response += f"• {source}\n"

    response += (
        "\n\n🐢 Tortue Sagace\n"
        "Tu souhaites approfondir ce sujet ?"
    )

    return response


def answer(question):
    """Point d'entrée principal du moteur."""

    if not question or not question.strip():
        return UNKNOWN_ANSWER

    document = search(question)

    if document is None:
        return UNKNOWN_ANSWER

    return format_answer(document)
