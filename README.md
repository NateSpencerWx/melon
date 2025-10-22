# 🍉 Melon
Do (almost) anything on your computer with AI

Melon is a tool that lets you control your computer using plain English. Just tell it what you want to do, and it will figure out the technical details for you! It uses xAI's Grok AI to understand your requests and execute them safely.

## 📋 What You'll Need

Before you start, make sure you have:

1. **Python 3.7 or newer** installed on your computer
   - To check if you have Python: Open your terminal and type `python --version` or `python3 --version`
   - Don't have Python? Download it from [python.org](https://www.python.org/downloads/)

2. **An xAI API key** (free to create)
   - Sign up at: https://accounts.x.ai/sign-up?redirect=cloud-console
   - Get your API key from: https://console.x.ai/team/default/api-keys
   - Don't worry - Melon will help you set this up on first run!

3. **A terminal/command line** (already on your computer)
   - **Windows:** Search for "Command Prompt" or "PowerShell" in the Start menu
   - **Mac:** Search for "Terminal" in Spotlight (press Cmd+Space)
   - **Linux:** Search for "Terminal" in your applications menu

## 🚀 Installation

### Step 1: Download Melon

**Option A: Download as ZIP (Easiest)**
1. Go to https://github.com/NateSpencerWx/melon
2. Click the green "Code" button
3. Click "Download ZIP"
4. Extract the ZIP file to a folder you can find easily (like your Desktop or Documents)

**Option B: Use Git (If you have it)**
1. Open your terminal
2. Navigate to where you want to install Melon (e.g., `cd Desktop`)
3. Run: `git clone https://github.com/NateSpencerWx/melon.git`

### Step 2: Navigate to the Melon Folder

Open your terminal and navigate to where you extracted/cloned Melon:

```bash
# If you put it on your Desktop:
cd Desktop/melon

# If you put it in your Documents:
cd Documents/melon

# If you're not sure where it is, use the full path:
# Windows example: cd C:\Users\YourName\Desktop\melon
# Mac/Linux example: cd /Users/YourName/Desktop/melon
```

**Tip:** You can often drag the folder into the terminal window to automatically type its path!

### Step 3: Install Required Components

In the terminal (while in the melon folder), run:

**On Windows:**
```bash
pip install -r requirements.txt
```

**On Mac/Linux:**
```bash
pip3 install -r requirements.txt
```

This installs the Python packages Melon needs to work. It might take a minute or two.

### Step 4: Run Melon!

**On Windows:**
```bash
python melon.py
```

**On Mac/Linux:**
```bash
python3 melon.py
```

🎉 **That's it!** On your first run, Melon will ask for your xAI API key. Just paste it in when prompted, and you're ready to go!

## 💡 How to Use Melon

Once Melon is running, you'll see a watermelon emoji (🍉) prompt. Just type what you want to do in plain English!

### Example Requests:
- "list all files in this folder"
- "create a new folder called my-project"
- "show me the current date and time"
- "find all text files in this directory"
- "tell me how much disk space is available"

### Special Commands:
- Type `/clear` or `clear` to start a fresh conversation
- Press `Ctrl+C` to exit Melon

### How It Works:
1. You type your request in natural language
2. Melon figures out what terminal command(s) to run
3. **Safety first:** Commands that only read information run automatically
4. **Permission required:** Commands that could change your system (like creating or deleting files) will ask for your approval first
5. Melon shows you the result and you can make follow-up requests!

## 🔧 Troubleshooting

### "Python is not recognized" or "command not found: python"

**Problem:** Python isn't installed or not added to your system PATH.

**Solution:**
- Install Python from [python.org](https://www.python.org/downloads/)
- During installation, **check the box that says "Add Python to PATH"**
- After installing, restart your terminal and try again

### "pip is not recognized" or "command not found: pip"

**Problem:** pip (Python's package installer) isn't available.

**Solution:**
- Try using `pip3` instead of `pip`
- If that doesn't work, try: `python -m pip install -r requirements.txt`
- Or: `python3 -m pip install -r requirements.txt`

### "Permission denied" when running commands

**Solution (Mac/Linux):**
- You might need to make the file executable first: `chmod +x melon.py`
- Then run: `./melon.py`

### Can't find the melon folder in terminal

**Solution:**
1. In your file explorer, navigate to the melon folder
2. Look at the address bar to see the full path
3. In terminal, type `cd ` (with a space after cd)
4. Drag the melon folder into the terminal window - this will paste the path
5. Press Enter

### API Key Issues

**Problem:** "Invalid API key" error

**Solution:**
- Make sure you copied the entire API key (they're long!)
- Check for extra spaces at the beginning or end
- Create a new API key at https://console.x.ai/team/default/api-keys

### Other Issues?

If you run into other problems:
1. Check that you're in the melon folder when running commands (`ls` or `dir` should show melon.py)
2. Make sure Python 3.7+ is installed (`python --version`)
3. Try closing and reopening your terminal
4. Check the [GitHub Issues](https://github.com/NateSpencerWx/melon/issues) page to see if others have had similar problems

## 🆘 Terminal Basics (Quick Reference)

If you're new to using the terminal, here are some helpful commands:

| Command | What it does | Example |
|---------|-------------|---------|
| `cd [folder]` | Change directory (move to a folder) | `cd Desktop` |
| `cd ..` | Go up one folder | `cd ..` |
| `ls` (Mac/Linux) or `dir` (Windows) | List files in current folder | `ls` |
| `pwd` (Mac/Linux) | Show current folder path | `pwd` |
| `cd` (Windows) | Show current folder path | `cd` |

**Remember:** You need to be in the melon folder to run Melon!

## 🔐 Privacy & Safety

- All commands that could modify your system require your approval first
- You can see exactly what command will run before it executes
- You can edit commands before they run if needed
- Your API key is stored locally in a `.env` file (never share this file!)
