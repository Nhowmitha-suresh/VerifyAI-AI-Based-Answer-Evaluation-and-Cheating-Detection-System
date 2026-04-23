import re

def tokenize(text):
    return re.findall(r"\w+", (text or "").lower())

def keyword_score(keywords, answer):
    if not keywords:
        return 0.0, []
    tokens = tokenize(answer)
    present = [k for k in keywords if k.lower() in tokens]
    return (len(present) / len(keywords)) if keywords else 0.0, present

def semantic_score(question, answer):
    # Simple lexical overlap fallback (fast, zero-deps). For production use embeddings.
    q_tokens = set(tokenize(question))
    a_tokens = set(tokenize(answer))
    if not q_tokens or not a_tokens:
        return 0.0
    overlap = len(q_tokens & a_tokens) / len(q_tokens | a_tokens)
    return overlap

def score_answer(question, answer, keywords=None):
    if keywords is None:
        keywords = []
    k_score, present = keyword_score(keywords, answer)
    s_score = semantic_score(question, answer)
    # weighted score: semantic more important
    final = 0.6 * s_score + 0.4 * k_score
    details = {"keyword_score": round(k_score, 3), "present_keywords": present, "semantic_score": round(s_score, 3)}
    return round(final * 100, 2), details
