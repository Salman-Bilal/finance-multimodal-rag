from PIL import Image
import pytesseract

def extract_image_chunks(file_path: str) -> list[str]:
    try:
        image = Image.open(file_path)
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        extracted_text = pytesseract.image_to_string(image)
        
        cleaned_text = extracted_text.strip()
        if not cleaned_text:
            return ["Image contains no detectable text."]
            
        return [cleaned_text]
    except Exception as e:
        return [f"[OCR Processing Warning]: Unable to extract text from image. Details: {str(e)}"]