# models.py
import torch
import torch.nn as nn
from torch.utils.data import Dataset

class SessionClassifier(nn.Module):
    def __init__(self, emb_dim=384, num_types=3, num_tactics=None):
        super().__init__()
        self.attention = nn.MultiheadAttention(emb_dim, num_heads=4, batch_first=True)
        self.ln = nn.LayerNorm(emb_dim)
        self.head_type = nn.Linear(emb_dim, num_types)
        self.head_tactics = nn.Linear(emb_dim, num_tactics)

    def forward(self, x):
        attn, _ = self.attention(x, x, x)
        x = self.ln(attn + x)
        pooled = x.mean(dim=1)
        return self.head_type(pooled), torch.sigmoid(self.head_tactics(pooled))


class SessionDataset(Dataset):
    def __init__(self, sessions, encoder, type_to_idx, mlb, max_len=50, device='cuda'):
        self.sessions = sessions
        self.max_len = max_len
        self.emb_dim = encoder.get_embedding_dimension()
        self.embeddings = []
        self.type_labels = []
        self.tactic_labels = []

        for s in sessions:
            commands = [c['cmd'] for c in s['commands'][:max_len]]
            if commands:
                emb = encoder.encode(commands, convert_to_tensor=True, device=device)
                if emb.shape[0] < max_len:
                    pad = torch.zeros(max_len - emb.shape[0], self.emb_dim, device=device)
                    emb = torch.cat([emb, pad])
                else:
                    emb = emb[:max_len]
            else:
                emb = torch.zeros(max_len, self.emb_dim, device=device)

            self.embeddings.append(emb.to(device))
            self.type_labels.append(type_to_idx.get(s['type'], 0))
            self.tactic_labels.append(
                torch.tensor(mlb.transform([s.get('tactics', [])])[0], dtype=torch.float)
            )

        self.embeddings = torch.stack(self.embeddings)
        self.type_labels = torch.tensor(self.type_labels)
        self.tactic_labels = torch.stack(self.tactic_labels)

    def __len__(self):
        return len(self.sessions)

    def __getitem__(self, idx):
        return self.embeddings[idx], self.type_labels[idx], self.tactic_labels[idx]