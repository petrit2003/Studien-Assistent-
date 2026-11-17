import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import streamlit as st

MODEL = "mistral-small-latest"
API_URL = "https://api.mistral.ai/v1/chat/completions"
BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "wissensbasis"
DEADLINES_FILE = BASE_DIR / "deadlines.json"

st.set_page_config(page_title="Uni-Assistent", page_icon="🎓", layout="wide")


def load_knowledge_base():
    docs = []
    if not KB_DIR.exists():
        return docs
    for path in sorted(KB_DIR.glob("*.md")) + sorted(KB_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(split_chunks(text)):
            docs.append({"source": path.stem, "chunk": i, "text": chunk})
    return docs


def split_chunks(text, size=900):
    parts = re.split(r"\n\s*\n", text)
    chunks, current = [], ""
    for part in parts:
        if len(current) + len(part) < size:
            current = (current + "\n\n" + part).strip()
        else:
            if current:
                chunks.append(current.strip())
            current = part
    if current:
        chunks.append(current.strip())
    return chunks


def retrieve(query, docs, top_k=3):
    stopwords = {"der", "die", "das", "und", "ist", "ich", "ein", "eine", "im", "in",
                 "für", "zu", "zum", "zur", "wie", "was", "wer", "wann", "wo", "muss",
                 "kann", "soll", "mit", "von", "auf", "bei", "den", "dem", "des", "sich",
                 "nicht", "auch", "als", "an", "am", "ob", "oder", "aber", "noch", "nochmal"}
    words = [w for w in re.findall(r"[a-zäöüß]+", query.lower()) if w not in stopwords and len(w) > 2]
    if not words or not docs:
        return []
    scored = []
    for doc in docs:
        text = doc["text"].lower()
        score = sum(text.count(w) for w in words)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    return [doc for _, doc in scored[:top_k]]


def load_deadlines():
    if DEADLINES_FILE.exists():
        try:
            return json.loads(DEADLINES_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_deadlines(deadlines):
    DEADLINES_FILE.write_text(json.dumps(deadlines, ensure_ascii=False, indent=2), encoding="utf-8")


def call_mistral(messages, api_key):
    payload = {"model": MODEL, "messages": messages, "temperature": 0.3}
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


MODES = {
    "📚 Studienorganisation": {
        "intro": "Frag mich alles zu Studienplanung, Prüfungsordnung, Anmeldefristen oder Modulen.",
        "examples": [
            "Welche Module muss ich im 3. Semester belegen?",
            "Bis wann muss ich mich zur Prüfung in XY anmelden?",
            "Wie viele Prüfungsversuche habe ich pro Modul?",
            "Wie sieht ein sinnvoller Studienverlauf aus?",
        ],
        "prompt": (
            "Du bist ein persönlicher Studienassistent für organisatorische Fragen. "
            "Antworte auf Basis der bereitgestellten Studieninformationen (Modulhandbuch, Prüfungsordnung, "
            "Anerkennungsordnung). Zitiere bei jeder Antwort die Quelle, z. B. (Quelle: pruefungsordnung). "
            "Wenn die Information in den Dokumenten nicht enthalten ist, sage das ehrlich und empfehle, "
            "beim Prüfungsamt nachzufragen. Berücksichtige das Profil des Studierenden (Studiengang, Semester) "
            "und seine anstehenden Deadlines bei deinen Empfehlungen."
        ),
    },
    "🧠 Lernstrategien & Prüfungsvorbereitung": {
        "intro": "Ich helfe dir bei Lernmethoden, Zeitmanagement und der Vorbereitung auf Prüfungen.",
        "examples": [
            "Hilf mir, einen Lernplan für die Klausur in XY zu erstellen",
            "Welche Lernmethode passt zu Statistik?",
            "Ich prokrastiniere ständig, was kann ich tun?",
            "Wie bereite ich mich in 2 Wochen auf eine mündliche Prüfung vor?",
        ],
        "prompt": (
            "Du bist ein Lerncoach für Studierende. Gib konkrete, individuell angepasste Empfehlungen zu "
            "Lernmethoden, Zeitmanagement und Prüfungsvorbereitung. Frage nach, wenn dir wichtige Informationen "
            "fehlen (z. B. wie viel Zeit bleibt, Lerntyp, Umfang des Stoffs). Berücksichtige das Profil und die "
            "anstehenden Deadlines des Studierenden. Halte deine Ratschläge praktisch umsetzbar, z. B. in Form "
            "konkreter Wochenpläne oder Schritt-für-Schritt-Anleitungen."
        ),
    },
    "💡 Fachliche Lernunterstützung": {
        "intro": "Ich erkläre Studieninhalte, gebe Praxisbeispiele und erstelle Übungsaufgaben zum Ausprobieren.",
        "examples": [
            "Erkläre mir den Unterschied zwischen Array und Linked List",
            "Gib mir 3 Praxisbeispiele für Opportunitätskosten",
            "Erstelle eine Übungsaufgabe zu Normalverteilung",
            "Was ist der Unterschied zwischen correlation und causation?",
        ],
        "prompt": (
            "Du bist ein geduldiger Tutor deines Fachs. Erkläre komplexe Studieninhalte verständlich und "
            "stufenweise, nutze Alltagsbeispiele und Analogien. Wenn der Studierende eine Übungsaufgabe möchte, "
            "erstelle genau EINE Aufgabe mit klarem Schwierigkeitsgrad und löse sie NICHT selbst — warte auf "
            "seine Antwort und bewerte sie dann konstruktiv mit Lösungsweg. Passe den Schwierigkeitsgrad an das "
            "Semester im Profil an."
        ),
    },
}


def build_system_prompt(mode, docs):
    profile = st.session_state.profile
    deadlines = [d for d in st.session_state.deadlines if d["date"] >= date.today().isoformat()]
    deadline_text = "\n".join(f"- {d['date']}: {d['title']}" for d in sorted(deadlines, key=lambda x: x["date"])) or "- keine"
    parts = [MODES[mode]["prompt"]]
    parts.append(
        f"Profil des Studierenden: Studiengang {profile['studiengang'] or 'unbekannt'}, "
        f"Semester {profile['semester'] or 'unbekannt'}. Heute ist {date.today().isoformat()}. "
        f"Anstehende Deadlines:\n{deadline_text}"
    )
    if docs:
        kb_text = "\n\n".join(f"[Quelle: {d['source']}]\n{d['text']}" for d in docs)
        parts.append(f"Studieninformationen aus der Wissensbasis:\n{kb_text}")
    return "\n\n".join(parts)


def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = {mode: [] for mode in MODES}
    if "profile" not in st.session_state:
        st.session_state.profile = {"studiengang": "", "semester": ""}
    if "deadlines" not in st.session_state:
        st.session_state.deadlines = load_deadlines()


init_state()

with st.sidebar:
    st.title("🎓 Mein Studien-Assistent")
    st.caption("Dein persönlicher Begleiter durchs Studium")

    st.subheader("🔑 Mistral API-Key")
    api_key = st.text_input(
        "API-Key",
        value=os.environ.get("MISTRAL_API_KEY", ""),
        type="password",
        help="Kostenlos erstellbar auf console.mistral.ai",
    )
    if api_key:
        st.success("API verbunden ✅")
    else:
        st.warning("Demo-Modus: Ohne Key kommen nur Beispielantworten.")

    st.divider()
    st.subheader("👤 Mein Profil")
    st.session_state.profile["studiengang"] = st.text_input(
        "Studiengang", value=st.session_state.profile["studiengang"], placeholder="z. B. Wirtschaftsinformatik"
    )
    st.session_state.profile["semester"] = st.text_input(
        "Semester", value=st.session_state.profile["semester"], placeholder="z. B. 3"
    )

    st.divider()
    st.subheader("⏰ Meine Deadlines")
    with st.form("deadline_form", clear_on_submit=True):
        d_title = st.text_input("Was ist fällig?", placeholder="z. B. Prüfungsanmeldung Statistik")
        d_date = st.date_input("Wann?")
        if st.form_submit_button("Hinzufügen") and d_title:
            st.session_state.deadlines.append({"title": d_title, "date": d_date.isoformat()})
            save_deadlines(st.session_state.deadlines)
    for i, d in enumerate(sorted(st.session_state.deadlines, key=lambda x: x["date"])):
        days = (date.fromisoformat(d["date"]) - date.today()).days
        label = f"**{d['title']}** — {d['date']}"
        if days < 0:
            label += " · vergangen"
        elif days == 0:
            label += " · 🚨 heute!"
        elif days <= 14:
            label += f" · in {days} Tagen"
        col1, col2 = st.columns([4, 1])
        col1.markdown(label)
        if col2.button("🗑", key=f"del_{i}"):
            st.session_state.deadlines.remove(d)
            save_deadlines(st.session_state.deadlines)
            st.rerun()

    st.divider()
    st.subheader("📚 Wissensbasis")
    kb_files = (sorted(p.name for p in KB_DIR.glob("*.md")) + sorted(p.name for p in KB_DIR.glob("*.txt"))) if KB_DIR.exists() else []
    if kb_files:
        for f in kb_files:
            st.markdown(f"- {f}")
    else:
        st.caption("Noch keine Dokumente in wissensbasis/")

mode = st.sidebar.radio("Modus", list(MODES.keys()))

st.title(mode)
st.caption(MODES[mode]["intro"])

for msg in st.session_state.messages[mode]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.subheader("💬 Schnell starten")
cols = st.columns(2)
for i, example in enumerate(MODES[mode]["examples"]):
    if cols[i % 2].button(example, key=f"ex_{mode}_{i}", use_container_width=True):
        st.session_state.pending_prompt = example

user_input = st.chat_input("Stelle deine Frage …")
if "pending_prompt" in st.session_state:
    user_input = st.session_state.pop("pending_prompt")

if user_input:
    st.session_state.messages[mode].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Denke nach …"):
            docs = retrieve(user_input, load_knowledge_base()) if mode == "📚 Studienorganisation" else []
            history = st.session_state.messages[mode][-8:]
            messages = [{"role": "system", "content": build_system_prompt(mode, docs)}] + history
            if api_key:
                try:
                    answer = call_mistral(messages, api_key)
                except urllib.error.HTTPError as e:
                    answer = f"⚠️ API-Fehler {e.code}: Prüfe deinen API-Key. ({e.reason})"
                except urllib.error.URLError as e:
                    answer = f"⚠️ Keine Verbindung zur Mistral-API: {e.reason}"
            else:
                answer = (
                    "🤖 **Demo-Modus** — hier würde die Antwort des Assistenten stehen.\n\n"
                    f"Deine Frage war: *„{user_input}“*\n\n"
                    "Trage in der Seitenleiste einen kostenlosen Mistral-API-Key ein "
                    "(console.mistral.ai → API Keys), damit ich echt antworte."
                )
            st.markdown(answer)
    st.session_state.messages[mode].append({"role": "assistant", "content": answer})
    st.rerun()
