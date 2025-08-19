import os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Configs
CONFIG_PATH = os.path.join(DATA_DIR, "conversation_config.json")
FLOW_PATH = os.path.join(DATA_DIR, "conversation_flow.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    ACE_CONFIG = json.load(f)

with open(FLOW_PATH, "r", encoding="utf-8") as f:
    FLOW = json.load(f)

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-ac86f23b7a524c8cb0f42b4f62a010b2")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
