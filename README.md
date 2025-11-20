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

### Mentioning Files

You can mention files in your requests using the `@` symbol followed by a file path. Melon will automatically read the file contents and include them in the context sent to the AI.

**Autocomplete:** When you type `@` followed by a path, press **Tab** to see file suggestions. The autocomplete shows available files and directories with their sizes, making it easy to find and reference files.

Examples:
- `"Can you explain what @/path/to/script.py does?"`
- `"Review @./config.json and suggest improvements"`
- `"Compare @file1.txt and @file2.txt"`

Supported path formats:
- Absolute paths: `@/absolute/path/to/file.txt`
- Relative paths: `@./relative/path/file.py` or `@../parent/file.js`
- Home directory: `@~/Documents/report.md`
- Paths with spaces: `@"path/to/file with spaces.txt"` or `@'another file.py'`

Notes:
- File size is limited to 1MB to avoid overwhelming the AI context
- Binary files and directories are automatically excluded with error messages
- Multiple files can be mentioned in a single request
- Use Tab for autocomplete when typing file paths after `@`
