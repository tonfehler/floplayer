"""Discord Rich Presence: Verbindung, Statusaktualisierung und Persistenz der Einstellungen."""

import time

from pypresence import ActivityType, Presence

# Key des in Discord hochgeladenen Rich-Presence-Art-Assets (icon.png)
LARGE_IMAGE_KEY = "icon"
GITHUB_URL = "https://github.com/tonfehler/floplayer"


class DiscordPresenceManager:
    """Kapselt Verbindungsaufbau/-abbau und Status-Updates zu Discord Rich Presence."""

    def __init__(self, settings):
        self.settings = settings
        self.enabled = False
        self.client_id = ""
        self._presence = None

    def restore(self):
        """Gespeicherte Einstellungen laden und ggf. automatisch verbinden."""
        self.client_id = str(self.settings.value("discord/client_id", "") or "")
        enabled = self.settings.value("discord/enabled", False)
        enabled = str(enabled).lower() in ("1", "true", "yes")
        if enabled:
            self.enable()

    def set_client_id(self, client_id: str):
        self.client_id = client_id
        self.settings.setValue("discord/client_id", client_id)

    def enable(self):
        """Aktiviert Discord-RPC und versucht zu verbinden. Gibt Fehlermeldung zurück oder None bei Erfolg."""
        self.enabled = True
        self.settings.setValue("discord/enabled", True)
        self.disconnect()

        if not self.client_id:
            return "Keine Client ID eingetragen."

        try:
            presence = Presence(self.client_id)
            presence.connect()
        except Exception as exc:
            self._presence = None
            return f"Verbindung fehlgeschlagen: {exc}"

        self._presence = presence
        return None

    def disable(self):
        self.enabled = False
        self.settings.setValue("discord/enabled", False)
        self.disconnect()

    def disconnect(self):
        if self._presence is not None:
            try:
                self._presence.close()
            except Exception:
                pass
            self._presence = None

    def update_now_playing(self, title: str, artist: str, playing: bool, position_ms: int):
        if not self.enabled or self._presence is None:
            return

        try:
            if playing:
                start_epoch = int(time.time() - position_ms / 1000)
                self._presence.update(
                    details=title,
                    state=artist or "FloPlayer",
                    start=start_epoch,
                    large_image=LARGE_IMAGE_KEY,
                    large_text="FloPlayer",
                    activity_type=ActivityType.LISTENING,
                    buttons=[{"label": "GitHub", "url": GITHUB_URL}],
                )
            else:
                state = f"Pausiert – {artist}" if artist else "Pausiert"
                self._presence.update(
                    details=title,
                    state=state,
                    large_image=LARGE_IMAGE_KEY,
                    large_text="FloPlayer",
                    activity_type=ActivityType.LISTENING,
                    buttons=[{"label": "GitHub", "url": GITHUB_URL}],
                )
        except Exception:
            self._presence = None

    def clear_now_playing(self):
        if not self.enabled or self._presence is None:
            return
        try:
            self._presence.clear()
        except Exception:
            self._presence = None
