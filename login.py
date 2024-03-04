import streamlit as st
import spacy
import PyPDF2
from langchain.llms import HuggingFaceHub
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import uuid
import re
import json
import streamlit as st
from docx import Document
import fitz 
import requests
import magic
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import comtypes.client
import streamlit as st
from io import BytesIO
from docx2pdf import convert
import PyPDF2,os
import requests
import comtypes

from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import streamlit as st
import mysql.connector


def load_keywords():
    file_path = "keywords.json"  # Provide the correct path if it's in a different directory
    try:
        with open(file_path, "r") as file:
            keywords_data = json.load(file)
        return keywords_data
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Unable to decode JSON in '{file_path}'.")
        return None



# get keywords from file
keywords_data = load_keywords()




# extract skills from the cv and analyse with the cv
programming_language_keywords = set(keywords_data["programming_language_keywords"])
additional_programming_languages = set(keywords_data["additional_programming_languages"])
programming_tools_keywords = set(keywords_data["programming_tools_keywords"])
related_technologies = keywords_data["related_technologies"]



# extract keyword match with the text
def extract_skills(text):
    text = text.lower()
    print(text)



    # find keywords in the text
    skills_keywords = re.findall(r'\b[A-Za-z-]+\b', text)
    print(skills_keywords)


    # declare set to store the words
    matched_keywords = set()



    # extracted keyword is in the text store that in matched keyword sets
    for keyword in skills_keywords:
        if keyword.lower() in programming_language_keywords or \
            keyword.lower() in additional_programming_languages or \
            keyword.lower() in programming_tools_keywords or \
            keyword.lower() in related_technologies:
            matched_keywords.add(keyword)


    
    # replace "react" with "react.js" if present because it may treat as general reactions
    if "react" in matched_keywords:
        matched_keywords.remove("react")
        matched_keywords.add("reactjs")

    return list(matched_keywords)




# generate a question using (llm+nlp)

def generate_interview_questions_and_answers(keywords, job_title=None, total_questions=20):

    if not keywords:
        print("No keywords found. Unable to generate questions.")
        return []

    # Initialize LLMS model for generating questions and answers
    question_generator = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature": 0.3, "max_length": 250}, huggingfacehub_api_token="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")
    answer_generator = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature": 0.3, "max_length": 10000}, huggingfacehub_api_token="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")

    qa_pairs = []
    num_questions = total_questions // len(keywords)
    
    print("Keywords:", keywords)  #verification
    for keyword in keywords:
        unique_questions = set() 
       
       #number of questions you want
        for _ in range(num_questions):
            try:
                # generate question using faln xxl
                unique_id = str(uuid.uuid4())[:8]  # uuid unique Ques

                #based on your prompt it genrate a questions
                question_prompt = f"({unique_id}) give some interview questions related to {keyword} concepts {job_title}?"
                question_response = question_generator(question_prompt)
                print("Question Response:", question_response)  # verification
                question = question_response.strip()

                # check unique question or not
                if question not in unique_questions:
                    unique_questions.add(question)

                    # get answer using google flan
                    answer_prompt = f"Provide a very detailed response to the following question: {question}"  # Changed prompt for more detailed response
                    answer_response = answer_generator(answer_prompt)
                    print("Answer Response:", answer_response)  # verify


                    # check if the Answer is detailed enough or not
                    if len(answer_response.split()) > 150:  # 100 letter min
                        answer = answer_response.strip()
                    else:
                        
                        summary = ' '.join(answer_response.split()[:150]) 
                        answer_lines = summary.split('\n')
                        answer = '\n'.join(answer_lines[:7])  

                    print("Final Answer:", answer) #verify

                    
                    qa_pairs.append((question, answer))
            except Exception as e:
                print(f"Error generating QA pair for {keyword}: {e}")

    print("QA Pairs:", qa_pairs)  #  QA verify

    return qa_pairs



#pdf text generation
def extract_text_from_pdf(file_path):
    try:
        text = ""
        with fitz.open(file_path) as pdf:
            for page_num in range(len(pdf)):
                page = pdf.load_page(page_num)
                text += page.get_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return None
    
#pdf generation for docx
def extract_text_from_docpdf(pdf_file):
    text = ""
    with pdf_file as file:
        reader = PyPDF2.PdfReader(file)
        for page_num in range(len(reader.pages)):
            text += reader.pages[page_num].extract_text()
    return text

#interact with windows app like word
comtypes.CoInitialize()

# after process word application quits for next time smooth running
word_application = comtypes.client.CreateObject("Word.Application")


#converting docx to pdf. beacuse of all docx may contain images and background image 
#that may leeds to stop generating or extracting text from the docx 
#so thats why i convert that file to docx for efficinet extraction of text
def convert_docx_to_pdf(docx_file):
    try:
        # save as temporary file
        with open("temp.docx", "wb") as f:
            f.write(docx_file.read())
        
        # remove the existing PDF if it exists
        if os.path.exists("temp.pdf"):
            os.remove("temp.pdf")
        
        comtypes.CoInitialize()
        
        # Convert the temporary DOCX file to PDF
        convert("temp.docx")
        word_application.Quit()
        
        # Read the resulting PDF file as BytesIO object
        pdf_bytes = BytesIO()
        with open("temp.pdf", "rb") as f:
            pdf_bytes.write(f.read())
        
        pdf_bytes.seek(0)
        return pdf_bytes
    
    except Exception as e:
        st.error(f"Failed to convert DOCX to PDF: {e}")
        return None



#google drive fecth data
def download_file_from_google_drive(file_id):
    try:
        URL = f"https://drive.google.com/uc?id={file_id}"
        response = requests.get(URL)
        if response.status_code == 200:
            return response.content
        else:
            return None
    except Exception as e:
        print(f"Error downloading file from Google Drive: {str(e)}")
        return None


#generate pdf to text for downloading drive file 
def generate_pdf_from_text(text, output_path):
    try:
        # path for save
        pdf_path = "./extracted_text.pdf"

        # Create a PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)

        # create a stylesheet format
        styles = getSampleStyleSheet()

        # add paragraphs to the document
        paragraphs = [Paragraph(text, styles["Normal"])]

        # build the PDF document
        doc.build(paragraphs)

        return pdf_path
    except Exception as e:
        print(f"Error generate_pdf_from_text :{e}")
        return None
    

#question and answer generation call
def generate(text,job_title):
    keywords = extract_skills(text)
    #st.subheader("Extracted Keywords using generate")
    #st.write(keywords)   #verify
    qa_pairs = generate_interview_questions_and_answers(keywords, job_title)
    with st._main:
        st.subheader("Generated Interview Questions")
        for question, answer in qa_pairs:
                st.write(f"Question: {question}")
                st.write(f"Answer: {answer}")






# authenticate user
def authenticate_user(username, password):
    # Connect to MySQL database
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='test'
    )

    cursor = connection.cursor()

    # check user exists in the database
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    return user

# register a new user
def register_user(username, password):
    # Connect to MySQL database
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='test'
    )

    cursor = connection.cursor()

    # check if the username is already taken
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        st.error("Username already exists. Please choose another.")
        return False

    # new record insert
    insert_query = "INSERT INTO users (username, password) VALUES (%s, %s)"
    cursor.execute(insert_query, (username, password))
    connection.commit()

    cursor.close()
    connection.close()

    return True


# Streamlit app
def main():
    st.set_page_config(page_title="Interview Xpert",page_icon=":scroll")
    
    # Sidebar to switch between Login and Register and logout and cv parse
    page = st.sidebar.radio("Choose a page:", ("Login", "Register", "CV XPert","Discussion with pdf's","Discussion with sites", "Logout"))

    #default authentication false
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False


    if page == "Login":
        st.title("Home:scroll:")
        st.header("Login Page")
        username = st.text_input("Username:")
        password = st.text_input("Password:", type="password")

        if st.button("Login"):
            user = authenticate_user(username, password)
            if user:
                st.success("Login Successful!")
                st.session_state.authenticated = True
            else:
                st.error("Invalid username or password")

    elif page == "Register":
        st.header("Register Page")
        new_username = st.text_input("New Username:")
        new_password = st.text_input("New Password:", type="password")

        if st.button("Register"):
            if register_user(new_username, new_password):
                st.success("Registration Successful!")
                st.write(f"Welcome, {new_username}!")


    elif page == "CV XPert" and st.session_state.authenticated:
        run_streamlit_app()


    elif page == "CV XPert":
        st.title("Go back to Login")
        st.write("Working only after successfull login")
        

    elif page == "Logout":
        st.header("Logout Page")
        st.session_state.authenticated = False
        st.success("Logout Successful!")
    st.markdown("<br>", unsafe_allow_html=True)
    col1,col2,col3=st.columns(3)
    with col1:
        st.header("CV Xpert")
        st.write("Analayse cv and give interview question based on your matches")
    with col2:
        st.header("Discussion with pdf")
        st.write("Analayse pdf and give answer based on your input questions")
    with col3:
        st.header("Discussion with Website")
        st.write("Analayse Site and give answer based on your input questions")
        
def run_streamlit_app():
    st.header("CV Analysis QA")
    
    with st.sidebar:
        #radio button for types
        option = st.radio("Choose Input Type:", ("Upload PDF", "Upload DOCX", "Google Drive Link"))
        job_title = st.text_input("Job Title (optional)")


        if option == "Upload PDF":
            uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
            if uploaded_file is not None:
                # Write content to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(uploaded_file.getvalue())
                    temp_file_path = temp_file.name

                # Read text from the uploaded PDF
                text = extract_text_from_pdf(temp_file_path)
                if text:
                    st.subheader("Extracted Text from PDF")
                    st.write(text)
                    generate(text,job_title)
            


        elif option == "Upload DOCX":
            uploaded_file = st.file_uploader("Upload CV (DOCX)", type=["docx"])
            if uploaded_file is not None:
                # convert docx to pdf call
                pdf_bytes = convert_docx_to_pdf(uploaded_file)
                if pdf_bytes:
                    # after sucessfull extraction
                    #call docpdf to text for getting text
                    text = extract_text_from_docpdf(pdf_bytes)
                    if text:
                        st.subheader("Extracted Text")
                        st.write(text[:] + "...")
                        #call generration
                        generate(text,job_title)
                    else:
                        st.error("Error extract_text_from_docpdf")
                else:
                    st.error("Error convert_docx_to_pdf.")
            
                
        elif option == "Google Drive Link":
            gdrive_link = st.text_input("Enter Google Drive Link:")
            if gdrive_link:
                file_id = gdrive_link.split('/')[-2]
                file_content = download_file_from_google_drive(file_id)
                if file_content:
                    with open("temp_file", "wb") as f:
                        f.write(file_content)

                    # Determine file type
                    file_type = magic.Magic(mime=True).from_buffer(file_content)

                    if file_type == 'application/pdf':
                        # Read text from the downloaded PDF
                        text = extract_text_from_pdf("temp_file")
                        if text:
                            st.subheader("Extracted Text from PDF")
                            st.write(text)
                            generate(text,job_title)
                            # Generate PDF from the extracted text
                            pdf_output_path = generate_pdf_from_text(text, "extracted_text.pdf")
                            if pdf_output_path:
                                st.success("PDF generated successfully.")
                                with open("extracted_text.pdf", "rb") as f:
                                    pdf_bytes = f.read()
                                st.download_button(
                                    label="Download PDF",
                                    data=pdf_bytes,
                                    key="download_button",
                                    file_name="extracted_text.pdf",
                                )
                            else:
                                st.error("Failed to generate PDF.")
                        else:
                            st.error("Error extracting text from PDF.")
                    elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        # Convert DOCX to PDF
                        pdf_bytes = convert_docx_to_pdf("temp_file")
                        if pdf_bytes:
                            # Extract text from PDF
                            text = extract_text_from_pdf(pdf_bytes)
                            if text:
                                st.subheader("Extracted Text")
                                st.write(text[:1000] + "...")
                                generate(text,job_title)
                            else:
                                st.error("Error extracting text from PDF.")
                        else:
                            st.error("Error converting DOCX to PDF.")
                else:
                    st.error("Failed to download file from Google Drive.")

if __name__ == "__main__":
    main()
