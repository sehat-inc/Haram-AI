import os
from pathlib import Path
import re
from typing import Optional
from dotenv import load_dotenv
import img2pdf
from pyzerox import zerox
from PIL import Image


load_dotenv()

class OCRProcessor:
    def __init__(self):
        self.model = "gemini/gemini-2.0-flash"
        
        self.image_prompt = """
        You are an expert in identifying ingredient lists and grocery products. 
        Your task is to check if the image provided contains a grocery product label. 
        If it does, then output "YES".
        If it does not, then output "NO".
        """

        self.custom_system_prompt = """
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
        self.kwargs = {}

    async def process_image(self, file_path: str) -> Optional[str]:
        """
        Process an image file and extract ingredients information.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            str: Extracted ingredients information or error message
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File {file_path} not found")

            # Convert image to PDF if necessary
            if self._is_image_file(file_path):
                pdf_path = await self._convert_image_to_pdf(file_path)
                if not pdf_path:
                    raise Exception("Failed to convert image to PDF")
                file_path = pdf_path

            

            # Identifying if the image contains a grocery product label
            zerox_output_binary = await zerox(
                file_path=file_path,
                model=self.model,
                custom_system_prompt=self.image_prompt,
                select_pages=None,
                **self.kwargs
            )

            

            ifImage = self._extract_content(zerox_output_binary)
            if ifImage == "NO" or ifImage == "no" or ifImage == "No" or ifImage == "nO":
                
                return 'no'
            else:   

                
                # Process with Zerox
                zerox_output = await zerox(
                    file_path=file_path,
                    model=self.model,
                    custom_system_prompt=self.custom_system_prompt,
                    select_pages=None,
                    **self.kwargs
                )

                # Extract and format the content
                result = self._extract_content(zerox_output)
                ingredients = self._extract_ingredients(result)    
                
        
                # Cleanup temporary PDF if created
                if file_path.endswith('.pdf') and self._is_image_file(file_path[:-4]):
                    os.remove(file_path)
                    
                return ingredients

        except Exception as e:
            return f"Error processing image: {str(e)}"

    @staticmethod
    def _is_image_file(file_path: str) -> bool:
        """Check if the file is an image."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'}
        return Path(file_path).suffix.lower() in image_extensions

    async def _convert_image_to_pdf(self, image_path: str) -> Optional[str]:
        """Convert image to PDF format."""
        try:
            output_pdf = str(Path(image_path).with_suffix('.pdf'))
            
            with Image.open(image_path) as image:
                if image.mode == 'RGBA':
                    image = image.convert('RGB')
                
                with open(output_pdf, "wb") as f:
                    f.write(img2pdf.convert(image_path, rotation=img2pdf.Rotation.ifvalid))
                
            return output_pdf
        except Exception as e:
            raise Exception(f"Error converting image to PDF: {str(e)}")

    def _extract_content(self, zerox_output) -> str:
        """Extract content from Zerox output object."""
        if hasattr(zerox_output, 'pages') and zerox_output.pages:
            return zerox_output.pages[0].content if hasattr(zerox_output.pages[0], 'content') else str(zerox_output.pages[0])
        elif hasattr(zerox_output, 'markdown'):
            return zerox_output.markdown
        elif hasattr(zerox_output, 'text'):
            return zerox_output.text
        elif hasattr(zerox_output, 'content'):
            return zerox_output.content
        elif hasattr(zerox_output, 'output'):
            return zerox_output.output
        return str(zerox_output)

    def _extract_ingredients(self, text: str) -> str:
        """Extract and format ingredients information."""
        if not text or not isinstance(text, str):
            return "No valid text content found"

        # Clean up the text
        text = re.sub(r'\*\*|\*|__|_|~~|`', '', text)

        # Extract ingredients section
        ingredients_match = re.search(r'INGREDIENTS:(.*?)(?:ALLERGEN INFORMATION:|$)', text, re.DOTALL | re.IGNORECASE)
        ingredients_text = ingredients_match.group(1).strip() if ingredients_match else ""

        # Extract allergen information
        allergen_match = re.search(r'ALLERGEN INFORMATION:(.*?)$', text, re.DOTALL | re.IGNORECASE)
        allergen_text = allergen_match.group(1).strip() if allergen_match else ""

        # Format output
        output = "INGREDIENTS:\n"
        if ingredients_text:
            for line in ingredients_text.split('\n'):
                clean_line = re.sub(r'^\s*[-•*]\s*', '', line.strip())
                if clean_line:
                    output += f"- {clean_line}\n"
        else:
            output += "No ingredients found\n"

        if allergen_text:
            output += "\nALLERGEN INFORMATION:\n"
            for line in allergen_text.split('\n'):
                clean_line = re.sub(r'^\s*[-•*]\s*', '', line.strip())
                if clean_line:
                    output += f"- {clean_line}\n"

        return output.strip()
