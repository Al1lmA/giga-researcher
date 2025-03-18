from io import BytesIO
import docx
from docx import Document
from loguru import logger
from pptx import Presentation
import pandas as pd
from pptx.dml.color import RGBColor
from pptx.util import Pt, Inches
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
import re
import math
import numpy

    # Константы для позиционирования текста на слайде
TEXT_BOX_LEFT = Inches(0.5)
TEXT_BOX_TOP = Inches(1)
TEXT_BOX_WIDTH = Inches(6.7)
TEXT_BOX_HEIGHT = Inches(2)
TEXT_FONT_SIZE = Pt(14)
TEXT_FONT_NAME = "SB Sans Display"

class Company():
    """This is a class for the company"""
    
    def __init__(self, inn) -> None:
        self.resources = [] #источники
        self.org_name = '' #название компании
        self.text_o_kompanii = ''
        self.holders = ''
        self.products = ''
        self.inn = inn
        self.filename=f'data/{self.inn}/{self.inn}.pdf'
        self.report = ''  
        self.card = {}
        self.table = pd.DataFrame()
        self.graph = ''
        self.team = ''
        self.feedback = ''
        self.customers = ''
        self.competitors = ''
        self.trends = ''
        self.bm = ''
        self.invest = ''
        self.infra = ''
        self.conclusion = ''
        self.summ = ''

    def combine_texts(self):
        """Соединяет текстовые атрибуты в 1 строку"""
        components = [
            self.text_o_kompanii,
            self.holders,
            self.products,
            self.team,
            self.feedback,
            self.customers,
            self.competitors,
            self.trends,
            self.bm,
            self.invest,
            self.infra
        ]
        
        # Соединяем все компоненты в один текст, разделяя их пустой строкой для удобства чтения
        combined_text = "\n\n".join(filter(None, components))
        return combined_text

    def split_text(self, text, max_length=115):
        """
        Разбивает длинную строку на части по заданной максимальной длине, сохраняя абзацы и переносы строк.
        
        Args:
            text (str): Исходная длинная строка.
            max_length (int): Максимальная длина каждой части (по умолчанию 120 символов).
            
        Returns:
            list: Список частей строки.
        """
        parts = []
        parts = text.split('\n')
        # for paragraph in text.split('\n'):
        #     # parts.extend(textwrap.wrap(paragraph, width=max_length))
        #     wrapped_paragraph = textwrap.wrap(paragraph, width=max_length, drop_whitespace=False, tabsize=1)
        #     parts.extend(wrapped_paragraph)
        return parts

    async def add_text(self, prs, title, text):
        try:
            # Создаем новый слайд
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = title

            # Создаем текстовый блок
            text_box = slide.shapes.add_textbox(TEXT_BOX_LEFT, TEXT_BOX_TOP, TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT)
            text_frame = text_box.text_frame
            text_frame.word_wrap = True
            text_frame.paragraphs[0].font.size = TEXT_FONT_SIZE
            text_frame.paragraphs[0].font.name = TEXT_FONT_NAME
            text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT  # Выравнивание текста по левому краю

            # Разбиваем текст на строки и добавляем их в текстовый блок
            text_lines = text.split('\n') # self.split_text(text)
            
            current_slide = slide
            current_text_frame = text_frame
            

            pattern = r'\*\*(.*?)\*\*'

            for line in text_lines:
                if len(current_text_frame.paragraphs) >= 6:  # Максимальное количество абзацев в текстовом блоке
                    total_characters = sum(len(paragraph.text) for paragraph in current_text_frame.paragraphs)

                    if total_characters + len(line) > 1000: # Максимальное количество символов на слайде
                        # Если текст не помещается в текстовый блок, создаем новый слайд
                        current_slide = prs.slides.add_slide(prs.slide_layouts[1])
                        current_text_frame = current_slide.shapes.add_textbox(TEXT_BOX_LEFT, TEXT_BOX_TOP, TEXT_BOX_WIDTH, TEXT_BOX_HEIGHT).text_frame
                        current_text_frame.word_wrap = True
                        current_text_frame.paragraphs[0].font.size = TEXT_FONT_SIZE
                        current_text_frame.paragraphs[0].font.name = TEXT_FONT_NAME
                        current_text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT

                if line.startswith('#'):
                    # Добавляем заголовок
                    p = current_text_frame.add_paragraph()
                    p.text = line.replace('#', '').strip()
                    p.font.bold = True
                    p.font.size = TEXT_FONT_SIZE
                    p.font.name = TEXT_FONT_NAME
                
                else:
                    # Добавляем обычный текст
                    p = current_text_frame.add_paragraph()
                    p.font.size = TEXT_FONT_SIZE
                    p.font.name = TEXT_FONT_NAME
                    match = re.search(pattern, line)
                    if re.match(r'^\d+\.', line) or match:
                        # Если строка соответствует регулярному выражению или является нумерованным списком, добавляем ее жирным
                        text_list = line.split(':')
                        if text_list.__len__() == 1:
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

    async def make_pptx(self):
        """
        Формирование документа в формате pptx, по заданному шаблону.

        Структура:

        Executive summary  
        О компании  
        Анализ владения  
        Финансовые показатели   
        Бизнес-модель  
        Инвестиции 
        Ключевые клиенты 
        Продукты  
        ИТ-Инфраструктура  
        Оценка рынка и конкурентов  
        Оценка команды  
        Заключение  
        Источники  """

        # Путь к загруженному шаблону
        template_path = 'modules/template.pptx'
        # Создание нового документа на основе шаблона
        prs = Presentation(template_path)

        # Заполнение карточки компании
        slide = prs.slides[0] 
        table = slide.shapes[1].table  

        slide.shapes[0].text = f'Карточка компании\x0b«{self.org_name}»'
        title_text_frame = slide.shapes[0].text_frame
        title_text_frame.paragraphs[0].font.name = TEXT_FONT_NAME  # Задание шрифта "SB Sans Display"
        title_text_frame.paragraphs[0].font.bold = True  # Жирный шрифт
        title_text_frame.paragraphs[0].font.size = Pt(30)  # Размер шрифта 
        title_text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)  # Цвет шрифта 

        data = self.card
        for row in table.rows:
            try:
                key = row.cells[0].text
                if key == 'Год основания компании':
                    # Проверяем наличие ключа в data
                    if 'Год основания компании' in data:
                        row.cells[1].text = str(data['Год основания компании'])
                    elif 'Дата регистрации компании' in data:
                        # Меняем текст на 'Дата регистрации компании' и заполняем значение
                        row.cells[0].text = 'Дата регистрации компании'
                        row.cells[0].text_frame.paragraphs[0].font.size = Pt(11)
                        row.cells[0].text_frame.paragraphs[0].font.bold = True
                        row.cells[0].text_frame.paragraphs[0].font.name = "SB Sans Display Semibold"
                        row.cells[1].text = str(data['Дата регистрации компании'])
                else:
                        row.cells[1].text = str(data[str(key)])
                    
            except Exception as er:
                    logger.error(er)
                    row.cells[1].text = 'n/a'

            row.cells[1].text_frame.paragraphs[0].font.size = Pt(11)
            row.cells[0].text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
            row.cells[1].text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)

        
        # Добавление раздела "Executive summary"
        prs = await self.add_text(title='1 Executive summary', prs=prs, text=self.summ)
        
        # Добавление раздела "О компании"
        
        prs = await self.add_text(title='2. О компании', prs=prs, text=self.text_o_kompanii)
        

        # Добавление раздела "Анализ владения"
        prs = await self.add_text(title='2.1 Анализ владения', prs=prs, text=self.holders)

        try:
            # Добавление раздела "Финансовые показатели"
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = '2.2 Финансовые показатели'

            # 'Финансовые показатели'
            try:
                df = self.table
                left_inch, top_inch, width_inch, height_inch = Inches(0.3), Inches(1), Inches(6.8), Inches(4)
                new_table = slide.shapes.add_table(df.shape[0]+1, df.shape[1], left_inch, top_inch, width_inch, height_inch).table

                # Заполнение заголовков новой таблицы
                for col_num, column in enumerate(df.columns):
                    cell = new_table.cell(0, col_num)
                    cell.text = column
                    for paragraph in cell.text_frame.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(13)
                            run.font.name = TEXT_FONT_NAME
                # Заполнение данных из датафрейма в новую таблицу
                for row_num in range(df.shape[0]):
                    for col_num in range(df.shape[1]):
                        value = df.iloc[row_num, col_num]
                        cell = new_table.cell(row_num+1, col_num)
                        if isinstance(value, (int, float, numpy.int64)):
                            if math.isnan(value):
                                cell.text = '-'
                            else:
                                cell.text = "{:,.0f} тыс. ₽".format(value)
                        else:
                            cell.text = str(value)
                        for paragraph in cell.text_frame.paragraphs:
                            paragraph.alignment = PP_ALIGN.CENTER
                            for run in paragraph.runs:
                                run.font.size = Pt(11)
                                run.font.name = TEXT_FONT_NAME
                # Установка ширины столбцов
                try:
                    new_table.columns[0].width = Inches(0.6) 
                    new_table.columns[1].width = Inches(1.3)
                    new_table.columns[2].width = Inches(1.5)
                    new_table.columns[3].width = Inches(1.7)
                    
                    new_table.columns[4].width = Inches(1.7)  
                except Exception as er:
                    logger.error(er)        
            except Exception as er:
                logger.error(er)
            try:
                # Добавление рисунка на слайд из BytesIO
                img_data = BytesIO(self.graph)  # Здесь должны быть данные изображения в формате BytesIO
                img = slide.shapes.add_picture(img_data, Inches(0.5), Inches(6), width=Inches(6.8), height=Inches(4))
            except Exception as er:
                logger.error(er)
        except Exception as er:
            logger.error(er)

        # Добавление раздела "Бизнес-модель"
        prs = await self.add_text(title='2.3 Бизнес-модель', prs=prs, text=self.bm)


        # Добавление раздела "Инвестиции"
        prs = await self.add_text(title='2.4 Инвестиции', prs=prs, text=self.invest)

        # Добавление раздела "Ключевые клиенты"
        prs = await self.add_text(title='2.5 Ключевые клиенты', prs=prs, text=self.customers)

        # Добавление раздела "Продукты"
        prs = await self.add_text(title='2.6 Продукты', prs=prs, text=self.products)


        # Добавление раздела "ИТ-Инфраструктура"
        prs = await self.add_text(title='2.7 ИТ-Инфраструктура', prs=prs, text=self.infra)


        # Добавление раздела "Оценка рынка и конкурентов"
        prs = await self.add_text(title='3 Оценка рынка и конкурентов', prs=prs, text=self.competitors)

        # Добавление раздела "Оценка команды"
        prs = await self.add_text(title='4 Оценка команды', prs=prs, text=self.team)

        # Добавление раздела "Заключение"
        prs = await self.add_text(title='5 Заключение', prs=prs, text=self.conclusion)

        # Добавление раздела "Источники"
        # slide = prs.slides.add_slide(prs.slide_layouts[1])
        # slide.shapes.title.text = '12. Источники'
        # text_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(2))
        # text_frame = text_box.text_frame
        # p = text_frame.add_paragraph()
        # p.text = 'Текст об источниках'

        # Сохранение созданной презентации
        pptx_path = f"/home/TIsAmbrosyeva/giga_researcher/outputs/{self.org_name}.pptx"
        prs.save(pptx_path)
              
        
        return pptx_path
    


    
    async def make_doc(self):
        try:
            doc = Document()

            doc.add_heading(self.org_name, 0)

            doc.add_heading('Карточка компании', 1)
            table = doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid' 
            for o in self.card:
                row_cells = table.add_row().cells
                row_cells[0].text = o
                row_cells[1].text = self.card[o]

        except Exception as er:
            logger.error(er)

        try:
            doc.add_heading('О компании', 1)
            doc.add_paragraph(self.text_o_kompanii)
        except Exception as er:
            logger.error(er)

        try:
            doc.add_heading('Финансовые показатели', 1)
            t = doc.add_table(self.table.shape[0]+1, self.table.shape[1])

            for j in range(self.table.shape[-1]):
                t.cell(0,j).text = self.table.columns[j]

            for i in range(self.table.shape[0]):
                for j in range(self.table.shape[-1]):
                    t.cell(i+1,j).text = str(self.table.values[i,j])

            buffer = BytesIO(self.graph)
            doc.add_picture(buffer, width = docx.shared.Cm(17))
        except Exception as er:
            logger.error(er)
        
        try:
            doc.add_heading('Продукты и услуги', 1)
            doc.add_paragraph(self.products)
        except Exception as er:
            logger.error(er)
        
        try:
            doc.add_heading('Клиенты', 1)
            doc.add_paragraph(self.customers)
        except Exception as er:
            logger.error(er)
        
        try:
            doc.add_heading('Отзывы', 1)
            doc.add_paragraph(self.feedback)
        except Exception as er:
            logger.error(er)

        try:
            doc.add_heading('Вакансии', 1)
            doc.add_paragraph(self.team)
        except Exception as er:
            logger.error(er)

        try:
            doc.add_heading('Конкуренты', 1)
            doc.add_paragraph(self.competitors)
        except Exception as er:
            logger.error(er)

        try:
            doc.add_heading('Тренды', 1)
            doc.add_paragraph(self.trends)
        except Exception as er:
            logger.error(er)
        
        # doc.add_heading('Источники', 1)
        # doc.add_paragraph("\n".join(self.resources))
        
        try:  
            path = f'data/{self.inn}/{self.org_name}.docx'
            doc.save(path)
            logger.info(f"Отчет сохранен. Путь: {path}")
        except Exception as er:
            logger.error(er)
            doc.save(f'{self.inn}.docx')
            logger.info(f"Отчет сохранен. Путь: {self.inn}.docx")

