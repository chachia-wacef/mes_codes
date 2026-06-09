
pip install langchain langchain-community faiss-cpu sentence-transformers

from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA

# ==========================================
# 1. Configuration des Modèles Locaux
# ==========================================
print("Chargement des modèles locaux...")

# Modèle de génération (LLM) : Il se connecte automatiquement à Ollama qui tourne en arrière-plan
llm = Ollama(
    model="mistral", # Remplacez par "llama3" si vous avez téléchargé ce modèle
    temperature=0.0  # Température à 0 pour rester factuel
)

# Modèle d'Embedding : all-MiniLM-L6-v2 est très rapide et léger (téléchargé la première fois)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ==========================================
# 2. Chargement et Chunking du texte
# ==========================================
texte_transcription = """
A: Bonjour, on peut faire un point sur le projet Alpha ?
B: Oui, j'ai vérifié les chiffres ce matin. Le budget est dépassé de 5000 euros.
A: Mince. Et pour la date de livraison ?
B: Toujours prévue pour le 15 novembre.
[... Imaginez votre texte de 50 000 mots ici ...]
"""

text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ".", " "], 
    chunk_size=1200,    
    chunk_overlap=200,  
    length_function=len
)

chunks = text_splitter.split_text(texte_transcription)
print(f"Le texte a été découpé en {len(chunks)} segments.")

# ==========================================
# 3. Création de la base vectorielle locale (FAISS)
# ==========================================
print("Vectorisation en cours (CPU/GPU local)...")
# FAISS stocke les vecteurs dans la RAM de votre ordinateur
vector_store = FAISS.from_texts(chunks, embeddings)

# Récupérer les 4 segments les plus pertinents
retriever = vector_store.as_retriever(search_kwargs={"k": 4})

# ==========================================
# 4. Configuration du Prompt et de la Chaîne
# ==========================================
template = """Tu es un assistant expert, chargé de vérifier des informations dans une transcription de réunion.
Utilise uniquement le contexte fourni ci-dessous pour répondre à la question.
Si l'information n'est pas dans le contexte, dis simplement que l'information n'est pas présente dans le texte. Ne l'invente pas.

Contexte extrait :
{context}

Question : {question}
Réponse :"""

prompt = PromptTemplate(template=template, input_variables=["context", "question"])

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    chain_type_kwargs={"prompt": prompt}
)

# ==========================================
# 5. Exécution et Test
# ==========================================
question_utilisateur = "De combien le budget du projet Alpha est-il dépassé ?"
print(f"\nQuestion : {question_utilisateur}")
print("Génération de la réponse par le LLM local...\n")

# Appel au LLM local (Ollama)
reponse = qa_chain.invoke(question_utilisateur)

print(f"Réponse : {reponse['result']}")
