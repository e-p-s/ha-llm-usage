# LLM Usage für Home Assistant

Zwei eigene Home-Assistant-Integrationen, die API-Kontingente von **MiniMax** (Token-Plan) und **OpenRouter** (Credits) als Sensoren abbilden — inklusive Verbrauchs-Deltas über rollierende Zeitfenster (1 h / 2 h / 24 h).

| | MiniMax Usage | OpenRouter Usage |
|---|---|---|
| Datenquelle | `https://www.minimax.io/v1/token_plan/remains` | `https://openrouter.ai/api/v1/credits` + `/api/v1/auth/key` |
| Poll-Intervall | 60 s | 5 min |
| Benötigter Key | MiniMax-Subscription-Key (platform.minimax.io) | OpenRouter-API-Key (openrouter.ai → Keys) |

## Sensoren

### MiniMax Usage (Gerät „MiniMax Token Plan — Allgemein“ / „— Video“)
| Sensor | Typ | Beschreibung |
|---|---|---|
| 5h-Nutzung | % | Verbrauch im laufenden 5-Stunden-Fenster |
| 5h-Reset | Zeit | Ende des 5h-Fensters |
| Wochen-Nutzung | % | Verbrauch in der laufenden Woche |
| Wochen-Reset | Zeit | Ende des Wochenfensters |
| Δ 5h-Nutzung letzte Stunde / letzte 2 Std. | Prozentpunkte | Verbrauch im rollierenden Fenster |
| Δ Wochen-Nutzung letzte Stunde | Prozentpunkte | Verbrauch im rollierenden Fenster |

Zusätzlich ein separates Gerät „— Video“ mit Wochen-Sensoren für die Modellgruppe `video`.
Hinweis: Die Video-Gruppe liefert von der API nur ein 24h-Tagesfenster statt eines echten 5h-Fensters; die Integration blendet den irreführenden „5h“-Wert der Video-Gruppe aus.

### OpenRouter Usage
| Sensor | Typ | Beschreibung |
|---|---|---|
| Guthaben | USD | `total_credits − total_usage` |
| Verbrauch gesamt | USD | kumulierter Verbrauch seit Account-Eröffnung |
| Key-Verbrauch (Monat) | USD | monatlicher Verbrauch des Keys |
| Verbrauch letzte Stunde / 2 Std. / 24 Std. | USD | Delta über rollierende Fenster |

## Funktionsweise der Delta-Sensoren

Jeder Poll wird als Sample in einer 48-Stunden-History persistiert (`.storage/minimax_usage.samples` bzw. `.storage/openrouter_usage.samples`, private Dateien). Deltas werden aus den Differenzen der Samples berechnet:

- **OpenRouter** (kumulierter Zähler): einfache Positive-Delta-Summe.
- **MiniMax** (Fenster-Prozentwerte): Wenn das Zeitfenster zwischen zwei Samples wechselt (Reset), zählt nur der neue Wert — ein Reset erzeugt damit keine Schein-Verbräuche.

Die History startet nach der Installation bei null; nach 1–2 Stunden sind alle Fenster gefüllt. Auflösung = Poll-Intervall.

## Installation

### Variante A — Manuell
1. Verzeichnis `custom_components/` aus diesem Repo komplett nach `/config/custom_components/` kopieren (die beiden Unterordner `minimax_usage` und `openrouter_usage`).
2. Home Assistant neu starten (Settings → System → Neu starten → **Home Assistant neu starten**).
3. Settings → Geräte & Dienste → Integration hinzufügen → nach **„MiniMax Usage“** bzw. **„OpenRouter Usage“** suchen.
4. API-Key eintragen, fertig. Der Key ist danach jederzeit über das Zahnrad der Integration („Konfigurieren“) änderbar.

### Variante B — HACS (Custom Repository)

MiniMax: [![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=e-p-s&repository=ha-minimax-usage&category=integration)
OpenRouter: [![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=e-p-s&repository=ha-openrouter-usage&category=integration)

Nach der Installation — Integration direkt hinzufügen:
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=minimax_usage)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=openrouter_usage)

Voraussetzung: HACS ist installiert.

> **Wichtig:** HACS erwartet pro Repository genau **eine** Integration. Für HACS die jeweiligen Einzel-Repos verwenden (`ha-minimax-usage` bzw. `ha-openrouter-usage`), nicht das All-in-One-Repo.

1. HACS → Integrationen → ⋮ (oben rechts) → **Custom repositories**.
2. Repo-URL eintragen, Kategorie **Integration**, hinzufügen.
3. Integration in HACS installieren → HA-Neustart → danach wie oben hinzufügen.

## Datenschutz

- API-Keys liegen ausschließlich in der lokalen Config-Entry-Datei (`.storage`, private).
- Es gibt keine Aufrufe an Dritte: nur `minimax.io` bzw. `openrouter.ai`.
- Die Sample-History enthält nur Prozentwerte/USD-Beträge, keine Prompt-Inhalte.

## Voraussetzungen

- Home Assistant ≥ 2024.12 (getestet auf 2026.10)
- MiniMax: aktiver Token-/Subscription-Plan (ohne Plan liefert die API keine Gruppen)
- OpenRouter: gültiger API-Key (Read-only reicht)

## Troubleshooting

| Problem | Ursache / Lösung |
|---|---|
| Integration erscheint nicht in der Suchliste | Kein vollständiger Neustart durchgeführt (Reload reicht nach der Ersten Installation nicht) |
| Entry-Status „FEHLER“ / `setup_error` | Core-Neustart; Details: Einstellungen → System → Protokolle |
| Deltas zeigen 0 | History muss erst anwachsen (1 Poll-Zyklusminimum, sinnvoll ab ~1 h) |
| MiniMax „Video 5h“ fehlt | Absichtliches Verhalten — API liefert dort kein echtes 5h-Fenster |

## Für Entwickler: Veröffentlichung über HACS

Der offizielle Weg („default repository“, damit die Integration in der HACS-Suche auftaucht):

1. Repo **öffentlich** auf GitHub, eine Integration pro Repo.
2. `manifest.json` vollständig: `domain`, `name`, `version`, `documentation`, `issue_tracker`, `codeowners` (GitHub-Handle, nicht leer).
3. `hacs.json` im Repo-Root (liegt bei).
4. GitHub Actions: **HACS Action** + **Hassfest** (Workflows liegen bei) — müssen fehlerfrei laufen.
5. **GitHub Release** (vollständiger Release, nicht nur Tag) veröffentlichen.
6. `brand/icon.png` (512×512) ins Repo (für die offizielle Aufnahme Pflicht).
7. README mit Screenshots/Bildern (Pflicht für HACS-Rendering).
8. PR gegen [hacs/default](https://github.com/hacs/default) → Datei `./integration`, alphabetisch eintragen, Repo muss Beschreibung, Topics und Issues aktiviert haben.

Details: <https://www.hacs.xyz/docs/publish/include/>

## Lizenz

MIT — siehe [LICENSE](LICENSE).
