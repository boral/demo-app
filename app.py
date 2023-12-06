import streamlit as st
import fitz  # PyMuPDF
from openai import OpenAI
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv('API_KEY')

client = OpenAI( api_key=key)

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

def create_pdf( input_text):
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

    # Build the PDF document
    doc.build(flowables)


def main():
    st.title("Radiologist")

    # Upload image
    uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    
    if uploaded_image is not None:
        # Display the uploaded image
        st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
        
        with open('uploaded_image.jpg', "wb") as f:
            f.write(uploaded_image.read())
        
        create_pdf( radiologist_report( 'uploaded_image.jpg' ) )   #>.. report

        # Display report
        display_pdf('radiologist_report.pdf')


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
