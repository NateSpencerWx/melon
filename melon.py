#!/usr/bin/env python3

import json
import os
import subprocess
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

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

def load_settings():
    """Load settings from file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        return {"reasoning_enabled": False}  # Default settings
    except Exception:
        return {"reasoning_enabled": False}

def save_settings(settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False

def load_favorites():
    """Load favorite models from file"""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception:
        return []

def save_favorites(favorites):
    """Save favorite models to file"""
    try:
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(favorites, f, indent=2)
        return True
    except Exception:
        return False

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


def display_status(console, current_model, settings):
    """Show the current model and reasoning status with quick command hints"""
    reasoning_on = settings.get("reasoning_enabled", False)
    reasoning_label = "[green]ON[/green]" if reasoning_on else "[red]OFF[/red]"
    console.print(
        f"[bold cyan]Model[/bold cyan]: {current_model}    "
        f"[bold cyan]Reasoning[/bold cyan]: {reasoning_label}"
    )
    console.print(
        "[dim]Shortcuts: /m (model favorite #) switch model · /r (on|off) toggle reasoning · /clear reset history[/dim]"
    )
    console.print("")


def handle_settings(console):
    """Handle the settings interface"""
    settings = load_settings()
    
    console.print("\n[cyan]⚙️  Settings[/cyan]")
    console.print(f"[yellow]Reasoning:[/yellow] {'Enabled' if settings.get('reasoning_enabled', False) else 'Disabled'}")
    console.print("[dim]Tip: You can also use '/r on' or '/r off' at the main prompt for instant changes.[/dim]")
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


def main():
    print("\033[91m" + LOGO + "\033[0m")  # Red color
    console = Console()
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
    messages = [system_message]

    print("\033[96m💡 Type your request in natural language. Use '/m' to switch models, '/r' to toggle reasoning, '/clear' to reset, and ^C to leave.\033[0m")
    print("\033[90m" + "─" * 60 + "\033[0m\n")
    while True:
        try:
            display_status(console, current_model, settings)
            user_input = input("\033[95m🍉 \033[0m").strip()
            if not user_input:
                continue

            # Check for quick commands
            lowered_input = user_input.lower()

            if lowered_input in {"model", "/model"}:
                current_model = process_model_command("/m", current_model, console)
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue

            if lowered_input.startswith("/m"):
                current_model = process_model_command(user_input, current_model, console)
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue

            # Check for settings command
            if lowered_input in {"settings", "/settings"}:
                settings = handle_settings(console)
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue

            # Quick reasoning toggle command
            if lowered_input in {"/r", "/reason", "/reasoning"} or lowered_input.startswith("/r "):
                target_state = None
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    target_state = parts[1].strip().lower()
                settings = toggle_reasoning(settings, console, target_state)
                print("\033[90m" + "─" * 60 + "\033[0m\n")
                continue

            # Check for clear command
            if lowered_input in ["clear"]:
                print("\033[92m🧹 Conversation history cleared. Starting fresh!\033[0m")
                messages = [system_message]
                print("\033[90m" + "─" * 60 + "\033[0m\n")
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