"""
services/disease_service.py — Disease matching using BAAI/bge-m3 and FAISS RAG.
Replaces primitive word overlap with vector search.
"""
import os
import json
import faiss
import torch
import warnings

# Suppress PyTorch warnings for clean startup
warnings.filterwarnings("ignore")

_embedder_model = None
_retriever = None

class Embedder:
    def __init__(self, model_name: str, device: str = "cpu"):
        from sentence_transformers import SentenceTransformer
        self.device = "cuda" if torch.cuda.is_available() and device == "cuda" else "cpu"
        print(f"🧠 Loading embedding model '{model_name}' on {self.device}...")
        self.model = SentenceTransformer(model_name, device=self.device)
        
    def embed_text(self, text: str):
        return self.model.encode(text, normalize_embeddings=True)
        
    def embed_batch(self, texts: list[str]):
        return self.model.encode(texts, normalize_embeddings=True)

class Retriever:
    def __init__(self, embedder: Embedder, index_dir: str, kb_path: str):
        self.embedder = embedder
        self.index_dir = index_dir
        self.kb_path = kb_path
        self.indices = {} # crop_name -> faiss_index
        self.metadata = {} # crop_name -> list of doc dicts
        
    def build_indices(self):
        if not os.path.exists(self.kb_path):
            print(f"⚠️ Knowledge base not found at {self.kb_path}")
            return
            
        with open(self.kb_path, 'r', encoding='utf-8') as f:
            docs = json.load(f)
            
        crop_docs = {}
        for doc in docs:
            crop = doc['crop'].lower()
            if crop not in crop_docs:
                crop_docs[crop] = []
            crop_docs[crop].append(doc)
            
        os.makedirs(self.index_dir, exist_ok=True)
        
        for crop, c_docs in crop_docs.items():
            texts_to_embed = []
            for doc in c_docs:
                text = doc.get('symptoms_english', '')
                cause = doc.get('cause_english', '')
                if cause:
                    text += " " + cause
                # Add tamil text to embedding payload for cross-lingual boost
                if doc.get('symptoms_tamil'):
                    text += " " + doc.get('symptoms_tamil')
                texts_to_embed.append(text)
            
            embeddings = self.embedder.embed_batch(texts_to_embed)
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)
            index.add(embeddings)
            
            faiss.write_index(index, os.path.join(self.index_dir, f"{crop}.index"))
            self.indices[crop] = index
            self.metadata[crop] = c_docs
            print(f"✅ Built FAISS index for '{crop}' ({len(c_docs)} docs).")
            
    def load_indices(self):
        if not os.path.exists(self.kb_path):
            return
            
        with open(self.kb_path, 'r', encoding='utf-8') as f:
            docs = json.load(f)
            
        for doc in docs:
            crop = doc['crop'].lower()
            if crop not in self.metadata:
                self.metadata[crop] = []
            self.metadata[crop].append(doc)
            
        for crop in self.metadata.keys():
            index_path = os.path.join(self.index_dir, f"{crop}.index")
            if os.path.exists(index_path):
                self.indices[crop] = faiss.read_index(index_path)
            else:
                print(f"⚠️ Index for {crop} not found, building required...")
                
    def retrieve(self, crop: str, query: str, top_k: int = 2) -> list[dict]:
        if not crop:
            return []
            
        crop = crop.lower()
        # Handle Tamil crop names mapping (simple fallback)
        crop_map = {
            "நெல்": "rice", "பருத்தி": "cotton", "கரும்பு": "sugarcane",
            "நிலக்கடலை": "groundnut", "மக்காச்சோளம்": "maize", "தக்காளி": "tomato"
        }
        for tamil, eng in crop_map.items():
            if tamil in crop:
                crop = eng
                break

        if crop not in self.indices:
            print(f"⚠️ FAISS: Crop '{crop}' not found in indices.")
            # Search all if crop is unknown? For now, we return empty as RAG relies on crop isolation
            return []
            
        query_embedding = self.embedder.embed_text(query).reshape(1, -1)
        distances, indices = self.indices[crop].search(query_embedding, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            doc = self.metadata[crop][idx]
            results.append({
                "doc": doc,
                "score": float(distances[0][i])
            })
            
        return results

def init_models():
    """Called on FastAPI startup to pre-warm BGE-M3 and FAISS indices."""
    global _embedder_model, _retriever
    if _embedder_model is not None:
        return
        
    try:
        _embedder_model = Embedder(model_name="BAAI/bge-m3", device="cpu")
        
        # We store indices in backend/data/faiss_indices
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        index_dir = os.path.join(data_dir, "faiss_indices")
        kb_path = os.path.join(os.path.dirname(__file__), "..", "..", "disease-prediction", "kb_data_gen.json")
        
        # Verify KB path exists
        if not os.path.exists(kb_path):
            print(f"❌ KISAN-AI KB not found at {kb_path}")
            return
            
        _retriever = Retriever(embedder=_embedder_model, index_dir=index_dir, kb_path=kb_path)
        
        if os.path.exists(index_dir) and os.listdir(index_dir):
            _retriever.load_indices()
            # Check if all crops have indices
            if not _retriever.indices:
                _retriever.build_indices()
        else:
            _retriever.build_indices()
            
    except Exception as e:
        print(f"❌ Failed to init disease RAG: {e}")

def match_disease(symptoms_text: str, crop: str = None) -> list:
    """
    Called by pipeline_service.py.
    Returns: list of dicts: [{"disease": ..., "treatment": ..., "prevention": ...}]
    """
    if not _retriever:
        print("⚠️ Disease RAG not initialized.")
        return []
        
    if not crop:
        # Fallback to extracting crop from text
        crop_map = {
            "நெல்": "rice", "பருத்தி": "cotton", "கரும்பு": "sugarcane",
            "நிலக்கடலை": "groundnut", "மக்காச்சோளம்": "maize", "தக்காளி": "tomato"
        }
        for tamil, eng in crop_map.items():
            if tamil in symptoms_text:
                crop = eng
                break
                
    if not crop:
        print("⚠️ No crop provided/found for disease match.")
        return []

    print(f"🔍 FAISS searching '{crop}' for: {symptoms_text}")
    matches = _retriever.retrieve(crop, symptoms_text, top_k=2)
    
    results = []
    if matches:
        for m in matches:
            doc = m["doc"]
            results.append({
                "disease": doc.get("disease_name"),
                "crop": doc.get("crop"),
                "symptoms": doc.get("symptoms_english", ""),
                "treatment": doc.get("remedy_english", ""),
                "prevention": doc.get("preventive_measure_english", ""),
                "score": m["score"]
            })
        print(f"✅ FAISS match: {results[0]['disease']} (score: {results[0]['score']:.2f})")
    
    return results
