# Melon
Do (almost) anything on your computer with AI

Melon is a CLI tool that uses xAI's Grok model to interpret your requests and execute terminal commands on your behalf, with built-in safety reviews.

## Installation

1. Clone this repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python melon.py` or `./melon.py` (after making executable)

On first run, it will prompt for your xAI API key if not found in `.env`.

Get your API key from: https://console.x.ai/team/default/api-keys

## Usage

Run the script and type what you want to do, e.g., "list files in current directory", "create a new folder called test", etc.

Melon will suggest a command, review it for safety, and execute it if verified safe or after confirmation if it thinks you may want to review it yourself first.

Melon maintains conversation history across multiple interactions, allowing for contextual follow-up requests. To clear the conversation history and start fresh, type `/clear` or `clear`.
