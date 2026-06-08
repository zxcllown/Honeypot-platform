import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split

from models import SessionDataset, SessionClassifier


def train():
    # Загрузка
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")

    encoder = SentenceTransformer('../command-encoder', device=device)

    with open('../Logs/sessions.json', 'r', encoding='utf-8') as f:
        sessions = json.load(f)

    print(f"Сессий всего: {len(sessions)}")

    # Метки
    type_to_idx = {'benign': 0, 'malicious': 1, 'mixed': 2}

    all_tactics = sorted(set(t for s in sessions for t in s.get('tactics', [])))
    mlb = MultiLabelBinarizer()
    mlb.fit([all_tactics])

    print(f"Типы: {type_to_idx}")
    print(f"Тактик: {len(all_tactics)}")

    # Датасет
    dataset = SessionDataset(sessions, encoder, type_to_idx, mlb, device=device)
    train_data, test_data = train_test_split(dataset, test_size=0.2, random_state=42)
    train_loader = DataLoader(train_data, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=16)

    # Модель
    model = SessionClassifier(emb_dim=384, num_types=3, num_tactics=len(all_tactics)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    loss_type = nn.CrossEntropyLoss()
    loss_tactics = nn.BCELoss()

    # Обучение
    epochs = 10
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for emb, t_label, t_hot in train_loader:
            emb, t_label, t_hot = emb.to(device), t_label.to(device), t_hot.to(device)
            optimizer.zero_grad()
            out_type, out_tactics = model(emb)
            loss = loss_type(out_type, t_label) + loss_tactics(out_tactics, t_hot)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        model.eval()
        correct, total = 0, 0
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
        'all_tactics': all_tactics,
        'type_to_idx': type_to_idx,
    }, '../session-classifier.pt')

    print("Модель сохранена: session-classifier.pt")


if __name__ == '__main__':
    train()