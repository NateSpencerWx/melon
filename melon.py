#!/usr/bin/env python3

import json
import os
import subprocess
import urllib.request
import urllib.error
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.layout import Layout
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import ANSI

LOGO = """
╔═══════════════════════════════════════════════════════════╗
║                                                      beta ║
║   ███╗   ███╗███████╗██╗      ██████╗ ███╗   ██╗          ║
║   ████╗ ████║██╔════╝██║     ██╔═══██╗████╗  ██║          ║
║   ██╔████╔██║█████╗  ██║     ██║   ██║██╔██╗ ██║          ║
║   ██║╚██╔╝██║██╔══╝  ██║     ██║   ██║██║╚██╗██║          ║
║   ██║ ╚═╝ ██║███████╗███████╗╚██████╔╝██║ ╚████║          ║
║   ╚═╝     ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝          ║
║                                                           ║
║   Do (almost) anything on your computer with AI           ║
║                                                           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""

# Constants
DEFAULT_MODEL = "x-ai/grok-4-fast"
SAFETY_MODEL = "x-ai/grok-4-fast"  # Hardcoded for safety analysis
FAVORITES_FILE = ".melon_favorites.json"
SETTINGS_FILE = ".melon_settings.json"
CHATS_DIR = ".melon_chats"
DEFAULT_CHAT_NAME = "default"
CURRENT_VERSION = "0.2.1"
GITHUB_REPO = "NateSpencerWx/melon"

def parse_version(version_string):
    """Parse a version string like 'v0.2.0' or '0.2.0' into a tuple of integers."""
    # Remove 'v' prefix if present
    version_string = version_string.lstrip('v')
    try:
        return tuple(int(part) for part in version_string.split('.'))
    except (ValueError, AttributeError):
        return (0, 0, 0)

def check_for_updates():
    """
    Check GitHub for the latest release and compare with current version.
    Returns (has_update, latest_version, error_message)
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/vnd.github.v3+json')
        req.add_header('User-Agent', 'Melon-CLI')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get('tag_name', '')
            
            # Parse versions for comparison
            current = parse_version(CURRENT_VERSION)
            latest = parse_version(latest_version)
            
            # Check if latest is newer than current
            if latest > current:
                return True, latest_version, None
            return False, latest_version, None
            
    except urllib.error.URLError as e:
        # Network error - silently fail to not interrupt user experience
        return False, None, str(e)
    except Exception as e:
        # Other errors - silently fail
        return False, None, str(e)

def display_update_notification(latest_version):
    """Display a notification about available update."""
    print(f"\033[93m🎉 A new version of Melon is available: {CURRENT_VERSION} -> {latest_version}\033[0m")
    print(f"\033[93mTo update, run: pip install --upgrade git+https://github.com/{GITHUB_REPO}.git\033[0m\n")

def load_settings():
    """Load settings from file with error recovery"""
    default_settings = {"reasoning_enabled": False, "active_chat": DEFAULT_CHAT_NAME}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Validate structure
                if not isinstance(settings, dict):
                    raise ValueError("Settings file contains invalid data structure")
                # Ensure required keys exist
                if "reasoning_enabled" not in settings:
                    settings["reasoning_enabled"] = False
                if "active_chat" not in settings:
                    settings["active_chat"] = DEFAULT_CHAT_NAME
                return settings
        return default_settings
    except json.JSONDecodeError as e:
        # File is corrupted - backup and recreate
        print(f"\033[93m⚠️  Settings file corrupted ({e}). Creating backup and resetting...\033[0m")
        try:
            backup_file = f"{SETTINGS_FILE}.backup"
            if os.path.exists(SETTINGS_FILE):
                os.rename(SETTINGS_FILE, backup_file)
                print(f"\033[92m✓ Corrupted file backed up to {backup_file}\033[0m")
        except Exception as backup_error:
            print(f"\033[91m⚠️  Failed to backup corrupted settings file: {backup_error}\033[0m")
        return default_settings
    except (OSError, PermissionError) as e:
        print(f"\033[93m⚠️  Cannot read settings file: {e}. Using defaults.\033[0m")
        return default_settings
    except Exception as e:
        print(f"\033[93m⚠️  Unexpected error loading settings: {e}. Using defaults.\033[0m")
        return default_settings

def save_settings(settings):
    """Save settings to file with error handling"""
    try:
        # Validate input
        if not isinstance(settings, dict):
            raise ValueError("Settings must be a dictionary")
        
        # Write to temporary file first
        temp_file = f"{SETTINGS_FILE}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # If successful, replace the original file
        os.replace(temp_file, SETTINGS_FILE)
        return True
    except (OSError, PermissionError) as e:
        print(f"\033[91m❌ Cannot save settings: {e}\033[0m")
        return False
    except Exception as e:
        print(f"\033[91m❌ Unexpected error saving settings: {e}\033[0m")
        # Clean up temp file if it exists
        try:
            temp_file = f"{SETTINGS_FILE}.tmp"
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as cleanup_error:
            print(f"\033[93m⚠️  Failed to remove temp file {temp_file}: {cleanup_error}\033[0m")
        return False

def load_favorites():
    """Load favorite models from file with error recovery"""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r') as f:
                favorites = json.load(f)
                # Validate structure
                if not isinstance(favorites, list):
                    raise ValueError("Favorites file contains invalid data structure (expected list)")
                # Validate each item is a string
                favorites = [str(fav) for fav in favorites if fav]
                return favorites
        return []
    except json.JSONDecodeError as e:
        # File is corrupted - backup and recreate
        print(f"\033[93m⚠️  Favorites file corrupted ({e}). Creating backup and resetting...\033[0m")
        try:
            backup_file = f"{FAVORITES_FILE}.backup"
            if os.path.exists(FAVORITES_FILE):
                os.rename(FAVORITES_FILE, backup_file)
                print(f"\033[92m✓ Corrupted file backed up to {backup_file}\033[0m")
        except Exception:
            pass
        return []
    except (OSError, PermissionError) as e:
        print(f"\033[93m⚠️  Cannot read favorites file: {e}. Starting with empty list.\033[0m")
        return []
    except Exception as e:
        print(f"\033[93m⚠️  Unexpected error loading favorites: {e}. Starting with empty list.\033[0m")
        return []

def save_favorites(favorites):
    """Save favorite models to file with error handling"""
    try:
        # Validate input
        if not isinstance(favorites, list):
            raise ValueError("Favorites must be a list")
        
        # Ensure all items are strings
        favorites = [str(fav) for fav in favorites if fav]
        
        # Write to temporary file first
        temp_file = f"{FAVORITES_FILE}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(favorites, f, indent=2)
        
        # If successful, replace the original file
        os.replace(temp_file, FAVORITES_FILE)
        return True
    except (OSError, PermissionError) as e:
        print(f"\033[91m❌ Cannot save favorites: {e}\033[0m")
        return False
    except Exception as e:
        print(f"\033[91m❌ Unexpected error saving favorites: {e}\033[0m")
        # Clean up temp file if it exists
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass
        return False

def get_chat_file(chat_name):
    """Get the file path for a specific chat"""
    # Ensure chats directory exists
    if not os.path.exists(CHATS_DIR):
        os.makedirs(CHATS_DIR, exist_ok=True)
    return os.path.join(CHATS_DIR, f"{chat_name}.json")

def migrate_old_history():
    """Migrate old .melon_history.json to new multi-chat format"""
    old_history_file = ".melon_history.json"
    if os.path.exists(old_history_file):
        try:
            with open(old_history_file, 'r') as f:
                old_history = json.load(f)
            
            # Save to default chat
            if old_history and isinstance(old_history, list):
                save_history(old_history, DEFAULT_CHAT_NAME)
                print(f"\033[92m✓ Migrated old conversation history to '{DEFAULT_CHAT_NAME}' chat\033[0m")
            
            # Rename old file as backup
            backup_file = f"{old_history_file}.backup"
            os.rename(old_history_file, backup_file)
            print(f"\033[92m✓ Old history file backed up to {backup_file}\033[0m\n")
        except Exception as e:
            print(f"\033[93m⚠️  Could not migrate old history: {e}\033[0m")

def list_chats():
    """List all available chats"""
    if not os.path.exists(CHATS_DIR):
        return []
    try:
        chats = []
        for filename in os.listdir(CHATS_DIR):
            if filename.endswith('.json'):
                chat_name = filename[:-5]  # Remove .json extension
                chats.append(chat_name)
        return sorted(chats)
    except Exception:
        return []

def load_history(chat_name=None):
    """Load conversation history from a specific chat file with error recovery"""
    if chat_name is None:
        chat_name = DEFAULT_CHAT_NAME
    
    chat_file = get_chat_file(chat_name)
    
    try:
        if os.path.exists(chat_file):
            with open(chat_file, 'r') as f:
                history = json.load(f)
                # Validate structure
                if not isinstance(history, list):
                    raise ValueError("History file contains invalid data structure (expected list)")
                # Validate each message has required fields
                for msg in history:
                    if not isinstance(msg, dict) or 'role' not in msg:
                        raise ValueError("Invalid message format in history")
                return history
        return []
    except json.JSONDecodeError as e:
        # File is corrupted - backup and recreate
        print(f"\033[93m⚠️  Chat '{chat_name}' corrupted ({e}). Creating backup and resetting...\033[0m")
        try:
            backup_file = f"{chat_file}.backup"
            if os.path.exists(chat_file):
                os.rename(chat_file, backup_file)
                print(f"\033[92m✓ Corrupted file backed up to {backup_file}\033[0m")
        except Exception:
            pass
        return []
    except (OSError, PermissionError) as e:
        print(f"\033[93m⚠️  Cannot read chat '{chat_name}': {e}. Starting with empty history.\033[0m")
        return []
    except Exception as e:
        print(f"\033[93m⚠️  Unexpected error loading chat '{chat_name}': {e}. Starting with empty history.\033[0m")
        return []

def save_history(history, chat_name=None):
    """Save conversation history to a specific chat file with error handling"""
    if chat_name is None:
        chat_name = DEFAULT_CHAT_NAME
    
    chat_file = get_chat_file(chat_name)
    
    try:
        # Validate input
        if not isinstance(history, list):
            raise ValueError("History must be a list")
        
        # Write to temporary file first
        temp_file = f"{chat_file}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # If successful, replace the original file
        os.replace(temp_file, chat_file)
        return True
    except (OSError, PermissionError) as e:
        # Silently fail for history saving to not interrupt user flow
        return False
    except Exception as e:
        # Clean up temp file if it exists
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as cleanup_error:
            print(f"\033[93m⚠️  Failed to clean up temp file '{temp_file}': {cleanup_error}\033[0m")
        return False

def delete_chat(chat_name):
    """Delete a specific chat"""
    if chat_name == DEFAULT_CHAT_NAME:
        return False, "Cannot delete the default chat"
    
    chat_file = get_chat_file(chat_name)
    try:
        if os.path.exists(chat_file):
            os.remove(chat_file)
            return True, f"Chat '{chat_name}' deleted"
        return False, f"Chat '{chat_name}' not found"
    except Exception as e:
        return False, f"Error deleting chat: {e}"

def rename_chat(old_name, new_name):
    """Rename a chat"""
    if old_name == DEFAULT_CHAT_NAME:
        return False, "Cannot rename the default chat"
    
    if new_name == DEFAULT_CHAT_NAME:
        return False, f"Cannot use '{DEFAULT_CHAT_NAME}' as a name"
    
    old_file = get_chat_file(old_name)
    new_file = get_chat_file(new_name)
    
    try:
        if not os.path.exists(old_file):
            return False, f"Chat '{old_name}' not found"
        if os.path.exists(new_file):
            return False, f"Chat '{new_name}' already exists"
        os.rename(old_file, new_file)
        return True, f"Chat renamed from '{old_name}' to '{new_name}'"
    except Exception as e:
        return False, f"Error renaming chat: {e}"

def generate_chat_name(messages, client, current_name=None):
    """
    Use AI to generate a descriptive name for a chat based on its messages.
    Returns a short, descriptive name (2-4 words max).
    For dynamic renaming, uses recent messages to reflect current conversation topic.
    """
    try:
        # Get user messages to understand the topic
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        if not user_messages:
            # Fallback to timestamp-based name
            import time
            return f"chat-{int(time.time())}"
        
        # For dynamic renaming, focus on recent messages to capture topic evolution
        # Use last 3-5 user messages for better context of current conversation
        recent_count = min(5, len(user_messages))
        recent_messages = user_messages[-recent_count:]
        
        # Build context from recent messages
        context = " ".join([msg.get("content", "")[:150] for msg in recent_messages])
        
        response = client.chat.completions.create(
            model=SAFETY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a chat naming assistant. Generate a short, descriptive name (2-4 words max) for a conversation based on its content. "
                        "The name should be lowercase with hyphens, like 'python-help', 'work-project', or 'vacation-planning'. "
                        "Focus on the main topic of the conversation. "
                        "Only respond with the name, nothing else."
                    )
                },
                {
                    "role": "user",
                    "content": f"Generate a short name for a conversation about: {context}"
                }
            ],
            max_tokens=20
        )
        
        # Clean up the response
        name = response.choices[0].message.content.strip().lower()
        # Remove any quotes, extra spaces, and ensure it's a valid filename
        name = name.replace('"', '').replace("'", '').replace(' ', '-')
        # Remove any invalid characters
        import re
        name = re.sub(r'[^a-z0-9\-]', '', name)
        # Limit length
        name = name[:50]
        
        # Don't check uniqueness if we're renaming the current chat
        # (the current name will be freed up)
        if current_name != name:
            chats = list_chats()
            # Remove current_name from the list if it exists (we're renaming it)
            if current_name and current_name in chats:
                chats = [c for c in chats if c != current_name]
            
            if name in chats:
                import time
                name = f"{name}-{int(time.time()) % 10000}"
        
        return name if name else f"chat-{int(time.time())}"
    except Exception as e:
        # Fallback to timestamp-based name
        import time
        return f"chat-{int(time.time())}"

def dynamic_rename_chat(messages, client, current_chat, settings):
    """
    Dynamically rename a chat based on the current conversation.
    Returns (success, new_name, message)
    """
    # Don't rename the default chat
    if current_chat == DEFAULT_CHAT_NAME:
        return False, current_chat, "Default chat cannot be renamed"
    
    try:
        # Generate a new name based on current conversation
        new_name = generate_chat_name(messages, client, current_name=current_chat)
        
        # If the name hasn't changed significantly, don't rename
        if new_name == current_chat:
            return False, current_chat, "Chat name unchanged"
        
        # Rename the chat file
        old_file = get_chat_file(current_chat)
        new_file = get_chat_file(new_name)
        
        if os.path.exists(old_file):
            os.rename(old_file, new_file)
            
            # Update settings to reflect new name
            settings["active_chat"] = new_name
            save_settings(settings)
            
            return True, new_name, f"Chat renamed from '{current_chat}' to '{new_name}'"
        else:
            return False, current_chat, f"Chat file not found"
    
    except Exception as e:
        return False, current_chat, f"Error during dynamic rename: {e}"

def is_command_modifying(command: str, client) -> tuple[bool, str]:
    """
    Use AI to determine if a command modifies the system and get a description.
    Returns (is_modifying, description)
    """
    try:
        # Enable reasoning for safety analysis to improve accuracy
        response = client.chat.completions.create(
            model=SAFETY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a command safety analyzer. Your job is to determine if a shell command will modify the system (write, delete, install, update, etc.) or just read information.\n"
                        "Respond with a JSON object in this exact format:\n"
                        "{\n"
                        '  "modifies": true/false,\n'
                        '  "description": "Brief description of what the command does"\n'
                        "}\n"
                        "Commands that MODIFY include: write operations, file creation/deletion, installations, updates, permission changes, network operations that send data, etc.\n"
                        "Commands that are READ-ONLY include: listing files, reading file contents, checking status, viewing information, etc."
                    )
                },
                {
                    "role": "user",
                    "content": f"Analyze this command: {command}"
                }
            ],
            extra_body={"reasoning": {"effort": "high"}}
        )
        
        # Parse the JSON response
        response_text = response.choices[0].message.content.strip()
        # Extract JSON from markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        return result.get("modifies", True), result.get("description", "No description available")
    except Exception as e:
        # If analysis fails, assume it's modifying to be safe
        return True, f"Unable to analyze command (error: {e}). Treating as potentially modifying."

def run_terminal_command(command: str, client=None, console=None):
    """
    Run a terminal command with optional review for modifying commands.
    If client is provided, will check if command is modifying and prompt user for approval.
    """
    # If we have a client, do the safety check
    if client:
        is_modifying, description = is_command_modifying(command, client)
        
        if is_modifying:
            # Show the command and description to the user
            if console:
                console.print(f"\n[yellow]⚠️  Command requires approval:[/yellow]")
                console.print(f"[cyan]Command:[/cyan] {command}")
                console.print(f"[cyan]Description:[/cyan] {description}")
            else:
                print(f"\n\033[93m⚠️  Command requires approval:\033[0m")
                print(f"\033[96mCommand:\033[0m {command}")
                print(f"\033[96mDescription:\033[0m {description}")
            
            # Prompt user for action
            while True:
                choice = input("\n\033[95mDo you want to [A]ccept, [D]eny, or [E]dit this command? \033[0m").strip().lower()
                
                if choice in ['a', 'accept']:
                    break  # Proceed with the command
                elif choice in ['d', 'deny']:
                    reason = input("\033[95m📝 Why did you deny this command? (This helps the AI adjust): \033[0m").strip()
                    if reason:
                        return {"error": f"Command denied by user. Reason: {reason}. Please try a different approach based on this feedback.", "denied": True}
                    else:
                        return {"error": "Command denied by user. Please try a different approach.", "denied": True}
                elif choice in ['e', 'edit']:
                    new_command = input("\033[95mEnter the modified command: \033[0m").strip()
                    if new_command:
                        command = new_command
                        # Re-check the edited command
                        is_modifying, description = is_command_modifying(command, client)
                        if is_modifying:
                            if console:
                                console.print(f"\n[yellow]Updated command still requires approval:[/yellow]")
                                console.print(f"[cyan]Command:[/cyan] {command}")
                                console.print(f"[cyan]Description:[/cyan] {description}")
                            else:
                                print(f"\n\033[93mUpdated command still requires approval:\033[0m")
                                print(f"\033[96mCommand:\033[0m {command}")
                                print(f"\033[96mDescription:\033[0m {description}")
                            continue  # Ask again
                        else:
                            break  # Edited command is read-only, proceed
                    else:
                        print("\033[91mNo command entered. Denying.\033[0m")
                        reason = input("\033[95m📝 Why did you deny this command? (This helps the AI adjust): \033[0m").strip()
                        if reason:
                            return {"error": f"Command denied by user. Reason: {reason}. Please try a different approach based on this feedback.", "denied": True}
                        else:
                            return {"error": "Command denied by user. Please try a different approach.", "denied": True}
                else:
                    print("\033[91mInvalid choice. Please enter A, D, or E.\033[0m")
    
    # Execute the command
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        return {"output": output, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 60 seconds"}
    except Exception as e:
        return {"error": str(e)}

tool_definition = {
    "type": "function",
    "function": {
        "name": "run_terminal_command",
        "description": "Run a terminal command on the user's computer and return the output. Use this for actions that require executing commands. Be cautious with commands that could delete files, modify system files, or perform other risky operations. BE AS SAFE AS POSSIBLE WHILE STILL DOING EVERYTHING YOU CAN TO FULFILL THE USER'S REQUEST.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run."
                }
            },
            "required": ["command"]
        }
    }
}

def create_tools_map(client, console):
    """Create a tools map with closures that have access to client and console"""
    return {
        "run_terminal_command": lambda command: run_terminal_command(command, client, console)
    }

def handle_model_selection(current_model, console):
    """Handle the model selection interface"""
    favorites = load_favorites()
    
    console.print("\n[cyan]🤖 Model Selection[/cyan]")
    console.print(f"[yellow]Current model:[/yellow] {current_model}")
    console.print("\n[cyan]Options:[/cyan]")
    console.print("  [1] Enter a model name")
    console.print("  [2] Select from favorites")
    console.print("  [3] Add current model to favorites")
    console.print("  [4] Manage favorites")
    console.print("  [5] Cancel")
    
    choice = input("\n\033[95mSelect an option (1-5): \033[0m").strip()
    
    if choice == "1":
        # Enter a model name
        model_name = input("\033[95mEnter model name (e.g., openai/gpt-4o, anthropic/claude-3.5-sonnet): \033[0m").strip()
        if model_name:
            console.print(f"[green]✓ Switched to model: {model_name}[/green]")
            return model_name
    
    elif choice == "2":
        # Select from favorites
        if not favorites:
            console.print("[yellow]No favorites saved yet. Add some first![/yellow]")
            return current_model
        
        console.print("\n[cyan]📌 Favorite Models:[/cyan]")
        for i, fav in enumerate(favorites, 1):
            console.print(f"  [{i}] {fav}")
        
        try:
            fav_choice = int(input("\n\033[95mSelect a favorite (number): \033[0m").strip())
            if 1 <= fav_choice <= len(favorites):
                selected_model = favorites[fav_choice - 1]
                console.print(f"[green]✓ Switched to model: {selected_model}[/green]")
                return selected_model
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Invalid input[/red]")
    
    elif choice == "3":
        # Add current model to favorites
        if current_model in favorites:
            console.print(f"[yellow]Model '{current_model}' is already in favorites[/yellow]")
        else:
            favorites.append(current_model)
            if save_favorites(favorites):
                console.print(f"[green]✓ Added '{current_model}' to favorites[/green]")
            else:
                console.print("[red]Failed to save favorites[/red]")
    
    elif choice == "4":
        # Manage favorites
        if not favorites:
            console.print("[yellow]No favorites to manage[/yellow]")
            return current_model
        
        console.print("\n[cyan]📌 Manage Favorites:[/cyan]")
        for i, fav in enumerate(favorites, 1):
            console.print(f"  [{i}] {fav}")
        console.print("\n[cyan]Enter the number to remove, or 'c' to cancel:[/cyan]")
        
        remove_choice = input("\033[95m> \033[0m").strip().lower()
        if remove_choice == 'c':
            return current_model
        
        try:
            remove_idx = int(remove_choice) - 1
            if 0 <= remove_idx < len(favorites):
                removed = favorites.pop(remove_idx)
                if save_favorites(favorites):
                    console.print(f"[green]✓ Removed '{removed}' from favorites[/green]")
                else:
                    console.print("[red]Failed to save favorites[/red]")
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Invalid input[/red]")
    
    elif choice == "5":
        # Cancel
        console.print("[yellow]Cancelled[/yellow]")
    
    else:
        console.print("[red]Invalid option[/red]")
    
    return current_model


def process_model_command(command: str, current_model: str, console) -> str:
    """Handle quick model switching via slash commands"""
    favorites = load_favorites()
    parts = command.split(maxsplit=1)

    if len(parts) == 1:
        return handle_model_selection(current_model, console)

    target = parts[1].strip()

    if not target:
        return handle_model_selection(current_model, console)

    if target in {"?", "list"}:
        if favorites:
            console.print("\n[cyan]📌 Favorite Models:[/cyan]")
            for idx, fav in enumerate(favorites, 1):
                console.print(f"  [{idx}] {fav}")
        else:
            console.print("[yellow]No favorites saved yet. Use the model menu to add some.[/yellow]")
        return current_model

    if target.isdigit():
        fav_index = int(target) - 1
        if 0 <= fav_index < len(favorites):
            selected = favorites[fav_index]
            console.print(f"[green]✓ Switched to model: {selected}[/green]")
            return selected
        console.print("[red]Favorite number out of range[/red]")
        return current_model

    console.print(f"[green]✓ Switched to model: {target}[/green]")
    return target


def toggle_reasoning(settings: dict, console, target_state: str | None = None) -> dict:
    """Toggle reasoning setting with optional explicit on/off control"""
    current_state = settings.get("reasoning_enabled", False)

    if target_state in {"on", "enable", "enabled"}:
        new_state = True
    elif target_state in {"off", "disable", "disabled"}:
        new_state = False
    else:
        new_state = not current_state

    settings["reasoning_enabled"] = new_state
    if save_settings(settings):
        status_word = "enabled" if new_state else "disabled"
        console.print(f"[green]✓ Reasoning {status_word}[/green]")
    else:
        console.print("[red]Failed to save settings[/red]")
    return settings


def handle_chat_management(console, settings):
    """Handle the chat management interface"""
    current_chat = settings.get("active_chat", DEFAULT_CHAT_NAME)
    chats = list_chats()
    
    console.print("\n[cyan]💬 Chat Management[/cyan]")
    console.print(f"[yellow]Current chat:[/yellow] {current_chat}")
    
    if chats:
        console.print("\n[cyan]Available chats:[/cyan]")
        for i, chat in enumerate(chats, 1):
            marker = " ← current" if chat == current_chat else ""
            console.print(f"  [{i}] {chat}{marker}")
    else:
        console.print("\n[yellow]No saved chats yet[/yellow]")
    
    console.print("\n[cyan]Options:[/cyan]")
    console.print("  [1] Switch to a different chat")
    console.print("  [2] Create a new chat")
    console.print("  [3] Rename a chat")
    console.print("  [4] Delete a chat")
    console.print("  [5] Cancel")
    
    choice = input("\n\033[95mSelect an option (1-5): \033[0m").strip()
    
    if choice == "1":
        # Switch chat
        if not chats:
            console.print("[yellow]No chats available to switch to[/yellow]")
            return settings
        
        console.print("\n[cyan]Select a chat:[/cyan]")
        for i, chat in enumerate(chats, 1):
            console.print(f"  [{i}] {chat}")
        
        try:
            chat_choice = int(input("\n\033[95mEnter chat number: \033[0m").strip())
            if 1 <= chat_choice <= len(chats):
                selected_chat = chats[chat_choice - 1]
                settings["active_chat"] = selected_chat
                if save_settings(settings):
                    console.print(f"[green]✓ Switched to chat: {selected_chat}[/green]")
                    console.print("[yellow]⚠️  Please restart Melon to load the new chat[/yellow]")
                else:
                    console.print("[red]Failed to save settings[/red]")
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Invalid input[/red]")
    
    elif choice == "2":
        # Create new chat
        chat_name = input("\033[95mEnter new chat name: \033[0m").strip()
        if not chat_name:
            console.print("[red]Chat name cannot be empty[/red]")
        elif chat_name in chats:
            console.print(f"[red]Chat '{chat_name}' already exists[/red]")
        else:
            # Create empty chat and switch to it
            save_history([], chat_name)
            settings["active_chat"] = chat_name
            if save_settings(settings):
                console.print(f"[green]✓ Created and switched to chat: {chat_name}[/green]")
                console.print("[yellow]⚠️  Please restart Melon to load the new chat[/yellow]")
            else:
                console.print("[red]Failed to save settings[/red]")
    
    elif choice == "3":
        # Rename chat
        if not chats:
            console.print("[yellow]No chats to rename[/yellow]")
            return settings
        
        console.print("\n[cyan]Select a chat to rename:[/cyan]")
        for i, chat in enumerate(chats, 1):
            console.print(f"  [{i}] {chat}")
        
        try:
            chat_choice = int(input("\n\033[95mEnter chat number: \033[0m").strip())
            if 1 <= chat_choice <= len(chats):
                old_name = chats[chat_choice - 1]
                new_name = input(f"\033[95mEnter new name for '{old_name}': \033[0m").strip()
                if new_name:
                    success, message = rename_chat(old_name, new_name)
                    if success:
                        console.print(f"[green]✓ {message}[/green]")
                        # Update active chat if it was renamed
                        if settings.get("active_chat") == old_name:
                            settings["active_chat"] = new_name
                            save_settings(settings)
                    else:
                        console.print(f"[red]{message}[/red]")
                else:
                    console.print("[red]New name cannot be empty[/red]")
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Invalid input[/red]")
    
    elif choice == "4":
        # Delete chat
        if not chats or len(chats) == 1:
            console.print("[yellow]Need at least 2 chats to delete one[/yellow]")
            return settings
        
        console.print("\n[cyan]Select a chat to delete:[/cyan]")
        for i, chat in enumerate(chats, 1):
            console.print(f"  [{i}] {chat}")
        
        try:
            chat_choice = int(input("\n\033[95mEnter chat number: \033[0m").strip())
            if 1 <= chat_choice <= len(chats):
                chat_name = chats[chat_choice - 1]
                confirm = input(f"\033[95m⚠️  Delete chat '{chat_name}'? (yes/no): \033[0m").strip().lower()
                if confirm == "yes":
                    success, message = delete_chat(chat_name)
                    if success:
                        console.print(f"[green]✓ {message}[/green]")
                        # Switch to default if we deleted the active chat
                        if settings.get("active_chat") == chat_name:
                            settings["active_chat"] = DEFAULT_CHAT_NAME
                            save_settings(settings)
                            console.print(f"[yellow]Switched to '{DEFAULT_CHAT_NAME}' chat[/yellow]")
                    else:
                        console.print(f"[red]{message}[/red]")
                else:
                    console.print("[yellow]Deletion cancelled[/yellow]")
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Invalid input[/red]")
    
    elif choice == "5":
        console.print("[yellow]Cancelled[/yellow]")
    
    else:
        console.print("[red]Invalid option[/red]")
    
    return settings


def create_input_session():
    """Create a prompt session with Ctrl key bindings"""
    kb = KeyBindings()
    
    # Store action that was triggered
    class KeyAction:
        action = None
    
    @kb.add('c-n')  # Ctrl+N for new chat
    def _(event):
        KeyAction.action = 'new_chat'
        event.app.exit(result='__CTRL_N__')
    
    @kb.add('c-o')  # Ctrl+O for model selection (changed from Ctrl+M which conflicts with Enter)
    def _(event):
        KeyAction.action = 'model'
        event.app.exit(result='__CTRL_O__')
    
    @kb.add('c-r')  # Ctrl+R for reasoning toggle
    def _(event):
        KeyAction.action = 'reasoning'
        event.app.exit(result='__CTRL_R__')
    
    @kb.add('c-s')  # Ctrl+S for switching chats
    def _(event):
        KeyAction.action = 'switch_chat'
        event.app.exit(result='__CTRL_S__')
    
    session = PromptSession(key_bindings=kb)
    return session, KeyAction


def display_status(console, current_model, settings):
    """Show the current model and reasoning status with quick command hints"""
    reasoning_on = settings.get("reasoning_enabled", False)
    reasoning_label = "[green]ON[/green]" if reasoning_on else "[red]OFF[/red]"
    active_chat = settings.get("active_chat", DEFAULT_CHAT_NAME)
    console.print(
        f"[bold cyan]Chat[/bold cyan]: {active_chat}    "
        f"[bold cyan]Model[/bold cyan]: {current_model}    "
        f"[bold cyan]Reasoning[/bold cyan]: {reasoning_label}"
    )
    console.print("")


def handle_settings(console):
    """Handle the settings interface"""
    settings = load_settings()
    
    console.print("\n[cyan]⚙️  Settings[/cyan]")
    console.print(f"[yellow]Reasoning:[/yellow] {'Enabled' if settings.get('reasoning_enabled', False) else 'Disabled'}")
    console.print("\n[cyan]Options:[/cyan]")
    console.print("  [1] Toggle reasoning (enable extended thinking for complex queries)")
    console.print("  [2] Cancel")
    
    choice = input("\n\033[95mSelect an option: \033[0m").strip()
    
    if choice == "1":
        settings = toggle_reasoning(settings, console)
    
    elif choice == "2":
        # Cancel
        console.print("[yellow]Cancelled[/yellow]")
    
    else:
        console.print("[red]Invalid option[/red]")
    
    console.print(f"[yellow]Reasoning:[/yellow] {'Enabled' if settings.get('reasoning_enabled', False) else 'Disabled'}")
    return settings


def handle_chat_switch(console, settings, current_chat):
    """Handle switching between chats"""
    chats = list_chats()
    
    if not chats:
        console.print("[yellow]No chats available[/yellow]")
        return current_chat
    
    console.print("\n[cyan]💬 Available Chats:[/cyan]")
    for i, chat in enumerate(chats, 1):
        # Load history to get message count
        history = load_history(chat)
        msg_count = len(history)
        current_marker = " ← current" if chat == current_chat else ""
        console.print(f"  [{i}] {chat} ({msg_count} messages){current_marker}")
    
    console.print("\n[dim]Enter number to switch, or press Enter to cancel[/dim]")
    choice = input("\033[95m> \033[0m").strip()
    
    if not choice:
        console.print("[yellow]Cancelled[/yellow]")
        return current_chat
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(chats):
            selected_chat = chats[idx]
            if selected_chat != current_chat:
                # Update settings
                settings["active_chat"] = selected_chat
                save_settings(settings)
                
                # Load history count for display
                history = load_history(selected_chat)
                msg_count = len(history)
                console.print(f"[green]✓ Switched to '{selected_chat}' ({msg_count} messages)[/green]")
                return selected_chat
            else:
                console.print("[yellow]Already in this chat[/yellow]")
                return current_chat
        else:
            console.print("[red]Invalid selection[/red]")
            return current_chat
    except ValueError:
        console.print("[red]Invalid input[/red]")
        return current_chat



def main():
    print("\033[91m" + LOGO + "\033[0m")  # Red color
    console = Console()
    
    # Check for updates on startup
    has_update, latest_, error = check_for_updates()
    if has_update and latest_:
        display_update_notification(latest_)
    elif not has_update and latest_ and not error:
        # Successfully checked and no update available
        print("\033[92m✓ Melon is up to date ( {0})\033[0m\n".format(CURRENT_))
    
    load_dotenv()
    api_key = os.getenv('OPENROUTER_API_KEY')

    if not api_key:
        print("\033[93m⚠️  No OpenRouter API key found in .env file.\033[0m")
        print("\n📋 To get started:")
        print("   1. Sign up at: \033[94mhttps://openrouter.ai/\033[0m")
        print("   2. Get your API key from: \033[94mhttps://openrouter.ai/keys\033[0m")
        print("")
        print(" 💡You can use credits from other API providers with OpenRouter: \033[94mhttps://openrouter.ai/docs/use-cases/byok\033[0m")
        print()
        while True:
            api_key = input("🔑 Enter your OpenRouter API key: ").strip()
            if not api_key:
                print("\033[91m❌ No API key provided. Exiting.\033[0m")
                return
            # Validate the API key
            try:
                test_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                    timeout=10
                )
                # Make a test API call to verify the key
                test_response = test_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Say 'OK' if this works. You ABSOLUTELY MUST respond with only 'OK' if you see this message."}
                    ],
                    max_tokens=10
                )
                if "OK" not in test_response.choices[0].message.content:
                    raise Exception("Test API call failed")
                break  # Valid key, exit loop
            except Exception as e:
                print(f"\033[91m❌ Invalid API key: {e}\033[0m")
                print("\033[93m🔄 Please try again.\033[0m")
                continue
        with open('.env', 'w') as f:
            f.write(f'OPENROUTER_API_KEY={api_key}\n')
        print("\033[92m✓ API key saved to .env\033[0m\n")
    else:
        print("\033[92m✓ API key loaded successfully\033[0m\n")

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=3600
        )
    except Exception as e:
        print(f"\033[91m❌ Error initializing client: {e}\033[0m")
        return

    # Create tools map with access to client and console
    tools_map = create_tools_map(client, console)

    # Initialize current model and settings
    current_model = DEFAULT_MODEL
    settings = load_settings()
    active_chat = settings.get("active_chat", DEFAULT_CHAT_NAME)

    # Migrate old single-file history if it exists
    migrate_old_history()

    # Initialize conversation history with system message
    system_message = {
        "role": "system",
        "content": (
            "Your name is Melon, an AI assistant. "
            "In addition to your native capabilities, you have the ability to run terminal commands on the user's computer if needed to help complete/address the user's request/query. "
            "Commands are automatically reviewed: read-only commands execute immediately, but commands that modify the system (write, delete, install, etc.) will prompt the user for approval before execution. "
            "Do not worry about asking for permission - the review system handles this automatically. Just focus on fulfilling the user's request using the tool calls available to you. "
            "If a user denies a command, acknowledge it gracefully and offer alternatives or ask how they'd like to proceed. "
            "Additional background information: "
            "You live in the terminal, inside a command line interface, where the user interacts with you. The name of the interface is the same as your name, Melon. "
            "If the user is asking you about Melon, check out its public repository on GitHub (NateSpencerWx/melon) for more information."
        )
    }
    
    # Load persisted conversation history from active chat
    loaded_history = load_history(active_chat)
    if loaded_history:
        # Verify the first message is a system message, if not prepend it
        if loaded_history[0].get("role") != "system":
            messages = [system_message] + loaded_history
        else:
            # Replace the old system message with the current one
            messages = [system_message] + loaded_history[1:]
        # Calculate actual conversation messages (excluding system message)
        conversation_count = len([m for m in messages if m.get("role") != "system"])
        print(f"\033[92m✓ Loaded {conversation_count} conversation messages from '{active_chat}' chat\033[0m\n")
    else:
        messages = [system_message]

    print("\033[96m💡 Use ^N for new chat, ^S to switch chat, ^O for model, ^R for reasoning. Press ^C to exit.\033[0m")
    print("\033[90m" + "─" * 60 + "\033[0m\n")
    
    # Create prompt session with key bindings
    session, key_action = create_input_session()
    
    while True:
        try:
            display_status(console, current_model, settings)
            
            # Use prompt_toolkit session for input with key bindings
            try:
                user_input = session.prompt(ANSI("\033[95m🍉 \033[0m")).strip()
            except KeyboardInterrupt:
                print("\n\033[91m👋 Thanks for using Melon!\033[0m")
                break
            except EOFError:
                print("\n\033[91m👋 Thanks for using Melon!\033[0m")
                break
            
            # Check if a keyboard shortcut was triggered
            if user_input == '__CTRL_N__':
                # Ctrl+N - Create new chat
                if len(messages) > 1:  # Has some conversation
                    console.print("\n[cyan]Creating new chat...[/cyan]")
                    # Generate name based on current conversation
                    chat_name = generate_chat_name(messages, client)
                    console.print(f"[yellow]AI named this chat:[/yellow] {chat_name}")
                    
                    # Save current conversation to the new chat
                    save_history(messages[1:], chat_name)
                    console.print(f"[green]✓ Saved current conversation to '{chat_name}'[/green]")
                else:
                    # No conversation yet, just create timestamp-based chat
                    import time
                    chat_name = f"chat-{int(time.time())}"
                    save_history([], chat_name)
                    console.print(f"[green]✓ Created new chat: {chat_name}[/green]")
                
                # Switch to the new chat
                settings["active_chat"] = chat_name
                save_settings(settings)
                active_chat = chat_name
                
                # Reset messages for new conversation
                messages = [system_message]
                console.print("[cyan]Starting fresh conversation in new chat[/cyan]")
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue
                
            elif user_input == '__CTRL_O__':
                # Ctrl+O - Model selection
                current_model = handle_model_selection(current_model, console)
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue
                
            elif user_input == '__CTRL_R__':
                # Ctrl+R - Toggle reasoning
                settings = toggle_reasoning(settings, console)
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue
                
            elif user_input == '__CTRL_S__':
                # Ctrl+S - Switch chat
                new_chat = handle_chat_switch(console, settings, active_chat)
                if new_chat != active_chat:
                    # Load the new chat's history
                    active_chat = new_chat
                    loaded_history = load_history(active_chat)
                    
                    # Merge with system message
                    if loaded_history and loaded_history[0].get("role") != "system":
                        messages = [system_message] + loaded_history
                    else:
                        # Replace old system message with current one
                        messages = [system_message] + loaded_history[1:] if loaded_history else [system_message]
                    
                    console.print(f"[cyan]Loaded {len([m for m in messages if m.get('role') != 'system'])} messages[/cyan]")
                
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue
            
            if not user_input:
                continue

            print("\n\033[93mThinking...\033[0m")

            try:
                # Add user message to conversation
                messages.append({"role": "user", "content": user_input})
                print("\033[96m🤔 Getting a response from Melon...\033[0m")
                
                # Handle tool calls in a loop until we get a final response
                max_iterations = 10  # Prevent infinite loops
                iteration = 0
                
                while iteration < max_iterations:
                    # Build API call parameters
                    api_params = {
                        "model": current_model,
                        "messages": messages,
                        "tools": [tool_definition]
                    }
                    
                    # Add reasoning if enabled
                    if settings.get('reasoning_enabled', False):
                        api_params["extra_body"] = {"reasoning": {"effort": "high"}}
                    
                    response = client.chat.completions.create(**api_params)
                    
                    assistant_message = response.choices[0].message
                    
                    # Check if there are tool calls
                    if assistant_message.tool_calls:
                        print(f"\033[96m🔧 Melon wants to run some commands: {[tc.function.name for tc in assistant_message.tool_calls]}\033[0m")
                        
                        # Add assistant message with tool calls to history
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message.content,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }
                                for tc in assistant_message.tool_calls
                            ]
                        })

                        for tool_call in assistant_message.tool_calls:
                            print(f"\033[96m⏳ Running: {tool_call.function.name}...\033[0m")
                            function_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)
                            result = tools_map[function_name](**function_args)
                            print(f"\033[96m✅ Done!\033[0m")
                            
                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(result)
                            })

                        print("\033[96m🤔 Melon is thinking about the results...\033[0m")
                        iteration += 1
                    else:
                        # No more tool calls, we have a final response
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message.content
                        })
                        break

                # Check if we hit max iterations
                if iteration >= max_iterations:
                    print("\033[93m⚠️  Maximum iteration limit reached. Melon tried to make too many tool calls in succession.\033[0m")
                    print(f"\033[90mDebug - Response object: {response}\033[0m")
                # Check if response has content
                elif assistant_message.content:
                    print("\033[96m💬 Here's what Melon has to say:\033[0m")
                    console.print(Markdown(assistant_message.content))
                else:
                    print("\033[93m⚠️  Melon didn't have anything to say. This might be due to rate limiting or an API issue.\033[0m")
                    print(f"\033[90mDebug - Response object: {response}\033[0m")
                
                # Save conversation history after each successful interaction
                # Skip the system message when saving (it's always added on load)
                save_history(messages[1:], active_chat)
                
                # Dynamic chat renaming: rename chat based on evolving conversation
                # Only rename if there are actual user messages (not just system/tool messages)
                user_message_count = len([m for m in messages if m.get("role") == "user"])
                if user_message_count >= 1:  # At least one user message
                    success, new_name, rename_msg = dynamic_rename_chat(messages[1:], client, active_chat, settings)
                    if success:
                        # Update active_chat reference (rename happens silently)
                        active_chat = new_name
            except Exception as e:
                print(f"\033[91m❌ Error: {e}\033[0m")
                import traceback
                print(f"\033[90m{traceback.format_exc()}\033[0m")

            print("\033[90m" + "─" * 60 + "\033[0m\n")
        except KeyboardInterrupt:
            print("\n\033[92m👋 Thanks for using Melon!\033[0m")
            break

if __name__ == "__main__":
    main()
