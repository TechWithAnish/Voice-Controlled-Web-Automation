import time
import PyPDF2
from selenium import webdriver
from selenium.webdriver.common.by import By

def extract_data_from_pdf(pdf_file_path):
    # Implement your PDF parsing code here.
    # This function should extract relevant data from the PDF file.
    # For simplicity, let's assume the extracted_data dictionary with static data.
    extracted_data = {
        'name': 'John Doe',
        'email': 'johndoe@example.com',
        'address': '123 Main St, City, Country',
        # Add other fields as needed...
    }

    return extracted_data

def fill_form(url, data):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        time.sleep(2)

        # Find form fields and fill them using the extracted data.
        name_field = driver.find_element(By.NAME, 'name')
        name_field.send_keys(data['name'])

        email_field = driver.find_element(By.NAME, 'email')
        email_field.send_keys(data['email'])

        address_field = driver.find_element(By.NAME, 'address')
        address_field.send_keys(data['address'])

        # Add more fields as needed...

        # Submit the form.
        submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        time.sleep(2)

    finally:
        driver.quit()

if __name__ == "__main__":
    # URL of the form to fill.
    form_url = "https://forms.monday.com/forms/e41be69cc0e04d5f33bd471c3a64a6cb?r=use1"

    # Replace this with the actual path of the PDF file.
    pdf_file_path = r"C:\Users\anish\Downloads\empowerverse.pdf"

    # Extract data from the PDF.
    extracted_data = extract_data_from_pdf(pdf_file_path)

    # Fill the form with the extracted data.
    fill_form(form_url, extracted_data)
