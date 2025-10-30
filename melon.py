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

def is_command_modifying(command: str, client) -> tuple[bool, str]:
    """
    Use AI to determine if a command modifies the system and get a description.
    Returns (is_modifying, description)
    """
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
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
            ]
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

    print("\033[96m💡 Type your request in natural language. Type '/clear' to reset conversation history, and ^C to leave.\033[0m")
    print("\033[90m" + "─" * 60 + "\033[0m\n")
    while True:
        try:
            user_input = input("\033[95m🍉 \033[0m").strip()
            if not user_input:
                continue

            # Check for clear command
            if user_input.lower() in ["/clear", "clear", "clear history", "reset"]:
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
                    response = client.chat.completions.create(
                        model="openai/gpt-4o",
                        messages=messages,
                        tools=[tool_definition]
                    )
                    
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