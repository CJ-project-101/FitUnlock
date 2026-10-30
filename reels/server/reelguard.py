"""ReelGuard: comment classifier (safe / abusive / threatening).

Two independent detectors, and the more serious result wins:
  1. RULES: weighted word lists and threat patterns (fast, explainable, work offline)
  2. MODEL: a pretrained toxicity model (Detoxify) that understands context (optional)

Model setup:  pip install detoxify     (installs PyTorch; weights download on first run)
Env vars:     REELGUARD_MODEL = unbiased (default) | unbiased-small | multilingual | original | off
Extra rule terms: reelguard_terms.txt next to this file (one per line, optional ",weight")
"""
import os
import re
import threading
import unicodedata
from pathlib import Path

MODEL_NAME = os.getenv("REELGUARD_MODEL", "unbiased").strip().lower()
RULE_AT = float(os.getenv("REELGUARD_RULE_AT", "0.50"))             # rule score that counts as a flag
ML_ABUSE_AT = float(os.getenv("REELGUARD_ML_ABUSE_AT", "0.60"))     # model score that counts as abusive
ML_THREAT_AT = float(os.getenv("REELGUARD_ML_THREAT_AT", "0.60"))   # model score that counts as a threat

# ---------------------------------------------------------------- rules: abuse
PROFANITY = {"fuck": .5, "shit": .5, "bitch": .55, "asshole": .6, "bastard": .55, "cunt": .7,
             "slut": .7, "whore": .7, "dumbass": .6, "jackass": .5, "dick": .35, "piss": .25}
INSULTS = {"idiot": .35, "stupid": .35, "moron": .4, "dumb": .3, "loser": .35, "ugly": .35,
           "trash": .3, "garbage": .3, "pathetic": .35, "worthless": .45, "useless": .35,
           "disgusting": .35, "creep": .35, "scum": .45, "freak": .35, "clown": .2}
PHRASES = [   # (regex, weight, reason)
    (r"\bshut (?:up|it|your (?:mouth|face))\b", .4, "tells someone to shut up"),
    (r"\b(?:nobody|no one) (?:likes|loves|wants|cares about) you\b", .65, "attacks the person"),
    (r"\bi (?:hate|despise) you\b", .55, "expresses hate towards a person"),
    (r"\byou (?:suck|stink|are a joke|are a disgrace|are a waste of (?:space|time|oxygen|air))\b", .55, "personal insult"),
    (r"\bwaste of (?:space|oxygen|air|skin)\b", .5, "personal insult"),
    (r"\bpiece of (?:shit|trash|garbage|crap)\b", .8, "personal insult"),
]

# -------------------------------------------------------------- rules: threats
_V = "kill|murder|stab|shoot|strangle|rape|slaughter|behead|beat|hurt|punch|slap|bash|smash|choke"
_WHO = r"(?:him|her|them|everyone|these people|that (?:guy|girl|man|woman|idiot|bastard|bitch|asshole|loser))"

STRONG = [    # clear on their own
    (r"\b(?:kill|hang|off|end|harm|hurt) (?:yourself|your self)\b", .95, "encourages self-harm"),
    (r"\bkys\b", .95, "encourages self-harm"),
    (r"\bgo (?:and )?(?:die|kill yourself|jump)\b", .95, "wishes harm on someone"),
    (r"\b(?:i )?(?:hope|wish) you (?:die|get killed|get hurt|suffer|rot|burn)\b", .9, "wishes harm on someone"),
    (r"\byou (?:deserve to|should) (?:die|suffer|burn|rot|be killed|be hurt)\b", .9, "wishes harm on someone"),
    (r"\byou (?:are|will be) (?:dead|done|finished)\b", .85, "threatens someone"),
    (r"\bwatch your back\b", .8, "threatens someone"),
    (r"\bi know where you (?:live|stay|work|sleep|study)\b", .95, "stalking or intimidation"),
    (r"\bcoming for you\b", .85, "threatens someone"),
    (r"\byou will (?:pay|regret|suffer|die)\b", .85, "threatens someone"),
    (r"\b(?:find|hunt|track) you (?:down|and)\b", .9, "threatens someone"),
    (r"\b(?:i|we) (?:will|am going to|shall|can|want to|would like to) (?:\w+ ){0,2}?(?:%s) (?:\w+ ){0,3}?(?:you|your|him|her|them)\b" % _V,
     .95, "threatens violence"),
]
WEAK = [      # suspicious, but can be a joke: counted only when the model agrees (or is not installed)
    (r"\b(?:%s)\b(?: \w+){0,2}? you\b" % _V, .7, "violent words aimed at you"),
    (r"\b(?:kill|murder|stab|shoot|strangle|rape|slaughter|behead|beat up)\b (?:\w+ ){0,2}?%s\b" % _WHO,
     .6, "calls for violence against someone"),
]
SAFE = [      # harmless phrases that would otherwise look violent or rude
    r"\bkilling it\b", r"\bkilled it\b", r"\bkill it\b", r"\bi(?: am|'m|m) dead\b", r"\bdead lol\b",
    r"\bdying (?:of|from) laugh\w*\b", r"\bthe shit\b", r"\bbad ?ass\b",
    r"\b(?:beat|destroy|crush) (?:you|your|him|her|them) (?:at|in|to)\b",
    r"\b(?:this|that|it|joke|video|reel) (?:\w+ )?(?:will|would|might|could|is going to) kill you\b",
]
_NEG = re.compile(r"\b(?:never|not|dont|don't|do not|wont|won't|wouldnt|wouldn't|cant|can't|cannot|no)\b")

_APOS = [("i'll", "i will"), ("i'm", "i am"), ("you're", "you are"), ("you'll", "you will"), ("i'd", "i would")]
_TOKEN = {"u": "you", "ur": "your", "ya": "you", "youre": "you are", "im": "i am",
          "gonna": "going to", "imma": "i am going to", "wanna": "want to"}
_SECOND = re.compile(r"\b(?:you|your|yourself|u|ur|ya|youre)\b")
_VOWELS = "aeiou"


def _obf(word):
    """Regex for a word that also catches f*ck, f u c k, fuuuck, fck ..."""
    parts = []
    for ch in word:
        if ch in _VOWELS:
            parts.append(r"(?:%s|[@*#$%%!])*" % ch)       # a vowel may be swapped for a symbol or dropped
        else:
            parts.append(re.escape(ch) + "+")
    return r"(?<![a-z])" + r"[\W_]*".join(parts) + r"(?![a-z])"


def _custom():
    out, p = {}, Path(__file__).with_name("reelguard_terms.txt")
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip().lower()
            if line and not line.startswith("#"):
                word, _, w = line.partition(",")
                try:
                    out[word.strip()] = float(w) if w.strip() else .5
                except ValueError:
                    out[word.strip()] = .5
    return out


_TERMS = ([(re.compile(_obf(w)), v, "profanity", w) for w, v in PROFANITY.items()] +
          [(re.compile(_obf(w)), v, "insult", w) for w, v in INSULTS.items()] +
          [(re.compile(_obf(w)), v, "flagged term", w) for w, v in _custom().items()])
_PHRASES = [(re.compile(p), w, r) for p, w, r in PHRASES]
_STRONG = [(re.compile(p), w, r) for p, w, r in STRONG]
_WEAK = [(re.compile(p), w, r) for p, w, r in WEAK]
_SAFE = [re.compile(p) for p in SAFE]


def _clean(text):
    t = (text or "").replace("\u2019", "'").replace("\u2018", "'")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)                 # soooo -> soo
    return re.sub(r"\s+", " ", t).strip()


def _expand(t):
    for a, b in _APOS:
        t = t.replace(a, b)
    return re.sub(r"\b(?:%s)\b" % "|".join(_TOKEN), lambda m: _TOKEN[m.group(0)], t)


def _prepare(text):
    t1 = _clean(text)
    t2 = _expand(t1)
    for p in _SAFE:
        t1, t2 = p.sub(" ", t1), p.sub(" ", t2)
    return t1, t2


def _threat_hits(patterns, t):
    """Best weight and the reasons for a list of threat patterns. 'I would never hurt you' is ignored."""
    best, reasons = 0.0, []
    for rx, w, reason in patterns:
        for m in rx.finditer(t):
            if _NEG.search(t[max(0, m.start() - 25):m.end()]):
                continue
            best = max(best, w)
            reasons.append(reason)
            break
    return best, list(dict.fromkeys(reasons))


def _abuse_rules(t1, t2):
    """1 - (1-w1)(1-w2)...; a word aimed at someone ("you idiot", "fuck you", "@name idiot") counts more."""
    keep, reasons = 1.0, []
    for rx, w, kind, word in _TERMS:
        for m in rx.finditer(t1):
            before, after = t1[max(0, m.start() - 30):m.start()], t1[m.end():m.end() + 14]
            directed = bool(_SECOND.search(before) or "@" in before or re.match(r"\s*(?:you|your|u|off)\b", after))
            keep *= 1 - (min(.95, w * 1.6) if directed else w)
            reasons.append(f"{kind} \"{m.group(0).strip()}\"" + (" aimed at someone" if directed else ""))
    for rx, w, reason in _PHRASES:
        if rx.search(t2):
            keep *= 1 - w
            reasons.append(reason)
    return round(1 - keep, 2), list(dict.fromkeys(reasons))


# ----------------------------------------------------------------- the model
_ml = None
_state = "off" if MODEL_NAME == "off" else "idle"          # idle -> loading -> ready | unavailable | off
_infer = threading.Lock()
_FRIENDLY = {"threat": "threat", "toxicity": "toxic", "toxic": "toxic", "severe_toxicity": "severely toxic",
             "severe_toxic": "severely toxic", "obscene": "obscene language", "insult": "insult",
             "identity_attack": "attack on identity", "identity_hate": "attack on identity"}
_ABUSE_KEYS = ("toxicity", "toxic", "severe_toxicity", "severe_toxic", "obscene", "insult",
               "identity_attack", "identity_hate")


def _load_ml():
    global _ml, _state
    if _state in ("off", "loading", "ready"):
        return
    _state = "loading"
    try:
        from detoxify import Detoxify
        _ml = Detoxify(MODEL_NAME)
        _state = "ready"
        print(f"[ReelGuard] model '{MODEL_NAME}' loaded.")
    except Exception as e:
        _state = "unavailable"
        print(f"[ReelGuard] model not available ({type(e).__name__}: {e}). Using rules only.")


def status():
    if _state == "ready":
        return f"Model ({MODEL_NAME}) + rules"
    if _state in ("idle", "loading"):
        return "Loading model... rules only for now"
    if _state == "off":
        return "Rules only (model turned off)"
    return "Rules only (model not installed)"


def _ml_scores(text):
    if _state != "ready":
        return None
    try:
        with _infer:
            raw = _ml.predict(text[:500])
        return {k: float(v) for k, v in raw.items()}
    except Exception as e:
        print(f"[ReelGuard] model error: {e}")
        return None


# ----------------------------------------------------------------- the verdict
def classify(text):
    """-> {"label": safe|abusive|threatening, "score": 0-1, "reasons": [...], "terms": [], "engine": "..."}"""
    t1, t2 = _prepare(text)
    strong, strong_why = _threat_hits(_STRONG, t2)
    weak, weak_why = _threat_hits(_WEAK, t2)
    rule_abuse, abuse_why = _abuse_rules(t1, t2)

    ml = _ml_scores(text)
    p_threat = p_abuse = 0.0
    ml_why = []
    if ml:
        p_threat = ml.get("threat", 0.0)
        p_abuse = max((ml.get(k, 0.0) for k in _ABUSE_KEYS), default=0.0)
        seen = {}
        for name, label in _FRIENDLY.items():
            if ml.get(name, 0.0) >= .3:
                seen[label] = max(seen.get(label, 0.0), ml[name])
        ml_why = [f"model: {label} {round(v * 100)}%" for label, v in sorted(seen.items(), key=lambda x: -x[1])]

    # a weak pattern ("kill you") only counts when the model also sees something wrong, or no model is running
    weak_ok = weak > 0 and (ml is None or p_threat >= .15 or p_abuse >= .5)
    threat_score = max(strong, weak if weak_ok else 0.0, p_threat)
    is_threat = strong >= RULE_AT or (weak_ok and weak >= RULE_AT) or p_threat >= ML_THREAT_AT
    abuse_score = max(rule_abuse, p_abuse)
    is_abuse = rule_abuse >= RULE_AT or p_abuse >= ML_ABUSE_AT
    engine = "model + rules" if ml else "rules"

    if is_threat:
        reasons = strong_why + (weak_why if weak_ok else []) + ml_why
        return {"label": "threatening", "score": round(threat_score, 2),
                "reasons": list(dict.fromkeys(reasons)), "terms": [], "engine": engine}
    if is_abuse:
        return {"label": "abusive", "score": round(abuse_score, 2),
                "reasons": list(dict.fromkeys(abuse_why + ml_why)), "terms": [], "engine": engine}
    return {"label": "safe", "score": round(max(threat_score, abuse_score), 2),
            "reasons": [], "terms": [], "engine": engine}


if __name__ != "__main__":
    threading.Thread(target=_load_ml, daemon=True).start()       # load the model without delaying the server


if __name__ == "__main__":
    _load_ml()
    print("engine:", status(), "\n")
    tests = [("Great video!", "safe"), ("you are so stupid", "abusive"), ("this is the shit lol", "safe"),
             ("I will find you and hurt you", "threatening"), ("kill yourself", "threatening"),
             ("fuck", "abusive"), ("hunt you down", "threatening"), ("kill you", "threatening"),
             ("will beat you kill that bastard", "threatening"), ("kill that bastard", "threatening"),
             ("bastard", "abusive"), ("you're killing it!", "safe"), ("I'll beat you at chess", "safe"),
             ("I would never hurt you", "safe"), ("this joke will kill you lol", "safe")]
    for s, want in tests:
        v = classify(s)
        print(f"{'ok ' if v['label'] == want else 'DIFF'} {v['label']:12} {v['score']:.2f}  {s}   ({'; '.join(v['reasons'])})")