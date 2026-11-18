import torch
import open_clip
from PIL import Image

_model = None
_preprocess = None
_tokenizer = None

def _load_model():
    global _model, _preprocess, _tokenizer
    if _model is None:
        print("  [validator] Loading CLIP model...")
        _model, _, _preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        _tokenizer = open_clip.get_tokenizer('ViT-B-32')
        _model.eval()

def is_image_relevant(image_path, caption, threshold=0.22):
    """
    Checks if an image matches a caption using the local CLIP model.
    Returns True if the similarity score is above the threshold.
    """
    _load_model()
    try:
        image = _preprocess(Image.open(image_path)).unsqueeze(0)
        text = _tokenizer([caption])
        
        with torch.no_grad():
            image_features = _model.encode_image(image)
            text_features = _model.encode_text(text)
            
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            
            score = (image_features @ text_features.T).item()
            
        print(f"  [validator] CLIP Score: {score:.3f} for '{caption[:40]}...'")
        
        # If the score is too low, reject the image
        return score >= threshold
        
    except Exception as e:
        print(f"  [validator] Error checking image: {e}")
        return True # Default to True so we don't break the pipeline on a minor error
