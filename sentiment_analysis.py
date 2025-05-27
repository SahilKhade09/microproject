import json
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import os

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('wordnet')

# Load sentiment word database
current_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(current_dir, 'sentiment_data', 'sentiment_dict.json')

with open(json_path, 'r') as f:
    sentiment_data = json.load(f)

# ✅ Ensure they are dictionaries
positive_words = sentiment_data.get('positive', {})
negative_words = sentiment_data.get('negative', {})

# Safety check
if not isinstance(positive_words, dict) or not isinstance(negative_words, dict):
    raise ValueError("positive and negative word lists must be dictionaries!")

lemmatizer = WordNetLemmatizer()

def get_sentiment_score(review):
    tokens = word_tokenize(review.lower())
    lemmatized_tokens = [lemmatizer.lemmatize(token) for token in tokens]

    score = 0
    for token in lemmatized_tokens:
        if token in positive_words:
            score += positive_words[token]
        elif token in negative_words:
            score += negative_words[token]

    return score

def get_star_rating(reviews):
    # 🔒 Handle both single string and list input
    if isinstance(reviews, str):
        reviews = [reviews]

    if not reviews:
        return 0.0

    total_score = sum(get_sentiment_score(review) for review in reviews)
    avg_score = total_score / len(reviews)

    # Normalize to 1-5 stars
    if avg_score <= -3:
        return 1
    elif -3 < avg_score <= -1:
        return 2
    elif -1 < avg_score <= 1:
        return 3
    elif 1 < avg_score <= 3:
        return 4
    else:
        return 5
