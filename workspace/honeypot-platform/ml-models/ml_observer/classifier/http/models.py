import torch
import torch.nn as nn
from torch.utils.data import Dataset

class HTTPSessionClassifier(nn.Module):
    def __init__(self, emb_dim=384, num_types=3, num_attacks=None):
        super().__init__()
        self.attention = nn.MultiheadAttention(emb_dim, num_heads=4, batch_first=True)
        self.ln = nn.LayerNorm(emb_dim)
        self.head_type = nn.Linear(emb_dim, num_types)
        self.head_attack = nn.Linear(emb_dim, num_attacks)

    def forward(self, x):
        attn, _ = self.attention(x, x, x)
        x = self.ln(attn + x)
        pooled = x.mean(dim=1)
        return self.head_type(pooled), torch.sigmoid(self.head_attack(pooled))

class HTTPSessionDataset(Dataset):
    def __init__(self, sessions, encoder, type_to_idx, mlb, max_len=50, device='cuda'):
        self.max_len = max_len
        self.emb_dim = encoder.get_embedding_dimension()
        self.embeddings = []
        self.type_labels = []
        self.attack_labels = []

        for s in sessions:
            payloads = [r.get('raw_payload', r.get('payload', '')) for r in s['requests'][:max_len]]

            if payloads:
                emb = encoder.encode(payloads, convert_to_tensor=True, device=device)
                if emb.shape[0] < max_len:
                    pad = torch.zeros(max_len - emb.shape[0], self.emb_dim, device=device)
                    emb = torch.cat([emb, pad])
                else:
                    emb = emb[:max_len]
            else:
                emb = torch.zeros(max_len, self.emb_dim)

            self.embeddings.append(emb.to(device))
            self.type_labels.append(type_to_idx.get(s['type'], 0))
            self.attack_labels.append(
                torch.tensor(mlb.transform([s.get('attack_types', [])])[0], dtype=torch.float)
            )

        self.embeddings = torch.stack(self.embeddings)
        self.type_labels = torch.tensor(self.type_labels)
        self.attack_labels = torch.stack(self.attack_labels)

    def __len__(self):
        return len(self.embeddings)

    def __getitem__(self, idx):
        return self.embeddings[idx], self.type_labels[idx], self.attack_labels[idx]

class RequestClassifier(nn.Module):
    def __init__(self, emb_dim=384, num_types=None):
        super().__init__()
        self.fc1 = nn.Linear(emb_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.head_binary = nn.Linear(64, 1)  # 0=normal, 1=anomalous
        self.head_type = nn.Linear(64, num_types)  # тип атаки (если anomalous)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        return torch.sigmoid(self.head_binary(x)).squeeze(), self.head_type(x)

class RequestDataset(Dataset):
    def __init__(self, payloads, labels, encoder, le, device='cuda'):
        self.embeddings = []
        self.binary_labels = []
        self.multi_labels = []

        for payload_text, label in zip(payloads, labels):
            emb = encoder.encode(payload_text, convert_to_tensor=True, device=device)
            self.embeddings.append(emb.to(device))
            self.binary_labels.append(0 if label == 'norm' else 1)
            self.multi_labels.append(
                torch.tensor(le.transform([label])[0], dtype=torch.long)
            )

        self.embeddings = torch.stack(self.embeddings)
        self.binary_labels = torch.tensor(self.binary_labels)
        self.multi_labels = torch.stack(self.multi_labels)

    def __len__(self):
        return len(self.embeddings)

    def __getitem__(self, idx):
        return self.embeddings[idx], self.binary_labels[idx], self.multi_labels[idx]
