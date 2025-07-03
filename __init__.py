# __init__.py

from .hf_batch_uploader import HuggingFaceSimpleUploader

NODE_CLASS_MAPPINGS = {
    "HuggingFaceSimpleUploader": HuggingFaceSimpleUploader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HuggingFaceSimpleUploader": "LovenHugging - - - - HuggingFace Batch Uploader"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("✅ Custom Node: HuggingFace Batch Uploader loaded.")
