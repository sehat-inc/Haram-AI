from pyzerox import zerox
import os
import asyncio
import img2pdf
from PIL import Image
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
### Model Setup (Use only Vision Models) Refer: https://docs.litellm.ai/docs/providers ###

## placeholder for additional model kwargs which might be required for some models
kwargs = {}

## system prompt to use for the vision model
custom_system_prompt = """
You are an expert at extracting ingredient information from grocery product labels.
Focus on identifying and listing all ingredients in the image.
If there are allergen warnings (like 'CONTAINS' or 'MAY CONTAIN'), include those as well.
Format the output as follows:

INGREDIENTS:
- [ingredient 1]
- [ingredient 2]
...

ALLERGEN INFORMATION:
- [allergen info]

If you cannot identify ingredients clearly, indicate this and provide any partial information you can extract.
"""

###################### Example for Gemini ######################
model = "gemini/gemini-2.0-flash" ## "gemini/<gemini_model>" -> format <provider>/<model>
os.environ['GEMINI_API_KEY'] # your-gemini-api-key

###################### For other providers refer: https://docs.litellm.ai/docs/providers ######################

def convert_image_to_pdf(image_path):
    """
    Convert an image file to PDF format
    """
    try:
        # Get the output PDF path (same name but with .pdf extension)
        output_pdf = str(Path(image_path).with_suffix('.pdf'))

        # Check if the image exists
        if not os.path.exists(image_path):
            print(f"Error: Image file {image_path} does not exist.")
            return None

        # Convert image to PDF using img2pdf
        with open(output_pdf, "wb") as f:
            # Open image to check if it's valid
            image = Image.open(image_path)
            # Convert to RGB if it's RGBA (to avoid transparency issues)
            if image.mode == 'RGBA':
                image = image.convert('RGB')
                rgb_image_path = str(Path(image_path).with_suffix('.rgb.jpg'))
                image.save(rgb_image_path)
                image_path = rgb_image_path
            image.close()

            # Convert to PDF
            f.write(img2pdf.convert(image_path))

        print(f"Successfully converted {image_path} to {output_pdf}")
        return output_pdf
    except Exception as e:
        print(f"Error converting image to PDF: {str(e)}")
        return None

# Define main async entrypoint
async def main():
    # Check if a file path was provided as a command-line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        print("Please provide a file path as a command-line argument.")
        return "No file provided"

    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return f"File {file_path} not found"

    # Check if the file is an image (not a PDF)
    image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif", ".webp"]
    if any(file_path.lower().endswith(ext) for ext in image_extensions):
        print(f"Converting image {file_path} to PDF...")
        pdf_path = convert_image_to_pdf(file_path)
        if not pdf_path:
            return "Failed to convert image to PDF"
        file_path = pdf_path

    # Process only some pages or all
    select_pages = None  # None for all, but could be int or list(int) page numbers (1 indexed)

    # Create output directory if it doesn't exist
    output_dir = "./output_test"  # directory to save the consolidated markdown file
    os.makedirs(output_dir, exist_ok=True)

    # Process the PDF with Zerox
    try:
        zerox_output = await zerox(file_path=file_path, model=model, output_dir=output_dir,
                          custom_system_prompt=custom_system_prompt, select_pages=select_pages, **kwargs)

        # Inspect the Zerox output object
        print("\nZerox output type:", type(zerox_output))

        # Extract content from the ZeroxOutput object
        if hasattr(zerox_output, 'pages') and zerox_output.pages:
            # Get content from the first page
            page = zerox_output.pages[0]
            if hasattr(page, 'content'):
                result = page.content
                print("Extracted content from page object")
            else:
                print("Page object attributes:", dir(page))
                result = str(page)
                print("Converted page object to string")
        elif hasattr(zerox_output, 'markdown'):
            result = zerox_output.markdown
            print("Using 'markdown' attribute")
        elif hasattr(zerox_output, 'text'):
            result = zerox_output.text
            print("Using 'text' attribute")
        elif hasattr(zerox_output, 'content'):
            result = zerox_output.content
            print("Using 'content' attribute")
        elif hasattr(zerox_output, 'output'):
            result = zerox_output.output
            print("Using 'output' attribute")
        elif isinstance(zerox_output, str):
            result = zerox_output
            print("Zerox output is already a string")
        else:
            # Try to convert to string
            result = str(zerox_output)
            print("Converted Zerox output to string")

        # Extract ingredients from the result
        ingredients_section = extract_ingredients(result)

        return ingredients_section
    except Exception as e:
        print(f"Error processing file with Zerox: {str(e)}")
        return f"Error: {str(e)}"

def extract_ingredients(text):
    """
    Extract and format the ingredients section from the OCR result
    """
    if not text or not isinstance(text, str):
        return "No valid text content found"

    # Print the raw text for debugging
    print("\nRaw OCR output:")
    print("---------------")
    print(text[:500] + "..." if len(text) > 500 else text)
    print("---------------\n")

    # Clean up the text - remove any markdown formatting
    text = re.sub(r'\*\*|\*|__|_|~~|`', '', text)

    # The model should already format the output as requested in the system prompt
    # But we can do additional processing if needed

    # Check if there's an INGREDIENTS section
    ingredients_match = re.search(r'INGREDIENTS:(.*?)(?:ALLERGEN INFORMATION:|$)', text, re.DOTALL | re.IGNORECASE)

    if not ingredients_match:
        # If no structured format is found, look for ingredient lists in other formats
        # Try to find a list of ingredients
        ingredients_alt = re.search(r'(?:ingredients|contains)[:;]\s*(.*?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)

        if ingredients_alt:
            ingredients_text = ingredients_alt.group(1).strip()
        else:
            # If still no match, return the whole text
            return "No clear ingredients section found. Full text:\n\n" + text
    else:
        ingredients_text = ingredients_match.group(1).strip()

    # Check for allergen information
    allergen_match = re.search(r'ALLERGEN INFORMATION:(.*?)$', text, re.DOTALL | re.IGNORECASE)

    # If no specific allergen section, look for common allergen statements
    if not allergen_match:
        allergen_alt = re.search(r'(?:contains|may contain|allergens)[:;]\s*(.*?)(?:\n\n|$)', text, re.DOTALL | re.IGNORECASE)
        allergen_text = allergen_alt.group(1).strip() if allergen_alt else ""
    else:
        allergen_text = allergen_match.group(1).strip()

    # Clean up the ingredients text
    # Convert bullet points to a clean list
    ingredients_list = []
    for line in ingredients_text.split('\n'):
        # Remove bullet points, dashes, and other list markers
        clean_line = re.sub(r'^\s*[-•*]\s*', '', line.strip())
        if clean_line:
            ingredients_list.append(clean_line)

    # Format the output
    formatted_output = "INGREDIENTS:\n"
    for ingredient in ingredients_list:
        formatted_output += f"- {ingredient}\n"

    if allergen_text:
        # Clean up allergen text
        allergen_list = []
        for line in allergen_text.split('\n'):
            clean_line = re.sub(r'^\s*[-•*]\s*', '', line.strip())
            if clean_line:
                allergen_list.append(clean_line)

        formatted_output += "\nALLERGEN INFORMATION:\n"
        for allergen in allergen_list:
            formatted_output += f"- {allergen}\n"

    return formatted_output

# Run the main function if this script is executed directly
if __name__ == "__main__":
    result = asyncio.run(main())
    print("\nEXTRACTED INGREDIENTS:")
    print("=======================")
    print(result)