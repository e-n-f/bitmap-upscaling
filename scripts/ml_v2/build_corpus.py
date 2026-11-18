"""Build corpus/corpus.json (text used to pick realistic 1-3 character sequences) from NLTK's data packages.

  curl -LO https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/gutenberg.zip
  curl -LO https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/udhr.zip
  mkdir x && (cd x && unzip ../gutenberg.zip && unzip ../udhr.zip)
  python build_corpus.py x corpus.json

English: NLTK's Project Gutenberg selection (public domain). Other languages: the Universal Declaration of
Human Rights. gen2.py uses the first 2 MB of English.
"""
import glob, json, re, sys

src, out = sys.argv[1], sys.argv[2]
UDHR = {
    "fr": ("French_Francais-Latin1", "latin-1"), "de": ("German_Deutsch-Latin1", "latin-1"),
    "es": ("Spanish_Espanol-Latin1", "latin-1"), "it": ("Italian_Italiano-Latin1", "latin-1"),
    "pt": ("Portuguese_Portugues-Latin1", "latin-1"), "nl": ("Dutch_Nederlands-Latin1", "latin-1"),
    "sv": ("Swedish_Svenska-Latin1", "latin-1"), "da": ("Danish_Dansk-Latin1", "latin-1"),
    "no": ("Norwegian_Norsk-Bokmal-Latin1", "latin-1"), "fi": ("Finnish_Suomi-Latin1", "latin-1"),
    "is": ("Icelandic_Yslenska-Latin1", "latin-1"), "hu": ("Hungarian_Magyar-UTF8", "utf-8"),
    "pl": ("Polish_Polski-Latin2", "iso-8859-2"), "cs": ("Czech_Cesky-Latin2", "iso-8859-2"),
    "ro": ("Romanian_Romana-Latin2", "iso-8859-2"), "hr": ("Croatian_Hrvatski-Latin2", "cp1250"),
    "tr": ("Turkish_Turkce-UTF8", "utf-8"), "vi": ("Vietnamese-UTF8", "utf-8"),
    "ru": ("Russian_Russky-UTF8", "utf-8"), "uk": ("Ukrainian-UTF8", "utf-8"),
    "bg": ("Bulgarian_Balgarski-UTF8", "utf-8"), "sr": ("Serbian_Srpski-UTF8", "utf-8"),
    "el": ("Greek_Ellinika-UTF8", "utf-8"),
}
c = {"en": "".join(open(p, encoding="latin-1").read() for p in sorted(glob.glob(f"{src}/gutenberg/*.txt")))}
for lang, (f, enc) in UDHR.items():
    c[lang] = open(f"{src}/udhr/{f}", "rb").read().decode(enc, errors="replace")
c = {k: re.sub(r"\s+", " ", v).replace("�", "") for k, v in c.items()}
json.dump(c, open(out, "w"), ensure_ascii=False)
