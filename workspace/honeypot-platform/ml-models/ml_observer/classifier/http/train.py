import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from models import HTTPSessionClassifier, HTTPSessionDataset

def train():
    # Загрузка
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    encoder = SentenceTransformer('../Http-encoder', device=device)

    with open('../Logs/http_sessions.json', 'r', encoding='utf-8') as f:
        sessions = json.load(f)

    print(f"HTTP-сессий всего: {len(sessions)}")

    # Метки
    type_to_idx = {'benign': 0, 'malicious': 1, 'mixed': 2}
    idx_to_type = {v: k for k, v in type_to_idx.items()}

    all_attack_types = sorted(set(t for s in sessions for t in s.get('attack_types', [])))
    mlb = MultiLabelBinarizer()
    mlb.fit([all_attack_types])

    print(f"Типы сессий: {type_to_idx}")
    print(f"Типов атак: {len(all_attack_types)} — {all_attack_types}")

    # Подготовка
    dataset = HTTPSessionDataset(sessions, encoder, type_to_idx, mlb, device='cuda')
    print('Dataset loaded')
    train_data, test_data = train_test_split(dataset, test_size=0.2, random_state=42)
    print('Dataset is divided')
    train_loader = DataLoader(train_data, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=16)
    print('Test and train loader is done')

    model = HTTPSessionClassifier(
        emb_dim=384,
        num_types=3,
        num_attacks=len(all_attack_types)
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    loss_type = nn.CrossEntropyLoss()
    loss_attack = nn.BCELoss()

    # Обучение
    epochs = 10
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for emb, t_label, a_hot in train_loader:
            emb, t_label, a_hot = emb.to(device), t_label.to(device), a_hot.to(device)
            optimizer.zero_grad()
            out_type, out_attack = model(emb)
            loss = loss_type(out_type, t_label) + loss_attack(out_attack, a_hot)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for emb, t_label, _ in test_loader:
                emb, t_label = emb.to(device), t_label.to(device)
                out_type, _ = model(emb)
                correct += (out_type.argmax(1) == t_label).sum().item()
                total += t_label.size(0)

        print(f"Epoch {epoch + 1}/{epochs} | Loss: {total_loss / len(train_loader):.4f} | Acc: {correct / total:.2%}")

    # Сохранение
    torch.save({
        'model_state_dict': model.state_dict(),
        'all_attack_types': all_attack_types,
        'type_to_idx': type_to_idx,
    }, '../http-session-classifier.pt')

    print("Модель сохранена: http-session-classifier.pt")

if __name__ == '__main__':
    train()