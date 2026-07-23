# 🌍 Universal AI Event Finder for Home Assistant

![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)

Ein KI-gestütztes Home-Assistant-Plugin, das automatisch **öffentliche Events in deiner Nähe** findet und live auf deiner Home-Assistant-Karte anzeigt.

---

## ⚡ Schnell-Überblick

* 🍷 **Findet Events:** Konzerte, Festivals, Märkte, Stadtfeste, Kulturveranstaltungen & mehr.
* 📍 **Weltweit & Exakt:** Funktioniert in jedem Land mit genauer GPS-Verortung.
* 💸 **100% Kostenlos:** Unterstützt kostenlose KI-APIs (Groq, Google Gemini).
* 🗺️ **Karten-Integration:** Zeigt Events als Stecknadeln inklusive Details (Uhrzeit, Preis, Beschreibung).
* ⚙️ **Voll Anpassbar:** Ort, Suchradius (km) und Kriterien lassen sich direkt in den Einstellungen ändern.

---

## 🚀 Installation

### Option 1: Direkt zu HACS hinzufügen (Empfohlen)

Klicke auf diesen Button, um das Repository direkt in deinen Home Assistant / HACS einzubinden:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)]([https://my.home-assistant.io/redirect/hacs_repository/?owner=Dealwirth&repository=universal_ai_events&category=integration](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dealwirth&repository=universal_ai_events&category=integration))

---

### Option 2: Manuell über HACS

1. Öffne **HACS** in Home Assistant.
2. Klicke oben rechts auf die **3 Punkte** ➔ **Benutzerdefinierte Repositories**.
3. Füge folgende Repository-URL ein:
   `[https://github.com/Dealwirth/universal_ai_events](https://github.com/Dealwirth/universal_ai_events)`
4. Wähle als Kategorie **Integration** aus und klicke auf **Hinzufügen**.
5. Klicke auf **Herunterladen** und starte Home Assistant neu.

---

## ⚙️ Einrichten

1. Gehe in Home Assistant zu **Einstellungen** ➔ **Geräte & Dienste** ➔ **Integration hinzufügen**.
2. Suche nach **Universal AI Event Finder**.
3. Gib folgende Daten ein:
   * **KI-Anbieter:** `Groq` (Kostenlos) oder `Gemini`
   * **API Key:** Dein kostenloser Key
   * **Ort & Land:** z. B. `Berlin`, `Germany`
   * **Radius:** z. B. `30` (km)
   * **Kriterien:** `Festival, Concert, Market, Open Air, Rock`

---

## 🗺️ Auf dem Dashboard anzeigen

Füge diese Karte zu deinem Dashboard hinzu:

```yaml
type: map
title: 🎪 Events in der Nähe
default_zoom: 11
geo_location_sources:
  - universal_ai_events
