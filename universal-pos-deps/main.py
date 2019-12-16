from typing import Sequence, Iterable, Set, List

import torch
import torch.nn as nn

from neural.types import TT

from data import Word, POS, Sent
import data
from word_embedding import WordEmbedder, AtomicEmbedder


# TODO: Implement this class
class PosTagger(nn.Module):
    """Simple POS tagger based on LSTM.

    * Each input word is embedded separately as an atomic object
    * LSTM is run over the word vector representations
    * The output "hidden" representations are used to predict the POS tags
    * Simple linear layer is used for scoring
    """

    # TODO EX6: adapt this method to use LSTM
    def __init__(self, word_emb: WordEmbedder, tagset: Set[POS]):
        super(PosTagger, self).__init__()
        # Keep the word embedder, so that it get registered
        # as a sub-module of the POS tagger.
        self.word_emb = word_emb
        # Keep the tagset
        self.tagset = tagset
        # We use the linear layer to score the embedding vectors
        # TODO EX6: account for LSTM
        self.linear_layer = nn.Linear(
            self.word_emb.embedding_size(),
            len(tagset)
        )
        # To normalize the output of the linear layer
        # (do we need it? we will see)
        self.normalizer = nn.Sigmoid()
        # TODO EX6: add LSTM submodule
        pass

    # TODO EX6: adapt this method to use LSTM
    def forward(self, sent: Sequence[Word]) -> TT:
        """Calculate the score vectors for the individual words."""
        # Embed all the words and create the embedding matrix
        embs = self.word_emb.forwards(sent)
        # The first dimension should match the number of words
        assert embs.shape[0] == len(sent)
        # The second dimension should match the embedding size
        # TODO EX6: account for LSTM
        assert embs.shape[1] == self.word_emb.embedding_size()
        # TODO EX6: apply LSTM to word embeddings
        pass
        # Calculate the matrix with the scores
        scores = self.linear_layer(embs)
        # The first dimension should match the number of words
        assert scores.shape[0] == len(sent)
        # The second dimension should match the size of the tagset
        assert scores.shape[1] == len(self.tagset)
        # TODO: do we need do apply some normalizer (sigmoid, softmax?)
        # Finally, return the scores
        return scores

    # DONE (modulo testing): implement this method
    def tag(self, sent: Sequence[Word]) -> Sequence[POS]:
        """Predict the POS tags in the given sentence."""
        # TODO: does it make sense to use `tag` as part of training?
        with torch.no_grad():
            # POS tagging is to be carried out based on the resulting scores
            scores = self.forward(sent)
            # Create a list for predicted POS tags
            predictions = []
            # For each word, we must select the POS tag corresponding to the
            # index with the highest score
            for score_vect in scores:
                # Determine the position with the highest score
                _, ix = torch.max(score_vect, 0)
                # Make sure `ix` is a 0d tensor
                assert ix.dim() == 0
                ix = ix.item()
                # Assert the index is within the range of POS tag indices
                assert 0 <= ix < len(self.tagset)
                # Determine the corresponding POS tag
                pos = list(self.tagset)[ix]
                # Append the new prediction
                predictions.append(pos)
            # We should have as many predicted POS tags as input words
            assert len(sent) == len(predictions)
            # Return the predicted POS tags
            return predictions


def accuracy(tagger: PosTagger, data_set: Iterable[Sent]) -> float:
    """Calculate the accuracy of the model on the given dataset.

    The accuracy is defined as the percentage of the words in the data_set
    for which the model predicts the correct POS tag.
    """
    k, n = 0., 0.
    for sent in data_set:
        # Split the sentence into input words and POS tags
        words, gold_poss = zip(*sent)
        # Predict the POS tags using the model
        pred_poss = tagger.tag(words)
        for (pred_pos, gold_pos) in zip(pred_poss, gold_poss):
            if pred_pos == gold_pos:
                k += 1.
            n += 1.
    return k / n


# TODO: implement this function
def total_loss(tagger: PosTagger, data_set: Iterable[Sent]) -> TT:
    """Calculate the total total, cross entropy loss over the given dataset."""
    # Create two lists for target indices (corresponding to POS tags we
    # want our mode to predict) and the actually predicted scores.
    target_ixs = []     # type: List[int]
    pred_scores = []    # type: List[TT]
    # Loop over the dataset in order to determine the target POS tags
    # and the predictions
    for sent in data_set:
        # Unzip the sentence into a (list of words, list of target POS tags)
        (words, gold_tags) = zip(*sent)
        # TODO: Determine the target POS tag indices and update `target_ixs`
        # TODO: Determine the predicted scores and update `pred_scores`
    # TODO: Convert the target indices and the predictions to tensors
    pass
    # Make sure the dimensions match
    assert target_ixs.shape[0] == pred_scores.shape[0]
    # TODO: assert that target_ixs is a vector (1d tensor)
    # TODO: In particular, the second dimension of the predicted scores
    # should correspond to the size of the tagset, i.e.?
    assert pred_scores.shape[1] == None
    # TODO: Calculate the loss and return it
    pass


# Training dataset
train_set = data.MemPosDataSet("UD_English-ParTUT/en_partut-ud-train.conllu")

# Development dataset
dev_set = data.MemPosDataSet("UD_English-ParTUT/en_partut-ud-dev.conllu")

# Size stats
print("Train size:", len(list(train_set)))
print("Dev size:", len(list(dev_set)))

# Determine the set of words in the dataset
word_set = set(
    word
    for sent in train_set
    for (word, _pos) in sent
)

# Number of words
print("Number of words:", len(word_set))

# Determine the POS tagset
tagset = set(
    pos
    for sent in train_set
    for (_word, pos) in sent
)

# Tagset
print("Tagset:", tagset)

# Create the word embedding module
word_emb = AtomicEmbedder(word_set, 10)

# Create the tagger
tagger = PosTagger(word_emb, tagset)

# TODO: train the model (see `train` in `neural/training`)
