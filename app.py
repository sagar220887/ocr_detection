import streamlit as st
from io import StringIO
from langchain_community.document_loaders import PyPDFLoader
from PIL import Image
from PyPDF2 import PdfReader
from streamlit_pdf_viewer import pdf_viewer
import base64
import pytesseract
from PIL import Image
import os
import pathlib
import fitz  # PyMuPDF

from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import StringIO
import time
from langchain.llms import CTransformers
from langchain.embeddings import HuggingFaceEmbeddings
# from langchain import PromptTemplate
from langchain import HuggingFaceHub
from langchain.chains import RetrievalQA
# from langchain.vectorstores import FAISS

from langchain_core.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import UnstructuredURLLoader, MergedDataLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pickle

# from transformers import  AutoTokenizer
# from ctransformers import AutoModelForCausalLM
# from langchain_community.llms import HuggingFaceHub
from langchain_community.vectorstores import FAISS
# from langchain_community.llms import CTransformers
# from langchain_community.embeddings import HuggingFaceEmbeddings
import ocr_process


## pip install pdf2image Pillow pytesseract

###  To run this file execute below command line
## streamlit run app.py --server.enableXsrfProtection false




parent_path = os.path.dirname(os.getcwd())
OCR_EXTRACTED_DATA_FOLDER = os.path.join(parent_path,'data', 'ocr')
OCR_EXTRACTED_DATA_FILE = os.path.join(OCR_EXTRACTED_DATA_FOLDER, 'ocr_extracted_data.txt')
vector_db_directory = "./model/vectordb"
os.makedirs(vector_db_directory, exist_ok=True)
os.makedirs(OCR_EXTRACTED_DATA_FOLDER, exist_ok=True)
chain = None
vector_db = None

from dotenv import load_dotenv
load_dotenv()

HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HUGGINGFACEHUB_API_TOKEN = os.getenv('HUGGINGFACEHUB_API_TOKEN')


if "ocr_uploaded_data" not in st.session_state:
    st.session_state["ocr_uploaded_data"] = None

if "ocr_file" not in st.session_state:
    st.session_state["ocr_file"] = None

if "processComplete" not in st.session_state:
    st.session_state.processComplete = None
if "new_data_source" not in st.session_state:
    st.session_state.new_data_source = False
if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = None

if "data_chunks" not in st.session_state:
    st.session_state.data_chunks = None

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# file process button state
if "file_process" not in st.session_state:
    st.session_state.file_process = None

# Initialize chat history
if "upload_files" not in st.session_state:
    st.session_state.upload_files = None

if "vector_db" not in st.session_state:
    st.session_state.vector_db = None

st.markdown(
    """
<style>
    .st-emotion-cache-4oy321 {
        flex-direction: row;
        text-align: left;
    }
</style>
""",
    unsafe_allow_html=True,
)


def read_pdf(file):
    print('Inside read_pdf')
    with st.spinner('Processing, Wait for it...'):
        try:
            pdfReader = PdfReader(file)
            count = len(pdfReader.pages)
            all_page_text = ""
            for i in range(count):
                page = pdfReader.pages[i]
                all_page_text += page.extract_text()
            return all_page_text
        except Exception as err:
            st.error(f"Error reading PDF: {err}")
            return None
        
# Specify the path to the Tesseract executable if necessary
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

######################## File Operations ###

def write_to_file(file_name_path, text_content):
    print('Writing to file - ' + file_name_path)
    f = open(file_name_path, 'w')
    f.write(text_content)
    f.close()
    # st.write(f'## File data saved in - ', file_name_path)
    
def create_temp_file(loaded_file):
    # save the file temporarily
    temp_file = f"./tmp_{loaded_file.name}"
    with open(temp_file, "wb") as file:
        file.write(loaded_file.getvalue())
    return temp_file

def delete_file(file_path):
    os.remove(file_path)

def get_file_info_uploaded_in_streamlit(uploaded_file):
    file_info = {
        'filename': uploaded_file.name,
        'file_type': uploaded_file.type,
        'file_size': uploaded_file.size
    }
    return file_info

####################### OCR processing functions ###

def load_ocr_image(image_filename):
    img = Image.open(image_filename)
    return img


def extract_text_from_image(image_path):
    # Open the image file
    try:
        with Image.open(image_path) as img:
            # Use pytesseract to do OCR on the image
            text = pytesseract.image_to_string(img)
            # Write the extracted text to a file
            write_to_file('ocr_text.txt', text)
            return text
    except Exception as e:
        print(f"Error processing the image: {e}")
        return None
  
def extarct_text_from_ocr_pdf(pdf_file):
    print('Inside extarct_text_from_ocr_pdf ===> ', pdf_file)
    try:
        tmp_pdf_file_path = create_temp_file(pdf_file)
        print('tmp_pdf_file_path - ', tmp_pdf_file_path)
        # Open the PDF file
        doc = fitz.open(tmp_pdf_file_path)
        extracted_text = ""
        # Iterate through each page
        for page in doc:
            extracted_text += page.get_text() + "\n"
        # Close the PDF file
        doc.close()
        # Write the extracted text to a file
        write_to_file(OCR_EXTRACTED_DATA_FILE, extracted_text)
        delete_file(tmp_pdf_file_path)
        return extracted_text
    except Exception as e:
        print('Exception in extarct_text_from_ocr_pdf - ', e)

## TODO
def display_ocr_data(uploaded_files):
    print('Inside display_ocr_data ===> ' + str(uploaded_files))
    for uploaded_file in uploaded_files:
        ## Display the file metadata
        file_info = get_file_info_uploaded_in_streamlit
        st.write(file_info)

        ## Display the image file uploaded
        ocr_image_file = ocr_process.display_ocr_file(uploaded_file)
        st.image(ocr_image_file, caption=uploaded_file.name, width=700)

        ## Display the contents of the image file
        ocr_extracted_data = ocr_process.extract_ocr_data(uploaded_file)
        st.text(ocr_extracted_data)

    st.session_state.conversation = process_data_for_search(OCR_EXTRACTED_DATA_FILE)


##############################################  Chat with Document ###############################################


def load_data_source(loaded_files):
    for loaded_file in loaded_files:
        print('loaded_file - ', loaded_file)
        temp_file = create_temp_file(loaded_file)
        loader = get_loader_by_file_extension(temp_file)
        print('loader - ', loader)
        data = loader.load()
        return data
    
def load_data_source_from_file(filename):
    loader = get_loader_by_file_extension(filename)
    print('loader - ', loader)
    data = loader.load()
    return data
    
def get_loader_by_file_extension(temp_file):
    file_split = os.path.splitext(temp_file)
    file_name = file_split[0]
    file_extension = file_split[1]
    print('file_extension - ', file_extension)

    
    if file_extension == '.pdf':
        loader = PyPDFLoader(temp_file)
        print('Loader Created for PDF file')
    
    elif file_extension == '.txt':
        loader = TextLoader(temp_file)

    elif file_extension == '.csv':
        loader = CSVLoader(temp_file)

    else :
        loader = UnstructuredFileLoader(temp_file)

    return loader

def get_data_chunks(data):
    recursive_char_text_splitter=RecursiveCharacterTextSplitter(
                                                chunk_size=500,
                                                chunk_overlap=50)
    documents=recursive_char_text_splitter.split_documents(data)
    # print('documents - ', documents)
    print('documents type - ', type(documents))
    print('documents length - ', len(documents))
    return documents

def create_embeddings():
    embeddings=HuggingFaceEmbeddings(
            model_name='sentence-transformers/all-MiniLM-L6-v2', 
            model_kwargs={'device':'cpu'}
    )
    print('%%%%%%%%%%% :: Embeddings Created ::')
    return embeddings

def store_data_in_vectordb(documents, embeddings):
    try:
        current_vectordb = load_vectordb(vector_db_directory, embeddings)
        print('current_vectordb - ', current_vectordb)
    except:
        print('Exception inside storing data in vector db')

    new_knowledge_base =FAISS.from_documents(documents, embeddings)
    print('new_knowledge_base - ', new_knowledge_base)

    # Saving the new vector DB
    new_knowledge_base.save_local(vector_db_directory)
    print('%%%%%%%%%%% :: Data stored in VectorDB ::')
    return new_knowledge_base

def load_vectordb(stored_directory, embeddings):
    loaded_vector_db = FAISS.load_local(stored_directory, embeddings)
    return loaded_vector_db
    
def get_llm_model():
    try:
        llm = HuggingFaceHub(repo_id="mistralai/Mistral-7B-Instruct-v0.2", huggingfacehub_api_token=HF_API_KEY)
    except Exception as e:
        print('Exception inside get_llm_model from Huggingface - ', e)

    try:
        llm=CTransformers(
                model="model/llama-2-7b-chat.ggmlv3.q4_0.bin",
                model_type="llama",
                config={'max_new_tokens':128,
                        'temperature':0.01}
        )
        # llm = AutoModelForCausalLM.from_pretrained("./model/mistral-7b-instruct-v0.1.Q4_K_S.gguf", model_type="cpu")
        print('LLM model Loaded')
        return llm
    except Exception as e:
        print('Exception inside get_llm_model from local - ', e)

    return None

def get_prompt():
    template="""Use the following pieces of information to answer the user's question.
            If you dont know the answer just say you dont know, don't try to make up an answer.

            Context:{context}
            Question:{question}

            Only return the helpful answer below and nothing else
            Helpful answer
            """
    

    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    print('Prompt created')
    return prompt

def create_chain(llm, vector_store, prompt):
    chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type='stuff',
            retriever=vector_store.as_retriever(search_kwargs={'k': 2}),
            return_source_documents=False,
            chain_type_kwargs={'prompt': prompt}
    )
    print('Chain created')
    return chain

def create_conversational_chain(llm, vector_store, prompt):
    memory = ConversationBufferMemory()
    conversation_chain = ConversationalRetrievalChain(
        llm=llm,
        chain_type='stuff',
        retriever=vector_store.as_retriever(search_kwargs={'k': 2}),
        return_source_documents=True,
        chain_type_kwargs={'prompt': prompt},
        memory=memory
    )
    print('Chain created')
    return conversation_chain

def get_similiar_docs(vector_db,query,k=1,score=False):
  if score:
    similar_docs = vector_db.similarity_search_with_score(query,k=k)
  else:
    similar_docs = vector_db.similarity_search(query,k=k)
  return similar_docs

def process_data_for_search(uploaded_files):

    try:

        with st.spinner('Processing, Wait for it...'):
        
            # #Load the PDF File
            documents = load_data_source_from_file(uploaded_files)

            # #Split Text into Chunks
            st.session_state.data_chunks = get_data_chunks(documents)

            # #Load the Embedding Model
            embeddings = create_embeddings()

            # #Convert the Text Chunks into Embeddings and Create a FAISS Vector Store
            st.session_state.vector_db=store_data_in_vectordb(st.session_state.data_chunks, embeddings)
            
            llm = get_llm_model()

            qa_prompt = get_prompt()

            chain = create_chain(llm, st.session_state.vector_db, qa_prompt)

            st.text("Ready to go ...✅✅✅")
            st.session_state.processComplete = True

            return chain
    except Exception as e:
        print('Exception: %s' % e)
    
def get_vectordb_response(user_query):
    try:
        db = st.session_state.vector_db
        similarity_search_value = db.similarity_search(user_query)
        print('user_query - ', user_query)
        print('similarity_search_value from VectorDB - ', similarity_search_value)
        document = similarity_search_value[0]
        return document.page_content
    except Exception as e:
        st.error('Exception inside vector similarity_search - ', e)

def get_llm_response(user_query):
    if st.session_state.conversation :
        result=st.session_state.conversation({'query':user_query}, return_only_outputs=True)
        print('result from llm - ', result)
        ans = result['result']
        print(f"Answer:{ans}")
        return ans



########## UI Rendering  #################
    

def ocr_file_uploader():
    files_uploaded = st.file_uploader(
        label="Upload OCR file",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )
    return files_uploaded

def display_process_btn():
    process_btn = st.button(
        label="Process ocr Image",
        key='ocr_process_btn',
        on_click=display_ocr_data,
        args=(st.session_state["ocr_uploaded_data"],)
    )
    return process_btn


with st.sidebar:
    st.session_state["ocr_uploaded_data"] = ocr_file_uploader()
    display_process_btn()


with st.chat_message("assistant"):
    st.write("Hello Human, How do I help U.")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    print('message - ', message)
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask Question about your files."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        print('Inside st.chat_message("assistant")')
        with st.spinner('Processing ...'):
            response = get_vectordb_response(prompt)
            st.text('Vector Response : \n', response)

            # response = get_llm_response(prompt)
            st.text('LLM Response : \n', response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
        
    
