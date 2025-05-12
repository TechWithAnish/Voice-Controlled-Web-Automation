import time
import pdfplumber
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def extract_data_from_pdf(pdf_file_path):
    """Extract key-value pairs from a PDF using pdfplumber."""
    try:
        extracted_data = {}
        with pdfplumber.open(pdf_file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # Simple parsing: assume fields are in "Field: Value" format
                lines = text.split("\n")
                for line in lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        extracted_data[key.strip().lower()] = value.strip()
        return extracted_data
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return {
            'name': 'John Doe',
            'email': 'johndoe@example.com',
            'address': '123 Main St, City, Country'
        }

def fill_form(url, data, field_mappings):
    """Fill a web form with extracted data."""
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(2)

        # Fill form fields based on mappings
        for data_key, field_name in field_mappings.items():
            if data_key in data:
                try:
                    field = driver.find_element(By.NAME, field_name)
                    field.send_keys(data[data_key])
                except Exception as e:
                    print(f"Could not fill field '{field_name}': {e}")

        # Submit the form
        submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()
        time.sleep(2)

    except Exception as e:
        print(f"Error filling form: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    # Example form URL and PDF path
    form_url = "https://forms.monday.com/forms/e41be69cc0e04d5f33bd471c3a64a6cb?r=use1"
    pdf_file_path = "sample_form_data.pdf"

    # Field mappings: {PDF key: form field name}
    field_mappings = {
        'name': 'name',
        'email': 'email',
        'address': 'address'
    }

    # Extract and fill
    extracted_data = extract_data_from_pdf(pdf_file_path)
    fill_form(form_url, extracted_data, field_mappings)