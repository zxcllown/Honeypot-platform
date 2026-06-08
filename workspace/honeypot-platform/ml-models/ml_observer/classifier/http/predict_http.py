import os
import torch
from sentence_transformers import SentenceTransformer
from ml_observer.classifier.http.models import RequestClassifier

_model = None
_encoder = None
_checkpoint = None
_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'ml-models', 'ml_observer')

def load_model():
    global _model, _encoder, _checkpoint, _device
    if _model is not None:
        return _model, _encoder, _checkpoint

    encoder_path = os.path.join(ML_MODELS_DIR, 'encoder', 'http-encoder')
    model_path = os.path.join(ML_MODELS_DIR, 'classifier', 'http', 'http-classifier.pt')

    _encoder = SentenceTransformer(encoder_path, device=_device)
    _checkpoint = torch.load(model_path, map_location=_device)
    _model = RequestClassifier(
        emb_dim=384,
        num_types=len(_checkpoint['classes'])
    ).to(_device)
    _model.load_state_dict(_checkpoint['model_state_dict'])
    _model.eval()

    return _model, _encoder, _checkpoint

def predict(payloads):
    model, encoder, checkpoint = load_model()
    classes = checkpoint['classes']
    results = []

    for payload in payloads:
        emb = encoder.encode(payload, convert_to_tensor=True, device=_device)
        with torch.no_grad():
            out_bin, out_type = model(emb)

        is_attack = out_bin.item() > 0.5
        attack_type = classes[out_type.argmax().item()] if is_attack else 'norm'

        results.append({
            'payload': payload,
            'is_attack': is_attack,
            'type': attack_type,
            'confidence': round(out_bin.item(), 3)
        })

    return results