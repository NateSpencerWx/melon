# Melon
Do (almost) anything on your computer with AI

Melon is a CLI tool that uses xAI's Grok 4 Fast Reasoning model to interpret your requests and execute terminal commands on your behalf, with built-in safety reviews.

## Installation

Click here, and our AI asssistant will walk you through installation! It should take less then 5 minutes: https://www.perplexity.ai/spaces/install-bot-KsasUoP0QS6ZBZVh2mFw4A#0

On first run, it will prompt for your xAI API key if not found in `.env`. Melon will tell you how to get this.

## Usage

Run Melon and type what you want to do, e.g., "list files in current directory", "create a new folder called test", etc.

Melon will suggest a command, review it for safety, and execute it if verified safe or after confirmation if it thinks you may want to review it yourself first.

Melon maintains conversation history across multiple interactions, allowing for contextual follow-up requests. To clear the conversation history and start fresh, type `/clear` or `clear`.
To be clear, when you stop Melon, the conversation history is lost (for now)
