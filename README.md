# 🃏 Discord Advanced Poker Engine

A fully asynchronous, real-time poker bot built in Python. Features a complete state machine for multi-round gameplay, dynamic side-pot calculations, and an interactive Discord UI.

## 🚀 Features
* **Multi-Mode Support:** Texas Hold'em, Omaha, and custom mature variants.
* **Asynchronous Game Loop:** Handles turn-based mechanics and automated folding.
* **Advanced Mathematics:** Hand-evaluator algorithm and all-in split pot management.
* **Visual Engine:** Dynamic ASCII card generation and emoji-based UI representations.
* **Persistent Memory:** SQLite database integration to save player bankrolls.

## 🛠️ Installation
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file and add your bot token: `DISCORD_TOKEN=your_token_here`
4. Run the engine: `python main.py`