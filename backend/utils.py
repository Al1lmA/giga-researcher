import aiofiles
import urllib
import uuid
from md2pdf.core import md2pdf
import os
import subprocess

async def convert_pptx_to_pdf(input_file, output_dir):
    """ Конвертация PPTX в PDF программой LibreOffice """

    try:
        if not os.path.exists("/usr/bin/libreoffice"):
            raise Exception("Установите LibreOffice")

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + ".pdf")
        subprocess.run(["/usr/bin/libreoffice", "--headless", "--convert-to", "pdf", input_file, "--outdir", output_dir], check=True)
        
        print(f"PPTX конверитирован в PDF: {output_file}")
    except Exception as e:
        print(f"Ошибка конвертации PPTX в PDF: {e}")

    return output_file


async def write_to_file(filename: str, text: str) -> None:
    """Запись текста в файл в кодировке UTF-8."""

    text_utf8 = text.encode('utf-8', errors='replace').decode('utf-8')

    async with aiofiles.open(filename, "w", encoding='utf-8') as file:
        await file.write(text_utf8)

async def write_md_to_pdf(text: str) -> str:
    """Конвертация Markdown в PDF """

    task = uuid.uuid4().hex
    file_path = f"/qcheck/giga_researcher/outputs/{task}"
    await write_to_file(f"{file_path}.md", text)

    try:
        md2pdf(f"{file_path}.pdf",
               md_content=None,
               md_file_path=f"{file_path}.md",
               css_file_path=None,
               base_url=None)

        print(f"Отчет сохранен {file_path}.pdf")
    except Exception as e:
        print(f"Ошибка конвертации: {e}")
        return ""

    encoded_file_path = urllib.parse.quote(f"{file_path}.pdf".replace('/qcheck/giga_researcher/', ''))
    return encoded_file_path
