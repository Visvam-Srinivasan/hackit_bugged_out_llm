# Setup Instructions

This guide explains how to set up and run the project on both Windows and Linux systems.

------------------------------------------------------------
1. Install Ollama
------------------------------------------------------------

WINDOWS:

1. Download Ollama from:
   https://ollama.com/download

2. Run the installer.

3. Open Command Prompt and verify:
   ollama --version


LINUX (Ubuntu/Debian):

curl -fsSL https://ollama.com/install.sh | sh

Verify installation:
ollama --version


------------------------------------------------------------
2. Download Model
------------------------------------------------------------

Recommended model:
ollama pull mistral

If system RAM is low:
ollama pull tinyllama

Test model:
ollama run mistral

Type:
Hello

Exit:
 /bye


------------------------------------------------------------
3. Clone Repository
------------------------------------------------------------

git clone <your-repo-url>
cd hackit_bugged_out_llm


------------------------------------------------------------
4. Create Virtual Environment
------------------------------------------------------------

WINDOWS (Command Prompt or PowerShell):

python -m venv venv
venv\Scripts\activate


LINUX:

python3 -m venv venv
source venv/bin/activate


If venv fails on Ubuntu/Debian:

sudo apt install python3-venv


------------------------------------------------------------
5. Install Dependencies
------------------------------------------------------------

pip install --upgrade pip
pip install -r requirements.txt


------------------------------------------------------------
6. Run Application
------------------------------------------------------------

Make sure Ollama is running.

Then start the app:

streamlit run app.py

Open browser at:
http://localhost:8501


