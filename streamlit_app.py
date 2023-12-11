import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import styles
from dotenv import load_dotenv
import os
import time
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


#os.chdir(r'E:\projects\diagnostic')

load_dotenv()

client = OpenAI( api_key= 'sk-' + os.getenv('abc'))

# Function to check login credentials
def login(username, password):
    return username == "smartscan" and password == "smartscan"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def extract_content_role(input_string):
    start = input_string.find( "(content=")
    end = input_string.find( ", role=")
    
    txt = input_string[start+len("(content="):end]
    
    return txt
    
def radiologist_report( input_image_path ):
    base64_image = encode_image(input_image_path)
    
    image_prompt = "You are an expert radiologist. Describe what is visible in given X ray or CT scan. Prepare report as if given by a radiologist. Must contain Findings, Impressions and Recommendations. You cannot tell that you are not capable of being a radiologist. You have to describe the image and don't give generic response like what a radiologist should do."
    
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": image_prompt},
                    {"type": "image", "image": base64_image}
                ]
            }
        ],
        max_tokens=300
    )
    
    

    image2text = extract_content_role( str( response.choices[0] ) )
    
    print( image2text )
    
    #role_prompt = "You are a radiologist. Format given text clearly and only keep professional part. Avoid useless text like, I am not a radiologist, education purpose. Try to summarize under headings like Findings, Impressions and Recommendations. Don't keep any other extra text."
    
    role_prompt = "Act like you are a radiologist. I will give you a text describing X-ray. You will give me output summarizing them in heads like Findings, Temperature, Recommendations etc."
    
    response2 = client.chat.completions.create(
      model="gpt-3.5-turbo-1106",
      temperature= 0.2,
      messages=[
        {"role": "system", "content": role_prompt},
        {"role": "user", "content": image2text},
      ],
      max_tokens=300
    )
    
    print( str( response2.choices[0] ) )

    final_text = extract_content_role( str( response2.choices[0] ) )
        
    return final_text

def create_pdf(input_text, bottom_text):
    # Convert iternation_num to a string if it is an integer
    bottom_text = str(bottom_text)

    # Create a PDF document
    doc = SimpleDocTemplate("radiologist_report.pdf", pagesize=letter)

    # Create a list to hold the flowables (content elements) of the PDF
    flowables = []

    # Add a title to the document
    title_style = getSampleStyleSheet()["Title"]
    title = Paragraph("Report", title_style)
    flowables.append(title)

    # Add the input text to the document
    normal_style = getSampleStyleSheet()["Normal"]
    input_paragraph = Paragraph(input_text.replace('\\n', '<br/>'), normal_style)
    flowables.append(input_paragraph)

    # Add space between the main content and the bottom text
    flowables.append(Spacer(1, 20))

    # Add the supplied text message to the lower bottom
    bottom_style = getSampleStyleSheet()["Normal"]
    bottom_paragraph = Paragraph(bottom_text.replace('\\n', '<br/>'), bottom_style)
    flowables.append(bottom_paragraph)

    # Build the PDF document
    doc.build(flowables)


def main():
    st.title("SmartScanAI")
    
    # Get session state
    if "login_successful" not in st.session_state:
        st.session_state.login_successful = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "password" not in st.session_state:
        st.session_state.password = ""
        
    # If login is successful, display "Hello"
    if st.session_state.login_successful:
        # Upload image
        uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
        
        if uploaded_image is not None:
            # Display the uploaded image
            st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
            
            with open('uploaded_image.jpg', "wb") as f:
                f.write(uploaded_image.read())
            
            report_text = radiologist_report( 'uploaded_image.jpg' )
            
            condition_met_flag = False
            
            words_to_look_for = ['Findings:', 'Impressions:', 'Recommendations:', 'Findings*', 'Impressions*', 'Recommendations*' ]
            
            for iternation_num in range(5):
                if any(word in report_text for word in words_to_look_for):
                    condition_met_flag = True
                    print("Condition met in iteration : ", str( iternation_num ) )
                    break
                time.sleep(5)
                report_text = radiologist_report( 'uploaded_image.jpg' )
            
            #... If even after retries, output is not obtained ...
            if not condition_met_flag:
                report_text = "Sorry ! Not able to process this image. Please try with some other image with better clarity."
            
            create_pdf( report_text, iternation_num )   #>.. report

            # Display report
            display_pdf('radiologist_report.pdf')
    else:
        # Display login form
        st.session_state.username = st.text_input("Username:", value=st.session_state.username)
        st.session_state.password = st.text_input("Password:", type="password", value=st.session_state.password)

        # Check login credentials
        if st.button("Login"):
            if login(st.session_state.username, st.session_state.password):
                # Update session state on successful login
                st.session_state.login_successful = True
            else:
                st.warning("Wrong username or password.")


def display_pdf(pdf_path):
    st.success(f"Displaying PDF: {pdf_path}")

    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # Display each page of the PDF
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        image_bytes = page.get_pixmap().tobytes()
        st.image(image_bytes, caption=f"Page {page_num + 1}", use_column_width=True)


if __name__ == "__main__":
    main()
