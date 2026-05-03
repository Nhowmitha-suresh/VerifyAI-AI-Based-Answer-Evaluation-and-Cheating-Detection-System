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


def grammar_score_text(answer):
    """Return grammar score on 0-10 scale. Try to use language_tool_python if available,
    otherwise use a simple heuristic based on punctuation, average sentence length, and error-prone patterns.
    """
    text = (answer or "").strip()
    if not text:
        return 0
    # Try language_tool_python for better accuracy
    try:
        import language_tool_python
        tool = language_tool_python.LanguageTool('en-US')
        matches = tool.check(text)
        errs = len([m for m in matches if m.ruleId != 'WHITESPACE_RULE'])
        # Map errors to 0-10: 0 errors -> 10, 20+ errors -> 0
        score = max(0, min(10, int(round(10 * (1 - (errs / 20.0))))))
        return score
    except Exception:
        # Fallback heuristic
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_len = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
        # Penalty for very long or very short sentences
        penalty = 0
        if avg_len > 30:
            penalty += min(5, int((avg_len - 30) / 6))
        if avg_len < 6:
            penalty += 1
        # punctuation density
        punct = sum(1 for c in text if c in '.,;:!?')
        punct_density = punct / max(1, len(text.split()))
        if punct_density < 0.2:
            penalty += 1
        base = 9
        score = max(0, base - penalty)
        return int(score)


def genuineness_score_text(answer):
    """Return a genuineness score (0-10) based on filler words, lexical variability, and length heuristics.
    This is a heuristic estimate and should be replaced by voice/authenticity models in production.
    """
    text = (answer or "").lower()
    if not text:
        return 0
    words = tokenize(text)
    total = len(words)
    unique = len(set(words))
    variability = (unique / total) if total else 0.0
    fillers = {'um','uh','like','you','know','actually','so','i','mean','basically'}
    filler_count = sum(1 for w in words if w in fillers)
    filler_ratio = (filler_count / total) if total else 0.0
    # Start from 10 and subtract for filler ratio and low variability
    score = 10
    score -= int(min(6, filler_ratio * 12))
    if variability < 0.3:
        score -= 3
    elif variability < 0.5:
        score -= 1
    # length bonus (very short answers are penalized)
    if total < 8:
        score -= 2
    return max(0, min(10, int(score)))
