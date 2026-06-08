import os
import torch
from sentence_transformers import SentenceTransformer
from ml_observer.classifier.http.models import HTTPSessionClassifier

_model = None
_encoder = None
_checkpoint = None
_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ml-models', 'ml_observer')

def load_model():
    global _model, _encoder, _checkpoint, _device
    if _model is not None:
        return _model, _encoder, _checkpoint

    encoder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'encoder', 'http-encoder')
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'classifier', 'http', 'http-session-classifier.pt')

    _encoder = SentenceTransformer(encoder_path, device=_device)
    _checkpoint = torch.load(model_path, map_location=_device)
    _model = HTTPSessionClassifier(
        emb_dim=384,
        num_types=3,
        num_attacks=len(_checkpoint['all_attack_types'])
    ).to(_device)
    _model.load_state_dict(_checkpoint['model_state_dict'])
    _model.eval()

    return _model, _encoder, _checkpoint


def predict_http_session(requests, max_len=50, threshold=0.5):
    model, encoder, checkpoint = load_model()

    payloads = [r.get('raw_payload', r.get('payload', '')) for r in requests[:max_len]]
    all_attack_types = checkpoint['all_attack_types']
    type_to_idx = checkpoint['type_to_idx']
    idx_to_type = {v: k for k, v in type_to_idx.items()}

    if payloads:
        emb = encoder.encode(payloads, convert_to_tensor=True, device=_device)
        if emb.shape[0] < max_len:
            pad = torch.zeros(max_len - emb.shape[0], emb.shape[1], device=_device)
            emb = torch.cat([emb, pad])
    else:
        emb = torch.zeros(max_len, 384, device=_device)

    emb = emb.unsqueeze(0)

    with torch.no_grad():
        out_type, out_attack = model(emb)

    type_idx = out_type.argmax(1).item()
    session_type = idx_to_type[type_idx]

    probs = out_attack[0].cpu().tolist()
    attacks = [all_attack_types[i] for i, p in enumerate(probs) if p > threshold]
    max_conf = max(probs) if probs else 0.0

    return {
        'type': session_type,
        'attack_types': attacks,
        'confidence': round(max_conf, 3),
        'probabilities': {all_attack_types[i]: round(p, 3) for i, p in enumerate(probs)}
    }