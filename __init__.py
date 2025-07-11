# __init__.py

from .hf_batch_uploader import HuggingFaceBatchUploader

# Dicionários de mapeamento para ComfyUI
NODE_CLASS_MAPPINGS = {
    "HuggingFaceBatchUploader": HuggingFaceBatchUploader
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "HuggingFaceBatchUploader": "lovenico HuggingFace Batch Uploader (Simple)"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("✅ Custom Node: HuggingFace Batch Uploader loaded.")
