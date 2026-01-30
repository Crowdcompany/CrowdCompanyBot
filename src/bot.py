"""
Crowdbot - Telegram Bot

Ein selbst gehosteter KI-Assistent mit Markdown-Gedächtnis.
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from src.memory_manager_v2 import MemoryManagerV2
from src.llm_client import LLMClient
from src.search_module import SearchModule
from src.web_import import WebImporter
from dotenv import load_dotenv
import os

# Lade Umgebungsvariablen
load_dotenv()

# Logging konfigurieren
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def is_authorized(user_id: int) -> bool:
    """
    Prüft ob ein Benutzer autorisiert ist.

    Args:
        user_id: Telegram User-ID

    Returns:
        True wenn autorisiert
    """
    allowed_ids_str = os.getenv("ALLOWED_USER_IDS", "")
    if not allowed_ids_str:
        logger.error("ALLOWED_USER_IDS nicht gesetzt! Alle User werden abgelehnt.")
        return False

    try:
        allowed_ids = [int(id.strip()) for id in allowed_ids_str.split(",") if id.strip()]
        return user_id in allowed_ids
    except ValueError as e:
        logger.error(f"Fehler beim Parsen von ALLOWED_USER_IDS: {e}")
        return False


class Crowdbot:
    """Hauptklasse für den Crowdbot."""

    def __init__(
        self,
        token: Optional[str] = None,
        data_dir: Optional[str] = None
    ):
        """
        Initialisiert den Crowdbot.

        Args:
            token: Telegram Bot Token (aus .env wenn None)
            data_dir: Verzeichnis für Benutzerdaten (aus .env wenn None)
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        data_dir = data_dir or os.getenv("DATA_DIR", "./data")

        if not self.token:
            raise ValueError(
                "Kein Telegram Bot Token gefunden. "
                "Bitte setze TELEGRAM_BOT_TOKEN in der .env Datei."
            )

        # Komponenten initialisieren
        self.memory_manager = MemoryManagerV2(data_dir=data_dir)
        self.llm_client = LLMClient()
        self.search_module = SearchModule()
        self.web_importer = WebImporter(data_dir=data_dir)

        # Tool registrieren: web_search
        self.llm_client.register_tool(
            name="web_search",
            func=self._tool_web_search,
            description="Suche im Internet nach aktuellen Informationen, Nachrichten, Fakten oder technischen Details. Nutze dieses Tool wenn der Benutzer nach etwas fragt das eine Recherche erfordert."
        )

        # Application erstellen
        self.application = Application.builder().token(self.token).build()

        # Handler registrieren
        self._register_handlers()

    async def check_authorization(self, update: Update) -> bool:
        """
        Prüft Autorisierung und sendet Fehlermeldung wenn nötig.

        Args:
            update: Telegram Update

        Returns:
            True wenn autorisiert
        """
        user_id = update.effective_user.id

        if not is_authorized(user_id):
            username = update.effective_user.username or update.effective_user.first_name
            await update.message.reply_text(
                "Entschuldigung, du bist nicht autorisiert, diesen Bot zu nutzen. "
                "Bitte kontaktiere den Bot-Administrator."
            )
            logger.warning(
                f"Nicht autorisierter Zugriffsversuch von User-ID: {user_id} "
                f"(Username: {username})"
            )
            return False

        return True

    def _tool_web_search(self, query: str) -> str:
        """
        Tool-Funktion für die Websuche.

        Wird vom LLM aufgerufen, wenn eine Suche benötigt wird.
        Nutzt intelligente Erkennung (Perplexity für Fakten, Deep Research für Analysen).

        Args:
            query: Die Suchanfrage

        Returns:
            Die Suchergebnisse als TTS-kompatibler Text
        """
        logger.info(f"Web-Suche Tool aufgerufen mit: {query}")
        result = self.search_module.search(query, force_deep_search=False, format="tts")

        if result:
            # Ergebnis stark begrenzen um Telegram-Limit zu vermeiden
            if len(result) > 1500:
                result = result[:1500] + "... (Suchergebnisse gekürzt)"
            return result
        else:
            return "Die Suche hat keine Ergebnisse geliefert."

    def _load_important_files(self, user_id: int) -> str:
        """
        Lädt alle important/*.md Dateien für den Kontext.

        Args:
            user_id: Telegram Benutzer-ID

        Returns:
            Kombinierter Inhalt aller important-Dateien als String
        """
        from pathlib import Path

        important_dir = Path(self.memory_manager.data_dir) / "users" / str(user_id) / "important"

        if not important_dir.exists():
            return ""

        important_content = []
        important_content.append("# Wichtige Informationen (dauerhaft gespeichert)")
        important_content.append("")

        # Alle .md Dateien in important/ laden
        for md_file in sorted(important_dir.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                important_content.append(f"## Aus Datei: {md_file.name}")
                important_content.append(content)
                important_content.append("")
                logger.debug(f"Important-Datei geladen: {md_file.name} ({len(content)} Zeichen)")
            except Exception as e:
                logger.error(f"Fehler beim Laden von {md_file.name}: {e}")
                continue

        if len(important_content) > 2:  # Mehr als nur Header
            return "\n".join(important_content)
        else:
            return ""

    def _remove_markdown(self, text: str) -> str:
        """
        Entfernt alle Markdown-Formatierungen aus dem Text für TTS-Kompatibilität.

        Args:
            text: Text mit potentiellen Markdown-Formatierungen

        Returns:
            Text ohne Markdown-Formatierungen
        """
        import re

        if not text:
            return text

        # Fett-Formatierungen entfernen: **text** und __text__
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)

        # Kursiv-Formatierungen entfernen: *text* und _text_
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # Code-Formatierungen entfernen: `code` und ```code```
        text = re.sub(r'```[^\n]*\n.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # Links entfernen: [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Überschriften entfernen: ### Text -> Text
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

        # Listen-Marker entfernen aber Struktur beibehalten
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

        # Blockquotes entfernen: > text
        text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)

        # Horizontale Linien entfernen: --- oder ***
        text = re.sub(r'^[\-\*]{3,}\s*$', '', text, flags=re.MULTILINE)

        # Mehrfache Leerzeichen reduzieren
        text = re.sub(r'\s+', ' ', text)

        # Mehrfache Zeilenumbrüche reduzieren
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        return text.strip()

    def _register_handlers(self):
        """Registriert alle Command- und Message-Handler."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("searchmd", self.search_md_command))
        self.application.add_handler(CommandHandler("deepresearch", self.deep_research_command))
        self.application.add_handler(CommandHandler("import", self.import_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /start Befehl.

        Erstellt einen neuen Benutzer mit Gedächtnis-Datei.
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

        # Prüfen, ob Benutzer bereits existiert
        if self.memory_manager.user_exists(user_id):
            message = (
                f"Hallo {username}! 👋\n\n"
                "Willkommen zurück bei Crowdbot. "
                "Ich habe mich an unsere bisherigen Unterhaltungen erinnert."
            )
        else:
            # Neuen Benutzer erstellen
            self.memory_manager.create_user(user_id, username)
            message = (
                f"Hallo {username}! 👋\n\n"
                "Willkommen bei Crowdbot! Ich bin dein persönlicher KI-Assistent. "
                "Ich werde unsere Unterhaltungen merken, damit ich dich besser kennen lernen kann.\n\n"
                "Schreib mir einfach eine Nachricht, um anzufangen!"
            )

        await update.message.reply_text(message)

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /reset Befehl.

        Setzt das Gedächtnis eines Benutzers zurück.
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

        # Gedächtnis zurücksetzen
        self.memory_manager.reset_user(user_id, username)

        message = (
            f"Alles klar, {username}! 🧹\n\n"
            "Ich habe mein Gedächtnis über dich zurückgesetzt. "
            "Lasst uns neu beginnen!"
        )

        await update.message.reply_text(message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /help Befehl.

        Zeigt Hilfe-Informationen an.
        """
        if not await self.check_authorization(update):
            return

        message = (
            "Crowdbot Hilfe\n\n"
            "Befehle:\n"
            "/start - Starte den Bot oder begrüße dich\n"
            "/reset - Setze mein Gedächtnis zurück\n"
            "/search <Anfrage> - Schnelle Fakten-Suche (Perplexity)\n"
            "/deepresearch <Anfrage> - Ausführliche Analyse (Jina Deep Research)\n"
            "/searchmd <Anfrage> - Suche mit Markdown-Datei\n"
            "/import <URL> [dateiname] - Importiere Webseite dauerhaft ins Memory\n"
            "/help - Zeigt diese Hilfe an\n\n"
            "Über Crowdbot:\n"
            "Ich bin ein selbst gehosteter KI-Assistent. "
            "Unsere Unterhaltungen werden lokal gespeichert und ich merke mich an frühere Gespräche.\n\n"
            "Automatische Suche:\n"
            "Ich kann automatisch im Internet suchen, wenn du nach aktuellen Informationen fragst. "
            "Ich nutze Perplexity für schnelle Fakten wie TV-Programm, Nachrichten oder allgemeine Fragen.\n"
            "Für tiefgehende Analysen nutze /deepresearch.\n\n"
            "Web-Import:\n"
            "Mit /import kannst du Webseiten dauerhaft in dein Memory importieren. "
            "Der Inhalt wird bereinigt und in important/ gespeichert, wo er nie gelöscht wird. "
            "Perfekt für Dokumentationen, Artikel oder wichtige Informationen.\n\n"
            "Schreib mir einfach eine Nachricht, um ins Gespräch zu kommen!"
        )

        await update.message.reply_text(message)

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /search Befehl.

        Sucht im Internet mit intelligenter Erkennung (Perplexity für Fakten)
        und liefert TTS-kompatible Ergebnisse in ganzen Sätzen.
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id

        # Prüfen, ob Suchanfrage vorhanden
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Bitte gib eine Suchanfrage an!\n"
                "Beispiel: /search Was ist Python?\n\n"
                "Für ausführliche Analysen nutze /deepresearch\n"
                "Für Markdown-Datei nutze /searchmd"
            )
            return

        query = " ".join(context.args)

        # Prüfen, ob Benutzer existiert
        if not self.memory_manager.user_exists(user_id):
            await update.message.reply_text(
                "Bitte starte den Bot erst mit /start!"
            )
            return

        # Typing-Indikator anzeigen
        await update.message.chat.send_action("typing")

        # Suchanfrage ausführen mit TTS-Formatierung
        await update.message.reply_text(
            f"🔍 Suche nach: {query}..."
        )

        result = self.search_module.search(query, force_deep_search=False, format="tts")

        if result:
            # Ergebnis kürzen, falls zu lang für Telegram
            if len(result) > 4000:
                result = result[:4000] + "\n\n... (gekürzt. Nutze /searchmd für die vollständige Version)"

            # Ergebnis speichern
            self.memory_manager.append_message(user_id, "user", f"/search {query}")
            self.memory_manager.append_message(user_id, "assistant", result)

            await update.message.reply_text(result)
        else:
            await update.message.reply_text(
                "Es tut mir leid, die Suche hat keine Ergebnisse geliefert. "
                "Versuche es mit einer anderen Anfrage."
            )
            logger.error(f"Suche lieferte keine Ergebnisse für: {query}")

    async def search_md_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /searchmd Befehl.

        Sucht im Internet und sendet das vollständige Markdown als Datei.
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id

        # Prüfen, ob Suchanfrage vorhanden
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Bitte gib eine Suchanfrage an!\n"
                "Beispiel: /searchmd Was ist Python?"
            )
            return

        query = " ".join(context.args)

        # Prüfen, ob Benutzer existiert
        if not self.memory_manager.user_exists(user_id):
            await update.message.reply_text(
                "Bitte starte den Bot erst mit /start!"
            )
            return

        # Typing-Indikator anzeigen
        await update.message.chat.send_action("typing")

        # Suchanfrage ausführen mit Markdown-Format
        await update.message.reply_text(
            f"🔍 Suche nach: {query}\n\n"
            "Dies kann 30-60 Sekunden dauern. "
            "Das Ergebnis wird als Datei gesendet..."
        )

        result = self.search_module.search(query, force_deep_search=False, format="markdown")

        if result:
            import tempfile
            import os

            # Temporäre Datei erstellen
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.md',
                delete=False,
                encoding='utf-8'
            ) as f:
                # Dateiname aus Query erstellen (sicher machen)
                safe_query = ''.join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_query = safe_query[:50]  # Limitieren
                filename = f"search_{safe_query}.md"

                f.write(f"# Suchergebnisse für: {query}\n\n")
                f.write(result)

                temp_path = f.name

            try:
                # Datei senden
                with open(temp_path, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"📄 Vollständige Suchergebnisse für: {query}"
                    )

                # Auch eine kurze Zusammenfassung senden
                summary = self.search_module._make_tts_compatible(result)
                if len(summary) > 500:
                    summary = summary[:500] + "..."

                await update.message.reply_text(
                    f"📝 Kurze Zusammenfassung:\n\n{summary}"
                )

                # Ergebnis speichern
                self.memory_manager.append_message(user_id, "user", f"/searchmd {query}")
                self.memory_manager.append_message(user_id, "assistant", f"[Markdown-Datei gesendet: {filename}]")

            finally:
                # Temporäre Datei löschen
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        else:
            await update.message.reply_text(
                "Es tut mir leid, die Suche hat keine Ergebnisse geliefert. "
                "Versuche es mit einer anderen Anfrage."
            )
            logger.error(f"Suche lieferte keine Ergebnisse für: {query}")

    async def deep_research_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /deepresearch Befehl.

        Führt eine ausführliche Deep Research mit Jina durch,
        ideal für komplexe Analysen und Wikipedia-ähnliche Recherchen.
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id

        # Prüfen, ob Suchanfrage vorhanden
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Bitte gib eine Suchanfrage an!\n"
                "Beispiel: /deepresearch Erkläre ausführlich wie Quantencomputer funktionieren\n\n"
                "Deep Research ist ideal für:\n"
                "- Ausführliche Analysen\n"
                "- Komplexe technische Themen\n"
                "- Wikipedia-ähnliche Recherchen\n\n"
                "Für schnelle Fakten nutze normale Nachrichten oder /search"
            )
            return

        query = " ".join(context.args)

        # Prüfen, ob Benutzer existiert
        if not self.memory_manager.user_exists(user_id):
            await update.message.reply_text(
                "Bitte starte den Bot erst mit /start!"
            )
            return

        # Typing-Indikator anzeigen
        await update.message.chat.send_action("typing")

        # Suchanfrage mit Deep Research erzwingen
        await update.message.reply_text(
            f"🔬 Starte ausführliche Deep Research für: {query}\n\n"
            "Dies kann 60-120 Sekunden dauern..."
        )

        result = self.search_module.search(query, force_deep_search=True, format="tts")

        if result:
            # Ergebnis kürzen, falls zu lang für Telegram
            if len(result) > 4000:
                result = result[:4000] + "\n\n... (gekürzt wegen Länge)"

            # Ergebnis speichern
            self.memory_manager.append_message(user_id, "user", f"/deepresearch {query}")
            self.memory_manager.append_message(user_id, "assistant", result)

            await update.message.reply_text(result)
        else:
            await update.message.reply_text(
                "Es tut mir leid, die Deep Research hat keine Ergebnisse geliefert. "
                "Versuche es mit einer anderen Anfrage."
            )
            logger.error(f"Deep Research lieferte keine Ergebnisse für: {query}")

    async def import_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /import Befehl.

        Importiert eine Webseite und speichert sie dauerhaft im Memory.
        Format: /import <URL> [optionaler_dateiname]
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id

        # Prüfe ob Argumente angegeben wurden
        if not context.args:
            await update.message.reply_text(
                "Bitte gib eine URL an!\n\n"
                "Verwendung: /import <URL> [dateiname]\n\n"
                "Beispiel: /import https://example.com/artikel wichtiger_artikel\n\n"
                "Die Webseite wird geladen, bereinigt und dauerhaft in deinem Memory gespeichert."
            )
            return

        url = context.args[0]
        custom_filename = " ".join(context.args[1:]) if len(context.args) > 1 else None

        # Prüfen, ob Benutzer existiert
        if not self.memory_manager.user_exists(user_id):
            await update.message.reply_text(
                "Bitte starte den Bot erst mit /start!"
            )
            return

        # Typing-Indikator anzeigen
        await update.message.chat.send_action("typing")

        # Info-Nachricht
        await update.message.reply_text(
            f"🌐 Importiere Webseite: {url}\n\n"
            "Dies kann einen Moment dauern..."
        )

        # Import durchführen
        success, message = self.web_importer.import_url(user_id, url, custom_filename)

        if success:
            # Erfolg - speichere auch in Memory für Kontext
            self.memory_manager.append_message(
                user_id,
                "user",
                f"/import {url}" + (f" {custom_filename}" if custom_filename else "")
            )
            self.memory_manager.append_message(user_id, "assistant", message)

            # TTS-kompatible Nachricht
            tts_message = self._remove_markdown(message)
            await update.message.reply_text(tts_message)

            logger.info(f"Web-Import erfolgreich: {url} für User {user_id}")
        else:
            # Fehler
            error_message = f"Fehler beim Importieren der Webseite:\n\n{message}"
            await update.message.reply_text(error_message)
            logger.error(f"Web-Import fehlgeschlagen: {url} - {message}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für Textnachrichten.

        Sendet die Nachricht an das LLM mit Tool-Unterstützung und speichert die Antwort.
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id
        user_message = update.message.text

        # Prüfen, ob Benutzer existiert
        if not self.memory_manager.user_exists(user_id):
            await update.message.reply_text(
                "Bitte starte den Bot erst mit /start!"
            )
            return

        # Typing-Indikator anzeigen
        await update.message.chat.send_action("typing")

        # Benutzer-Nachricht speichern
        self.memory_manager.append_message(user_id, "user", user_message)

        # Konversations-Kontext laden
        conversation_history = self.memory_manager.get_context(user_id, max_messages=10)

        # Important-Dateien laden (importierte Webseiten, Präferenzen)
        important_context = self._load_important_files(user_id)

        # Erweitere user_message mit wichtigem Kontext
        enhanced_user_message = user_message
        if important_context:
            enhanced_user_message = f"[Wichtiger Kontext aus deinem Gedächtnis:]\n{important_context}\n\n[Benutzer-Anfrage:]\n{user_message}"

        # Anfrage an das LLM senden mit Intention-basierter Tool-Nutzung
        response = self.llm_client.chat_with_intention(
            user_message=enhanced_user_message,
            conversation_history=conversation_history,
            max_tokens=2000
        )

        if response:
            # Markdown entfernen für TTS-Kompatibilität
            response = self._remove_markdown(response)

            # Antwort für Telegram kürzen (Limit: 4096 Zeichen)
            TELEGRAM_LIMIT = 4000

            if len(response) > TELEGRAM_LIMIT:
                response = response[:TELEGRAM_LIMIT] + "\n\n...(Antwort wegen Länge gekürzt)"

            # Antwort speichern
            self.memory_manager.append_message(user_id, "assistant", response)

            # Antwort senden
            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "Es tut mir leid, ich habe Probleme bei der Verbindung zu meinem Gehirn. "
                "Bitte versuche es später noch einmal."
            )
            logger.error(f"LLM-Antwort war None für User {user_id}")

    async def post_init(self, application):
        """
        Wird nach dem Start ausgeführt.
        Registriert Bot-Commands bei Telegram.
        """
        from telegram import BotCommand

        commands = [
            BotCommand("start", "Bot starten oder begrüßen"),
            BotCommand("reset", "Gedächtnis zurücksetzen"),
            BotCommand("help", "Hilfe anzeigen"),
            BotCommand("search", "Schnelle Faktensuche"),
            BotCommand("searchmd", "Suche mit Markdown-Datei"),
            BotCommand("deepresearch", "Ausführliche Analyse"),
            BotCommand("import", "Webseite ins Memory importieren"),
        ]

        await application.bot.set_my_commands(commands)
        logger.info("Bot-Commands bei Telegram registriert")

    def run(self):
        """Startet den Bot."""
        logger.info("Crowdbot wird gestartet...")

        # Post-Init Hook registrieren
        self.application.post_init = self.post_init

        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Haupteinstiegspunkt."""
    try:
        bot = Crowdbot()
        bot.run()
    except ValueError as e:
        logger.error(f"Konfigurationsfehler: {e}")
    except KeyboardInterrupt:
        logger.info("Bot wird gestoppt...")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")


if __name__ == "__main__":
    main()
