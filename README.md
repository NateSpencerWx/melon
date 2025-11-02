# Melon
Do (almost) anything on your computer with AI

Melon is a CLI tool that uses OpenRouter's AI models to interpret your requests and execute terminal commands on your behalf, with built-in safety reviews.

## Installation

Ask the AI here to help you install Melon on your computer: https://www.perplexity.ai/spaces/melon-install-helper-KsasUoP0QS6ZBZVh2mFw4A#0

On first run, it will prompt for your OpenRouter API key if not found in `.env`.

Get your API key from: https://openrouter.ai/keys

## Usage

Run Melon and type what you want to do, e.g., "list files in current directory", "create a new folder called test", "What is the weather at my location", etc.

Melon will suggest a command, review it for safety, and execute it if verified safe or after confirmation if it thinks you may want to review it yourself first.

Melon maintains conversation history across multiple interactions, allowing for contextual follow-up requests. To clear the conversation history and start fresh, type `/clear` or `clear`.
