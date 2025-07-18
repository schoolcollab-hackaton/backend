#!/usr/bin/env python3
"""
Script to download and cache HuggingFace models for the student matching system
"""

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

def download_models():
    """Download and cache models locally"""
    models_dir = os.path.join(os.path.dirname(__file__), 'ai_models')
    os.makedirs(models_dir, exist_ok=True)
    
    print("Downloading sentence transformer model...")
    # Download sentence transformer for semantic similarity
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    sentence_model.save(os.path.join(models_dir, 'sentence-transformer'))
    print("✓ Sentence transformer downloaded")
    
    print("Downloading multilingual sentence transformer for French...")
    # Download multilingual model for chatbot (supports French)
    multilingual_model = SentenceTransformer('all-mpnet-base-v2')
    multilingual_model.save(os.path.join(models_dir, 'multilingual-chatbot'))
    print("✓ Multilingual model downloaded")
    
    print("Downloading toxicity detection model...")
    # Download toxicity detection model
    tokenizer = AutoTokenizer.from_pretrained("unitary/toxic-bert")
    model = AutoModelForSequenceClassification.from_pretrained("unitary/toxic-bert")
    
    tokenizer.save_pretrained(os.path.join(models_dir, 'toxic-bert'))
    model.save_pretrained(os.path.join(models_dir, 'toxic-bert'))
    print("✓ Toxicity detection model downloaded")
    
    print("Skipping French sentiment model (not required for chatbot)")
    
    print("All models downloaded successfully!")
    print(f"Models saved in: {models_dir}")

if __name__ == "__main__":
    download_models()