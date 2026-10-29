"""Voiceover for the YouTube Shorts: Kokoro (British voice bf_emma) via onnxruntime.

Words become phonemes in this order:
  1. SAY        spoken forms for names, e.g. RTÉ -> "R T E"
  2. FIXED      hand-written British pronunciations
  3. cmudict    US dictionary, converted to non-rhotic British vowels
  4. espeak-ng  if installed (it is in the YouTube Short workflow)
  5. spelled out letter by letter, and reported, so it can be added to FIXED

The model, voices, symbol list and dictionary are data files, downloaded by
scripts/video/fetch_assets.sh into $VIDEO_ASSETS (default ~/.cache/onair-video).
"""
import json
import os
import re
import shutil
import subprocess

import numpy as np

ASSETS = os.environ.get("VIDEO_ASSETS", os.path.expanduser("~/.cache/onair-video"))
SR = 24000
VOICE = "bf_emma"

# Spoken forms. Applied to the voiceover text only; captions keep the written form.
SAY = [
    (r"onairireland\.ie", "on air ireland dot I E"),
    (r"RTÉ2", "R T E two"),
    (r"RTÉ", "R T E"),
    (r"TG4", "T G four"),
    (r"TNT", "T N T"),
    (r"URC", "U R C"),
    (r"PDC", "P D C"),
    (r"GAA\+", "G A A plus"),
    (r"GAA", "G A A"),
    (r"Disney\+", "Disney plus"),
    (r"Paramount\+", "Paramount plus"),
    (r"Apple TV", "Apple T V"),
    (r"\bTV\b", "T V"),
    (r"\bF1\b", "Formula one"),
    (r"\bNOW\b", "now"),
    (r"LaLiga", "La Liga"),
    (r"\b(\d{1,2})pm\b", lambda m: f"{m.group(1)} P M"),
    (r"\b(\d{1,2})am\b", lambda m: f"{m.group(1)} A M"),
    (r"€(\d+)\.(\d\d)", lambda m: f"{m.group(1)} euro {m.group(2)}"),
    (r"€(\d+)", lambda m: f"{m.group(1)} euro"),
    (r"&", " and "),
    (r"\+", " plus "),
]

# Hand-written British pronunciations (Kokoro symbols: A=eɪ I=aɪ Q=əʊ W=aʊ Y=ɔɪ).
FIXED = {
    "premier": "pɹˈɛmiə",
    "liga": "lˈiːɡə",
    "la": "lˈæ",
    "leinster": "lˈɛnstə",
    "munster": "mˈʌnstə",
    "ulster": "ˈʌlstə",
    "connacht": "kˈɒnəkt",
    "saorview": "sˈiːəvjuː",
    "tg4": "tˌiːʤiːfˈɔː",
    "adare": "ədˈɛː",
    "manor": "mˈænə",
    "dazn": "dˈæzən",
    "iplayer": "ˈIplˌAə", "britbox": "bɹˈɪtbɒks", "bundesliga": "bˈʊndəslˌiːɡə",
    "firestick": "fˈIəstɪk", "freesat": "fɹˈiːsæt", "freeview": "fɹˈiːvjuː", "hayu": "hˈAjuː",
    "hisense": "hˈIsɛns", "lg": "ˌɛlʤˈiː", "ligue": "lˈiːɡ", "motogp": "mˈQtQʤˌiːpˈiː",
    "mubi": "mˈuːbi", "rakuten": "ɹˈækʊtɛn", "roku": "ɹˈQkuː", "serie": "sˈɛɹiə",
    "soundbar": "sˈWndbɑː",
    "pm": "pˌiːˈɛm",
    "tuesday": "tjˈuːzdA", "thursday": "θˈɜːzdA", "saturday": "sˈætədA",
    "thirty": "θˈɜːti", "forty": "fˈɔːti", "eighty": "ˈAti", "ninety": "nˈInti",
    "ie": "ˌaɪˈiː",
    "e": "ˈiː",
    # weak forms of common short words
    "a": "ə", "an": "ən", "the": "ðə", "of": "əv", "to": "tə", "for": "fə",
    "and": "ənd", "at": "ət", "from": "fɹəm", "or": "ɔː", "but": "bət",
    "has": "hæz", "is": "ɪz", "are": "ɑː", "your": "jɔː", "you": "juː",
    "on": "ɒn", "in": "ɪn", "it": "ɪt", "its": "ɪts", "it's": "ɪts",
}

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
CONS = {"B": "b", "CH": "ʧ", "D": "d", "DH": "ð", "F": "f", "G": "ɡ", "HH": "h", "JH": "ʤ",
        "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p", "R": "ɹ", "S": "s",
        "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ"}
# Vowel followed by an R that isn't followed by a vowel (non-rhotic British).
VOWEL_R = {"AA": "ɑː", "AO": "ɔː", "IH": "ɪə", "IY": "ɪə", "EH": "ɛː", "EY": "ɛː",
           "UH": "ʊə", "UW": "ʊə", "AY": "Iə", "AW": "Wə", "OW": "ɔː", "AE": "ɑː", "AH": "ɜː"}

_vocab = _cmu = _sess = _voices = None
unknown_words = []   # words that had to be spelled out


def _load():
    global _vocab, _cmu
    if _vocab is None:
        with open(os.path.join(ASSETS, "config.json"), encoding="utf-8") as fh:
            _vocab = json.load(fh)["vocab"]
        _cmu = {}
        with open(os.path.join(ASSETS, "cmudict.dict"), encoding="latin-1") as fh:
            for line in fh:
                parts = line.split("#")[0].split()
                if not parts:
                    continue
                word = parts[0]
                if "(" in word:          # keep the first pronunciation only
                    continue
                _cmu[word] = parts[1:]


def _vowel(base, stress, final):
    if base == "AH":
        return "ʌ" if stress in "12" else "ə"
    if base == "ER":
        return "ɜː" if stress in "12" else "ə"
    if base == "IY":
        return "iː" if stress in "12" else "i"
    if base == "UW":
        return "uː" if stress in "12" else "u"
    return {"AA": "ɒ", "AE": "æ", "AO": "ɔː", "AW": "W", "AY": "I", "EH": "ɛ",
            "EY": "A", "IH": "ɪ", "OW": "Q", "OY": "Y", "UH": "ʊ"}[base]


def _arpabet_to_gb(phones):
    out, i = [], 0
    while i < len(phones):
        p = phones[i]
        base, stress = re.match(r"([A-Z]+)(\d?)", p).groups()
        nxt = phones[i + 1] if i + 1 < len(phones) else None
        after = phones[i + 2] if i + 2 < len(phones) else None
        mark = {"1": "ˈ", "2": "ˌ"}.get(stress, "")
        if base in VOWELS:
            r_next = nxt is not None and re.match(r"R$", nxt)
            r_then_vowel = after is not None and re.match(r"([A-Z]+)", after).group(1) in VOWELS
            if base == "ER":
                out.append(mark + ("ɜː" if stress in "12" else "ə"))
                if nxt and re.match(r"([A-Z]+)", nxt).group(1) in VOWELS:
                    out.append("ɹ")
            elif r_next and not r_then_vowel and base in VOWEL_R:
                out.append(mark + VOWEL_R[base])
                i += 1                    # the R is absorbed
            else:
                out.append(mark + _vowel(base, stress, nxt is None))
        elif base == "R":
            if nxt and re.match(r"([A-Z]+)", nxt).group(1) in VOWELS:
                out.append("ɹ")
        else:
            out.append(CONS[base])
        i += 1
    return "".join(out)


def _espeak(word):
    exe = shutil.which("espeak-ng")
    if not exe:
        return None
    ipa = subprocess.run([exe, "-q", "--ipa", "-v", "en-gb", word],
                         capture_output=True, text=True).stdout
    ipa = "".join(ipa.split())
    return ipa or None


def word_phonemes(word):
    _load()
    w = word.lower().replace("’", "'")
    if w in FIXED:
        return FIXED[w]
    key = w
    if key.endswith("'s") and key[:-2] in FIXED:
        base = FIXED[key[:-2]]
        return base + ("s" if base[-1] in "ptkfθ" else "ɪz" if base[-1] in "szʃʒʧʤ" else "z")
    if key in _cmu:
        return _arpabet_to_gb(_cmu[key])
    if key.endswith("'s") and key[:-2] in _cmu:
        base = word_phonemes(key[:-2])
        return base + ("s" if base[-1] in "ptkfθ" else "ɪz" if base[-1] in "szʃʒʧʤ" else "z")
    if key.endswith("s'") and key[:-1] in _cmu:
        return _arpabet_to_gb(_cmu[key[:-1]])
    ipa = _espeak(word)
    if ipa:
        return ipa
    unknown_words.append(word)
    letters = [_arpabet_to_gb(_cmu[c]) for c in key if c in _cmu]
    return "".join(letters)


NUM_WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen " \
            "fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(n):
    n = int(n)
    if n < 20:
        return NUM_WORDS[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + NUM_WORDS[n % 10])
    if n < 1000:
        rest = n % 100
        return NUM_WORDS[n // 100] + " hundred" + ("" if rest == 0 else " and " + number_words(rest))
    if 2000 <= n < 2100:          # years: twenty thirty-four
        return "twenty " + (number_words(n % 100) if n % 100 >= 10 else "oh " + NUM_WORDS[n % 100])
    return " ".join(NUM_WORDS[int(c)] for c in str(n))


def spoken(text):
    for pat, rep in SAY:
        text = re.sub(pat, rep, text)
    text = re.sub(r"\d+", lambda m: number_words(m.group(0)), text)
    return text


def phonemize(text):
    _load()
    out = []
    for token in re.findall(r"[A-Za-zÀ-ÿ'’]+|[,.!?;:—]", spoken(text)):
        if re.match(r"[,.!?;:—]", token):
            if out:
                out[-1] += token
            continue
        out.append(word_phonemes(token))
    ph = " ".join(out)
    return "".join(c for c in ph if c in _vocab).strip()


def synth(text, voice=VOICE, speed=1.0):
    global _sess, _voices
    import onnxruntime as ort
    if _sess is None:
        _sess = ort.InferenceSession(os.path.join(ASSETS, "kokoro.onnx"),
                                     providers=["CPUExecutionProvider"])
        _voices = np.load(os.path.join(ASSETS, "voices.bin"))
    ph = phonemize(text)
    tokens = [_vocab[c] for c in ph][:510]
    style = _voices[voice][min(len(tokens), len(_voices[voice])) - 1]
    names = {i.name: i for i in _sess.get_inputs()}
    tok_name = "input_ids" if "input_ids" in names else "tokens"
    speed_dtype = np.int32 if "int" in names["speed"].type else np.float32
    audio = _sess.run(None, {
        tok_name: np.array([[0, *tokens, 0]], dtype=np.int64),
        "style": np.asarray(style, dtype=np.float32),
        "speed": np.array([speed], dtype=speed_dtype),
    })[0]
    audio = np.asarray(audio, dtype=np.float32).ravel()
    nz = np.where(np.abs(audio) > 0.01)[0]
    if len(nz):
        audio = audio[max(0, nz[0] - 600): nz[-1] + 1800]
    return audio


if __name__ == "__main__":
    import sys
    for line in sys.argv[1:]:
        print(spoken(line))
        print(phonemize(line))
    if unknown_words:
        print("Spelled out (add to FIXED):", ", ".join(sorted(set(unknown_words))))
