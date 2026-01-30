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

from src.memory_manager import MemoryManager
from src.llm_client import LLMClient
from src.search_module import SearchModule
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
        data_dir: str = "/media/xray/NEU/Code/Crowdbot/data"
    ):
        """
        Initialisiert den Crowdbot.

        Args:
            token: Telegram Bot Token (aus .env wenn None)
            data_dir: Verzeichnis für Benutzerdaten
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")

        if not self.token:
            raise ValueError(
                "Kein Telegram Bot Token gefunden. "
                "Bitte setze TELEGRAM_BOT_TOKEN in der .env Datei."
            )

        # Komponenten initialisieren
        self.memory_manager = MemoryManager(data_dir=data_dir)
        self.llm_client = LLMClient()
        self.search_module = SearchModule()

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

        Args:
            query: Die Suchanfrage

        Returns:
            Die Suchergebnisse als TTS-kompatibler Text
        """
        logger.info(f"Web-Suche Tool aufgerufen mit: {query}")
        result = self.search_module.search(query, use_deep_search=True, format="tts")

        if result:
            # Ergebnis stark begrenzen um Telegram-Limit zu vermeiden
            if len(result) > 1500:
                result = result[:1500] + "... (Suchergebnisse gekürzt)"
            return result
        else:
            return "Die Suche hat keine Ergebnisse geliefert."

    def _register_handlers(self):
        """Registriert alle Command- und Message-Handler."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("searchmd", self.search_md_command))
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
            "/search <Anfrage> - Manuelle Suche im Internet mit TTS-kompatibler Ausgabe\n"
            "/searchmd <Anfrage> - Manuelle Suche im Internet, erhält vollständiges Markdown als Datei\n"
            "/help - Zeigt diese Hilfe an\n\n"
            "Über Crowdbot:\n"
            "Ich bin ein selbst gehosteter KI-Assistent. "
            "Unsere Unterhaltungen werden lokal gespeichert und ich merke mich an frühere Gespräche.\n\n"
            "Automatische Suche:\n"
            "Ich kann automatisch im Internet suchen, wenn du nach aktuellen Informationen fragst. "
            "Dazu musst du keinen speziellen Befehl nutzen - ich erkenne selbst, wann eine Suche sinnvoll ist.\n\n"
            "Für manuelle Suchen mit Datei-Download nutze /searchmd.\n\n"
            "Schreib mir einfach eine Nachricht, um ins Gespräch zu kommen!"
        )

        await update.message.reply_text(message)

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler für den /search Befehl.

        Sucht im Internet mit Jina Deep Research und liefert
        TTS-kompatible Ergebnisse in ganzen Sätzen.
        """
        if not await self.check_authorization(update):
            return

        user_id = update.effective_user.id

        # Prüfen, ob Suchanfrage vorhanden
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Bitte gib eine Suchanfrage an!\n"
                "Beispiel: /search Was ist Python?\n\n"
                "Mit /searchmd kannst du das vollständige Markdown als Datei erhalten."
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
            f"🔍 Suche nach: {query}\n\n"
            "Dies kann 30-60 Sekunden dauern..."
        )

        result = self.search_module.search(query, use_deep_search=True, format="tts")

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

        result = self.search_module.search(query, use_deep_search=True, format="markdown")

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

        # Anfrage an das LLM senden mit Intention-basierter Tool-Nutzung
        response = self.llm_client.chat_with_intention(
            user_message=user_message,
            conversation_history=conversation_history,
            max_tokens=2000
        )

        if response:
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

    def run(self):
        """Startet den Bot."""
        logger.info("Crowdbot wird gestartet...")
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
