import torch
from sentence_transformers import SentenceTransformer
from ml_observer.classifier.ssh.models import SessionClassifier

_model = None
_encoder = None
_checkpoint = None
_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Абсолютный путь к ml-models относительно backend/workers/
import os
ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ml-models', 'ml_observer')

def load_model():
    global _model, _encoder, _checkpoint, _device
    if _model is not None:
        return _model, _encoder, _checkpoint

    encoder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'encoder', 'command-encoder')
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'classifier', 'ssh', 'session-classifier.pt')

    _encoder = SentenceTransformer(encoder_path, device=_device)
    _checkpoint = torch.load(model_path, map_location=_device)

    _model = SessionClassifier(
        emb_dim=384,
        num_types=3,
        num_tactics=len(_checkpoint['all_tactics'])
    ).to(_device)
    _model.load_state_dict(_checkpoint['model_state_dict'])
    _model.eval()

    return _model, _encoder, _checkpoint


def predict_session(commands, max_len=50, threshold=0.5):
    model, encoder, checkpoint = load_model()
    all_tactics = checkpoint['all_tactics']
    type_to_idx = checkpoint['type_to_idx']
    idx_to_type = {v: k for k, v in type_to_idx.items()}

    if len(commands) > max_len:
        commands = commands[:max_len]

    if commands:
        emb = encoder.encode(commands, convert_to_tensor=True, device=_device)
        if emb.shape[0] < max_len:
            pad = torch.zeros(max_len - emb.shape[0], emb.shape[1], device=_device)
            emb = torch.cat([emb, pad])
    else:
        emb = torch.zeros(max_len, 384, device=_device)

    emb = emb.unsqueeze(0)

    with torch.no_grad():
        out_type, out_tactics = model(emb)

    type_idx = out_type.argmax(1).item()
    session_type = idx_to_type[type_idx]

    probs = out_tactics[0].tolist()
    tactics = [all_tactics[i] for i, p in enumerate(probs) if p > threshold]

    return {
        'type': session_type,
        'attack_types': tactics,
        'confidence': round(max(probs), 3) if probs else 0.0,
        'probabilities': {all_tactics[i]: round(p, 3) for i, p in enumerate(probs)}
    }