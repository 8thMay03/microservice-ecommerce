import torch
from torch import nn


class RNNBehaviorClassifier(nn.Module):
    def __init__(
        self,
        num_products: int,
        num_actions: int,
        product_embedding_dim: int = 32,
        action_embedding_dim: int = 8,
        hidden_size: int = 64,
        num_layers: int = 1,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.product_embedding = nn.Embedding(num_products, product_embedding_dim, padding_idx=0)
        self.action_embedding = nn.Embedding(num_actions, action_embedding_dim, padding_idx=0)
        recurrent_input_size = product_embedding_dim + action_embedding_dim
        recurrent_dropout = dropout if num_layers > 1 else 0.0

        self.rnn = nn.RNN(
            input_size=recurrent_input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=recurrent_dropout,
        )
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_actions - 1),
        )

    def forward(self, product_ids: torch.Tensor, action_ids: torch.Tensor) -> torch.Tensor:
        product_vectors = self.product_embedding(product_ids)
        action_vectors = self.action_embedding(action_ids)
        sequence_vectors = torch.cat([product_vectors, action_vectors], dim=-1)
        _, hidden = self.rnn(sequence_vectors)
        final_state = hidden[-1]
        return self.classifier(final_state)
