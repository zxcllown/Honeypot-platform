import csv
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from models import RequestDataset, RequestClassifier


def load_http_params(path):
    payloads = []
    labels = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                payload = row[0].strip()
                label = row[2].strip()
                if payload and label:
                    payloads.append(payload)
                    labels.append(label)
    return payloads, labels


def train():
    # Загрузка
    payloads, labels = load_http_params('../Data/payload_combined.csv')

    # Энкодер
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    encoder = SentenceTransformer('../Http-encoder', device=device)

    # Датасет
    le = LabelEncoder()
    le.fit(labels)
    dataset = RequestDataset(payloads, labels, encoder, le, device=device)

    train_data, test_data = train_test_split(dataset, test_size=0.2, random_state=42)
    train_loader = DataLoader(train_data, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=16)

    # Модель
    model = RequestClassifier(emb_dim=384, num_types=len(le.classes_)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    loss_binary = nn.BCELoss()
    loss_multi = nn.CrossEntropyLoss()

    # Обучение
    epochs = 10
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for emb, b_label, m_labels in train_loader:
            emb, b_label, m_labels = emb.to(device), b_label.to(device).float(), m_labels.to(device)
            optimizer.zero_grad()
            out_bin, out_label = model(emb)
            loss = loss_binary(out_bin, b_label) + loss_multi(out_label, m_labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for emb, b_label, _ in test_loader:
                emb, b_label = emb.to(device), b_label.to(device).float()
                out_bin, _ = model(emb)
                pred = (out_bin > 0.5).float()
                correct += (pred == b_label).sum().item()
                total += b_label.size(0)

        print(f"Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(train_loader):.4f} | Acc: {correct/total:.2%}")

    # Сохранение
    torch.save({
        'model_state_dict': model.state_dict(),
        'classes': le.classes_.tolist(),
    }, '../http-classifier.pt')
    print("Классификатор сохранён: http-classifier.pt")


if __name__ == '__main__':
    train()