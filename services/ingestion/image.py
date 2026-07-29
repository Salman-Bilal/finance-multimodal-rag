from PIL import Image
import pytesseract

def extract_image_chunks(file_path: str) -> list[str]:
    """Extract text from images using OCR (Tesseract)."""
    try:
        image = Image.open(file_path)
        # Convert image to RGB mode if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        extracted_text = pytesseract.image_to_string(image)
        
        cleaned_text = extracted_text.strip()
        if not cleaned_text:
            return ["Image contains no detectable text."]
            
        # Return as a single chunk or chunk by lines
        return [cleaned_text]
    except Exception as e:
        # Fallback if Tesseract engine is missing on local environment
        return [f"[OCR Processing Warning]: Unable to extract text from image. Details: {str(e)}"]