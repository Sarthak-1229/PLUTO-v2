import warnings
import torch

from core.audio_stt import transcribe, load_model as load_stt_model, unload_model as unload_stt_model
from core.brain import LLMReasoner
import core.config


def get_vram_usage_mb() -> float:
    """Return current GPU memory usage in megabytes, or 0 if no GPU is available."""
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / (1024 ** 2)
    return 0.0


def main() -> None:
    # Load the speech‑to‑text model
    stt_model = load_stt_model()
    print(f"Initial VRAM usage: {get_vram_usage_mb():.2f} MB")

    # Perform a dummy transcription to trigger any allocation
    try:
        # Using empty bytes as placeholder audio
        _ = transcribe(stt_model, audio=b"")
    except Exception as exc:
        warnings.warn(f"Dummy transcription failed: {exc}")

    # Unload the STT model to free its memory
    unload_stt_model(stt_model)

    # Instantiate the LLM reasoner
    llm = LLMReasoner()
    print(f"VRAM before prompt: {get_vram_usage_mb():.2f} MB")

    # Run a simple prompt
    response = llm.run("What is the capital of France?")
    print(f"LLM response: {response}")

    print(f"VRAM after prompt: {get_vram_usage_mb():.2f} MB")

    # Verify we stay within the configured budget, if it exists
    budget = getattr(core.config, "VRAM_BUDGET_MB", None)
    total_usage = get_vram_usage_mb()
    if budget is not None and total_usage > budget:
        warnings.warn(
            f"VRAM usage {total_usage:.2f} MB exceeds budget of {budget} MB"
        )
    assert budget is None or total_usage <= budget, "VRAM usage exceeded budget"


if __name__ == "__main__":
    main()
