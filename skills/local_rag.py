import os
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader
from docx import Document
import time

class LocalRAG:
    def __init__(self, db_path="chroma_db", documents_path="documents"):
        self.db_path = db_path
        self.documents_path = documents_path
        self.indexed_files_metadata = {} # {file_path: last_mtime}
        
        # Pastas padrão do sistema para monitorar
        self.watch_folders = [
            self.documents_path,
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "Documents")
        ]
        
        # Cria a pasta de documentos local se não existir
        if not os.path.exists(self.documents_path):
            os.makedirs(self.documents_path)
            
        # Inicializa o ChromaDB
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Modelo de embeddings local (leve e eficiente)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Coleção para o Jarvis
        self.collection = self.client.get_or_create_collection(
            name="jarvis_knowledge",
            embedding_function=self.embedding_fn
        )

    def _extrair_texto(self, file_path):
        """Extrai texto de PDF, DOCX ou TXT."""
        ext = os.path.splitext(file_path)[1].lower()
        texto = ""
        try:
            if ext == ".pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    texto += page.extract_text() + "\n"
            elif ext == ".docx":
                doc = Document(file_path)
                for para in doc.paragraphs:
                    texto += para.text + "\n"
            elif ext == ".txt" or ext == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    texto = f.read()
            return texto.strip()
        except Exception as e:
            print(f"[RAG] Erro ao ler {file_path}: {e}")
            return None

    def indexar_documentos(self, specific_folders=None):
        """Varre as pastas configuradas e indexa arquivos novos ou alterados."""
        folders = specific_folders if specific_folders else self.watch_folders
        all_files = []
        for folder in folders:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    full_path = os.path.join(folder, f)
                    if os.path.isfile(full_path):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in [".pdf", ".docx", ".txt", ".md"]:
                            all_files.append(full_path)
        
        count = 0
        for arq in all_files:
            try:
                mtime = os.path.getmtime(arq)
                # Só indexa se for novo ou se o arquivo foi modificado
                if arq not in self.indexed_files_metadata or self.indexed_files_metadata[arq] < mtime:
                    texto = self._extrair_texto(arq)
                    if texto:
                        # Chunking simples por parágrafo
                        chunks = [c.strip() for c in texto.split("\n\n") if len(c.strip()) > 50]
                        if not chunks: continue
                        
                        ids = [f"{os.path.basename(arq)}_{i}_{int(mtime)}" for i in range(len(chunks))]
                        metadatas = [{"source": os.path.basename(arq), "path": arq} for _ in chunks]
                        
                        self.collection.upsert(
                            ids=ids,
                            documents=chunks,
                            metadatas=metadatas
                        )
                        self.indexed_files_metadata[arq] = mtime
                        count += 1
            except Exception as e:
                print(f"[RAG] Erro ao processar {arq}: {e}")
                
        if count > 0:
            return f"Indexação concluída. {count} novos arquivos ou alterações processadas."
        return "Nenhuma alteração detectada nos documentos."

    def consultar_conhecimento(self, query, n_results=3):
        """Busca os trechos mais relevantes para uma pergunta."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents'][0]:
                return "Não encontrei informações relevantes nos documentos locais, senhor."
            
            contexto = "\n\n".join(results['documents'][0])
            fontes = ", ".join(set([m['source'] for m in results['metadatas'][0]]))
            
            return f"Baseado nos documentos ({fontes}):\n\n{contexto}"
        except Exception as e:
            return f"Erro na consulta de conhecimento local: {e}"

# Instância global para ser importada pelo jarvis.py
rag_service = LocalRAG()
