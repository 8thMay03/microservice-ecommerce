# Behavior Prediction

Thu muc nay train 3 mo hinh recurrent de du doan hanh vi tiep theo cua user:

- RNN: `rnn_model.py`
- LSTM: `lstm_model.py`
- BiLSTM: `bilstm_model.py`

File `train_behavior_models.py` dung de tien xu ly du lieu, train, danh gia, chon `model_best`
va xuat visualization.

Neu muon train tung mo hinh rieng:

```powershell
python behavior_prediction/train_rnn.py
python behavior_prediction/train_lstm.py
python behavior_prediction/train_bilstm.py
```

Du lieu mac dinh: `../behavior-data/data_user500.csv`

## Cach chay

```powershell
pip install -r behavior_prediction/requirements.txt
python behavior_prediction/train_behavior_models.py
```

Co the chinh nhanh so epoch hoac do dai chuoi:

```powershell
python behavior_prediction/train_behavior_models.py --epochs 50 --sequence-length 5
```

## Dau ra

Tat ca ket qua nam trong `behavior_prediction/outputs`:

- `model_best.pt`: checkpoint cua mo hinh tot nhat dua tren macro F1 tap test.
- `metrics.json`: accuracy, precision, recall, macro F1, weighted F1 va classification report.
- `model_selection_note.txt`: danh gia bang loi va ly do chon model tot nhat.
- `training_f1.png`: qua trinh train/validation macro F1.
- `training_loss.png`: qua trinh train/validation loss.
- `rnn_loss.png`, `lstm_loss.png`, `bilstm_loss.png`: train_loss va val_loss rieng cua tung model.
- `model_comparison.png`: so sanh cac metric cua 3 mo hinh.
- `best_confusion_matrix.png`: confusion matrix cua model tot nhat.
- `rnn_confusion_matrix.png`, `lstm_confusion_matrix.png`, `bilstm_confusion_matrix.png`: confusion matrix rieng cua tung model.

## Cach danh gia

Tap du lieu co phan bo action lech (`view` nhieu hon `purchase`), vi vay script uu tien `macro F1`
khi chon `model_best`. Metric nay danh gia can bang hon giua cac lop, khong de lop nhieu mau lan at
ket qua nhu accuracy.
