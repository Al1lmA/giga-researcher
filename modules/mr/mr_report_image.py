from loguru import logger
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt, Inches
import re
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import asyncio
from datetime import datetime
import locale
locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))
from loguru import logger
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt, Inches
import re
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import asyncio
from datetime import datetime
import locale
import base64

locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))

# Константы для позиционирования текста на слайде
TEXT_BOX_LEFT = Inches(0.5)
TEXT_BOX_TOP = Inches(0.5)
TEXT_BOX_WIDTH = Inches(11)  # Изменяем ширину для текста
TEXT_BOX_HEIGHT = Inches(2)

TEXT_WITH_MAGE_BOX_WIDTH = Inches(5.5)
IMAGE_LEFT = Inches(7)  # Позиция для изображения
IMAGE_TOP = Inches(1)
IMAGE_WIDTH = Inches(5.5)
IMAGE_HEIGHT = Inches(4.5)
URL_FONT_SIZE = Pt(11)

TEXT_FONT_SIZE = Pt(14)
TEXT_FONT_NAME = "SB Sans Display"
SOURCES_FONT_SIZE = Pt(11)


def add_footer_date(prs, slide):
	"""Добавляет текущую дату в нижний колонтитул слайда."""
	date_shape = slide.shapes.add_textbox(0, prs.slide_height - Pt(30), prs.slide_width, Pt(30))
	date_frame = date_shape.text_frame
	date_frame.text = datetime.now().strftime("%d-%m-%Y")
	date_frame.paragraphs[0].font.size = Pt(11)  
	date_frame.paragraphs[0].font.color.rgb = RGBColor(111, 193, 178)
	date_frame.paragraphs[0].font.bold = True  
	date_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

async def add_text(prs, title, text, image=None, url=None):
	try:
		# Создаем новый слайд разделитель
		title_slide = prs.slides.add_slide(prs.slide_layouts[1])
		title_shape = title_slide.shapes.title
		title_shape.text = title
		title_shape.text_frame.paragraphs[0].font.size = Pt(60)
		title_shape.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

		# Создаем текстовый блок
		text_slide_layout = prs.slide_layouts[2]
		text_slide = prs.slides.add_slide(text_slide_layout)

		if image:
			# Если изображение передано, добавляем его на слайд
			image_data = base64.b64decode(image)
			with open("temp_image.jpg", "wb") as f:
				f.write(image_data)

			slide_image = text_slide.shapes.add_picture("temp_image.jpg", IMAGE_LEFT, IMAGE_TOP, IMAGE_WIDTH, IMAGE_HEIGHT)

			# Создаем текстовый блок слева от изображения
			text_box = text_slide.shapes.add_textbox(TEXT_BOX_LEFT, TEXT_BOX_TOP, TEXT_WITH_MAGE_BOX_WIDTH, TEXT_BOX_HEIGHT)
			is_first_slide = True  # Флаг для отслеживания первого слайда
		# Добавляем URL под изображением (если предоставлен)
		if url:
			url_box = text_slide.shapes.add_textbox(IMAGE_LEFT, IMAGE_TOP + IMAGE_HEIGHT + Inches(0.1), IMAGE_WIDTH, Pt(20))
			url_frame = url_box.text_frame
			url_frame.word_wrap = True
			
			p_url = url_frame.add_paragraph()		
			run_link = p_url.add_run()
			run_link.text = str(url)  # Преобразуем значение в строку для отображения
			run_link.font.size = URL_FONT_SIZE
			run_link.hyperlink.address = str(url)


		
		else:
			# Если изображения нет, создаем текстовый блок на весь слайд
			text_box = text_slide.shapes.add_textbox(TEXT_BOX_LEFT, TEXT_BOX_TOP, TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT)

		text_frame = text_box.text_frame
		text_frame.word_wrap = True
		text_frame.paragraphs[0].font.size = TEXT_FONT_SIZE
		text_frame.paragraphs[0].font.name = TEXT_FONT_NAME
		text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT  # Выравнивание текста по левому краю

		add_footer_date(prs, text_slide)

		# Разбиваем текст на строки и добавляем их в текстовый блок
		text_lines = text.split('\n')
		
		current_slide = text_slide
		current_text_frame = text_frame
		
		pattern = r'\*\*(.*?)\*\*'

				

		for line in text_lines:
			if len(current_text_frame.paragraphs) >= 6:  # Максимальное количество абзацев в текстовом блоке
				total_characters = sum(len(paragraph.text) for paragraph in current_text_frame.paragraphs)

				if is_first_slide and total_characters + len(line) > 600:  # Проверка для первого слайда
					current_slide = prs.slides.add_slide(prs.slide_layouts[2])
					current_text_frame = current_slide.shapes.add_textbox(TEXT_BOX_LEFT, TEXT_BOX_TOP, TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT).text_frame
					current_text_frame.word_wrap = True
					current_text_frame.paragraphs[0].font.size = TEXT_FONT_SIZE
					current_text_frame.paragraphs[0].font.name = TEXT_FONT_NAME
					current_text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
					
					is_first_slide = False  # Устанавливаем флаг в False после первого слайда

				elif not is_first_slide and total_characters + len(line) > 1000:  # Максимальное количество символов на остальных слайдах
					current_slide = prs.slides.add_slide(prs.slide_layouts[2])
					current_text_frame = current_slide.shapes.add_textbox(TEXT_BOX_LEFT, TEXT_BOX_TOP, TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT).text_frame
					current_text_frame.word_wrap = True
					current_text_frame.paragraphs[0].font.size = TEXT_FONT_SIZE
					current_text_frame.paragraphs[0].font.name = TEXT_FONT_NAME
					current_text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT

			add_footer_date(prs, current_slide)

			if line.startswith('#'):
				p = current_text_frame.add_paragraph()
				p.text = line.replace('#', '').strip()
				p.font.bold = True
				p.font.size = TEXT_FONT_SIZE
				p.font.name = TEXT_FONT_NAME
			
			else:
				p = current_text_frame.add_paragraph()
				p.font.size = TEXT_FONT_SIZE
				p.font.name = TEXT_FONT_NAME
				
				match = re.search(pattern, line)
				if re.match(r'^\d+\.', line) or match:
					text_list = line.split(':')
					if len(text_list) == 1:
						text_list = line.split('-')
					p.text = text_list[0].replace('*', '').strip()
					p.level = 1
					p.font.bold = True
					
					for i, item in enumerate(text_list[1:], start=2):
						p = current_text_frame.add_paragraph()
						p.text = item.replace('*', '').strip()
						p.font.size = TEXT_FONT_SIZE
						p.font.name = TEXT_FONT_NAME
				
				else:
					p.text = line.strip()			
	except Exception as err:
		logger.error(f"Ошибка при добавлении текста: {err}")
	return prs


async def make_mr_images_pptx(task, qna_list):
	template_path = 'modules/mr/Market_Research_2.pptx'
	prs = Presentation(template_path)

	slide = prs.slides[0] 
	slide.shapes.title.text = f'{task}'.upper()
	slide.shapes.title.text_frame.paragraphs[0].font.size = Pt(70)

	for qna in qna_list:
		for question, answer in qna.items():
			prs = await add_text(title=question, prs=prs, text=answer[0], image=answer[1], url=answer[2])

	pptx_path = f"/home/TIsAmbrosyeva/giga_researcher/outputs/mr/{task}.pptx"
	prs.save(pptx_path)

	return pptx_path