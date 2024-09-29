from PIL import Image
import pytesseract
import os
import fitz  # PyMuPDF

# Specify the path to the Tesseract executable if necessary
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def load_ocr_image(image_filename):
    img = Image.open(image_filename)
    return img

def write_to_file(file_name_path, text_content):
    print('Writing to file - ' + file_name_path)
    f = open(file_name_path, 'w')
    f.write(text_content)
    f.close()

def delete_file(file_path):
    os.remove(file_path)

def create_temp_file(loaded_file):
    # save the file temporarily
    temp_file = f"./tmp_{loaded_file.name}"
    with open(temp_file, "wb") as file:
        file.write(loaded_file.getvalue())
    return temp_file

## TODO: write ur own custom method
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
        write_to_file('ocr_text.txt', extracted_text)
        delete_file(tmp_pdf_file_path)
        return extracted_text
    except Exception as e:
        print('Exception in extarct_text_from_ocr_pdf - ', e)


def extract_ocr_data(uploaded_file):

    if uploaded_file.type in ['image/jpg', 'image/jpeg', 'image/png']:
        ocr_extracted_data = extract_text_from_image(uploaded_file)
        return ocr_extracted_data
        
    elif uploaded_file.type in ['application/pdf']:
        # For PDF files
        # pdf_extracted_data = read_pdf(uploaded_file)
        # st.write(pdf_extracted_data)

        # For OCR pdf files
        ocr_extracted_data =  extarct_text_from_ocr_pdf(uploaded_file)
        return ocr_extracted_data

def display_ocr_file(uploaded_file):
    img = load_ocr_image(uploaded_file)
    return img
