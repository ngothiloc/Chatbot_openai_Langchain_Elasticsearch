from elasticsearch import Elasticsearch
from langchain.vectorstores import ElasticsearchStore
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader
)
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
import tempfile
import os
from src.config.config import (
    ELASTICSEARCH_URL,
    OPENAI_API_KEY,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SEPARATORS
)

class ElasticsearchService:
    def __init__(self):
        self.es = Elasticsearch(ELASTICSEARCH_URL)
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=SEPARATORS
        )
        self.vectorstore = ElasticsearchStore(
            es_connection=self.es,
            index_name="chatbot",
            embedding=self.embeddings,
            vector_query_field="embedding"
        )

    def process_file(self, uploaded_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        try:
            # Load document based on file type
            if uploaded_file.name.endswith('.txt'):
                loader = TextLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.pdf'):
                loader = PyPDFLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.docx'):
                loader = UnstructuredFileLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.md'):
                loader = UnstructuredMarkdownLoader(tmp_file_path)
            
            # Load and split the document
            documents = loader.load()
            splits = self.text_splitter.split_documents(documents)
            
            # Add documents to vectorstore
            self.vectorstore.add_documents(splits)
            return True, f"Đã xử lý thành công file: {uploaded_file.name}"
            
        except Exception as e:
            return False, f"Lỗi khi xử lý file {uploaded_file.name}: {str(e)}"
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)

    def get_retriever(self):
        return self.vectorstore.as_retriever() 