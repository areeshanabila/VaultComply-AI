from services.ollama_client import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL, status


def main() -> int:
    s = status(refresh=True)
    print("VaultComply AI — Ollama check")
    print(f"Endpoint: {OLLAMA_BASE_URL}")
    if not s.online:
        print(f"OFFLINE: {s.message}")
        return 1
    print("Ollama: online")
    print(f"Chat model ({CHAT_MODEL}): {'READY' if s.chat_model_ready else 'MISSING'}")
    print(f"Embedding model ({EMBED_MODEL}): {'READY' if s.embed_model_ready else 'MISSING'}")
    if s.models:
        print("Installed models:")
        for model in s.models:
            print(f"  - {model}")
    if not s.chat_model_ready:
        print(f"Run: ollama pull {CHAT_MODEL}")
    if not s.embed_model_ready:
        print(f"Run: ollama pull {EMBED_MODEL}")
    return 0 if s.chat_model_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
