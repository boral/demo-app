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
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
import pandas as pd


#os.chdir(r'E:\projects\smartscan')

load_dotenv()

client = OpenAI( api_key= 'sk-' + os.getenv('abc'))

config_df = pd.read_csv(r"config.csv")

# Function to check login credentials
def login(username, password):
    return username == "smartscan" and password == "smartscan"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def get_discipline_details( input_discipline ):
    result_df = config_df[ config_df['discipline'] == input_discipline ]
    result_df.reset_index(inplace=True)
    return result_df
    
def extract_content_role(input_string):
    start = input_string.find( "(content=")
    end = input_string.find( ", role=")
    
    txt = input_string[start+len("(content="):end]
    
    return txt
    
def radiologist_report( input_image_path, image_prompt, role_prompt ):
    base64_image = encode_image(input_image_path)
       
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
    
    icd_prompt = "Give ICD-10 code based on given text."
    
    response3 = client.chat.completions.create(
      model="gpt-3.5-turbo-1106",
      temperature= 0.2,
      messages=[
        {"role": "system", "content": icd_prompt},
        {"role": "user", "content": final_text},
      ],
      max_tokens=300
    )
    
    code = extract_content_role( str( response3.choices[0] ) )
    
    final_text_2 = final_text + "\\n" + code + "\\n"
        
    return final_text_2

def create_pdf(input_text, bottom_text, uploaded_image):
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

    # Add the image to the document
    if uploaded_image:
        image = Image(uploaded_image, width=300, height=300)  # Adjust width and height as needed
        flowables.append(image)
    
    # Add space between the main content and the bottom text
    flowables.append(Spacer(1, 20))

    # Add the supplied text message to the lower bottom
    bottom_style = getSampleStyleSheet()["Normal"]
    bottom_paragraph = Paragraph(bottom_text.replace('\\n', '<br/>'), bottom_style)
    flowables.append(bottom_paragraph)

    # Build the PDF document
    doc.build(flowables)
    
def display_pdf(pdf_path):
    st.success("Report generated successfully.")

    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # Display each page of the PDF
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        image_bytes = page.get_pixmap().tobytes()
        st.image(image_bytes, caption=f"Page {page_num + 1}", use_column_width=True)
    
def download_pdf():
    with open("radiologist_report.pdf", "rb") as file:
        btn = st.download_button(
                label="Download Report",
                data=file,
                file_name="radiologist_report.pdf"
              )


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
        
        # Use st.beta_columns or st.columns to create a side-by-side layout
        col1, col2 = st.columns([3,7])
        # Create a dropdown to select discipline
        selected_discipline = col1.selectbox("Select Discipline", config_df['discipline'])
        
        # Upload image
        uploaded_image = col2.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
        
        if st.button("Submit"):
            
            if selected_discipline and ( uploaded_image is not None ):
            
                #..... Filtering for selected Discipline ....
                selected_discipline_df = get_discipline_details(selected_discipline)
                
                image_prompt = selected_discipline_df.image_prompt[0]
                
                role_prompt = selected_discipline_df.role_prompt[0]
                
                # Display the uploaded image
                st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
                
                with open('uploaded_image.jpg', "wb") as f:
                    f.write(uploaded_image.read())
                
                report_text = radiologist_report( 'uploaded_image.jpg', image_prompt, role_prompt )
                
                condition_met_flag = False
                
                words_to_look_for = ['Findings:', 'Impressions:', 'Recommendations:', 'Findings*', 'Impressions*', 'Recommendations*' ]
                
                for iternation_num in range(5):
                    if any(word in report_text for word in words_to_look_for):
                        condition_met_flag = True
                        print("Condition met in iteration : ", str( iternation_num ) )
                        break
                    time.sleep(5)
                    report_text = radiologist_report( 'uploaded_image.jpg', image_prompt, role_prompt )
                
                #... If even after retries, output is not obtained ...
                if not condition_met_flag:
                    report_text = "Sorry ! Not able to process this image. Please try with some other image with better clarity."
                
                create_pdf( report_text, iternation_num, uploaded_image )   #>.. report
    
                # Display report
                download_pdf()
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



if __name__ == "__main__":
    main()
