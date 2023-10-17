from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QFileDialog, QLineEdit, QMessageBox, QApplication
from PyQt5.QtGui import QTextDocument, QTextCursor, QColor, QTextCharFormat
from PyQt5.QtCore import QSize, QTimer, QFileInfo
from ILX_translator_QT import Ui_ILX_translator_window
import pandas as pd
import re
import math


def messagebox(errortype, text, info):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(errortype)
    msg.setText(text)
    msg.setInformativeText(info)
    msg.exec()
    return None


class MyMainWindow(QMainWindow, Ui_ILX_translator_window):
    # Define the shared maximum_lineEdit_width as a class-level variable
    maximum_lineEdit_width = 500

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # self.label_text_over_500px.hide()
        # Creating callable layouts to add and delete lineEdits in
        self.layout_eng = QVBoxLayout(self.groupBox_eng_values)
        self.layout_trans = QVBoxLayout(self.groupBox_trans_values)

        # ---------------------------------------------------------------
        # ---------------------- SEARCHBAR METHODS ----------------------
        # ---------------------------------------------------------------

        # Timers makes sure that the Search Bar are not triggered when typed, but when the user has stopped typing
        # Allowing reduced resource/computing consumption
        self.search_timer_eng = QTimer(self, interval=1000)
        self.search_timer_eng.timeout.connect(self.search_and_highlight_eng)
        self.search_timer_trans = QTimer(self, interval=1000)
        self.search_timer_trans.timeout.connect(self.search_and_highlight_trans)

    def lineEdit_search_eng_changed(self):
        # Triggered when search bar above english html is changed.
        # Starts the respective timer.
        self.lineEdit_search_changed(self.search_timer_eng)

    def lineEdit_search_trans_changed(self):
        # Triggered when search bar above translated html is changed.
        # Starts the respective timer.
        self.lineEdit_search_changed(self.search_timer_trans)

    def lineEdit_search_changed(self, timer):
        # This method starts the timer,
        # in the __init__ the timeout connects to the respective search_and_highlight method
        timer.start()

    def search_and_highlight_eng(self):
        # On timer.timeout (interval set in __init__)
        # triggers the search_and_highlight method with the respective input (lineEdit) and output (textEdit)
        self.search_and_highlight(self.lineEdit_search_eng, self.textEdit_eng, self.search_timer_eng)

    def search_and_highlight_trans(self):
        # On timer.timeout (interval set in __init__)
        # triggers the search_and_highlight method with the respective input (lineEdit) and output (textEdit)
        self.search_and_highlight(self.lineEdit_search_trans, self.textEdit_trans, self.search_timer_trans)

    def search_and_highlight(self, lineEdit, textEdit, timer):
        """
        :param lineEdit: Searchbar for English and Translation
        :param textEdit: HTML textEdit for English and Translation
        :param timer:  Timeout timer for English and Translation searchbar
        :return: text within lineEdit (searchbar) is highlighted yellow in textEdit (html text)
        """
        timer.stop()
        words = lineEdit.text()  # Search bar text
        format = QTextCharFormat()
        format.setBackground(QColor("white"))
        cursor = textEdit.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.mergeCharFormat(format)

        if words:
            cursor = textEdit.document().find(words)
            format.setBackground(QColor("yellow"))
            while not cursor.isNull():
                cursor.mergeCharFormat(format)
                cursor = textEdit.document().find(words, cursor)

    # --------------------------------------------------------------
    # ---------------------- MENU BAR METHODS ----------------------
    # --------------------------------------------------------------
    def Save_html_triggered(self):
        # TODO: Except textEdit_eng is empty:
        filename, _ = QFileDialog.getSaveFileName(self, "Save html As", "",
                                                  "Hypertext Markup Language (*.htm *html);;"
                                                  "All files (*.*)")
        if filename:
            html = self.textEdit_eng.toHtml()
            with open(filename, 'w') as f:
                f.write(html)

    def Import_html_triggered(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open file", "",
                                                  "Hypertext Markup Language (*.htm *.html);;"
                                                  "All files (*.*)")
        if filename:
            with open(filename, 'r') as f:
                html = f.read()
            self.textEdit_eng.setText(html)
            basename = QFileInfo(filename).baseName()
            self.lineEdit_notification_template.setText(basename)

    # --------------------------------------------------------------------
    # ----------------------TRANSLATION TAB METHODS ----------------------
    # --------------------------------------------------------------------

    def delete_textEdits(self):
        """
        Called from:
        1) : textEdit_eng_changed > English HTML text is changed
        2) : button_clicked_import > Translation template file is imported
        :return: Clear previous LineEdits in both groupBox
        """
        for groupBox_layout in [self.layout_eng, self.layout_trans]:
            for i in reversed(range(groupBox_layout.count())):
                widget = groupBox_layout.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()

    def button_clicked_export(self):
        # TODO: error message when empty
        """
        Creates an Excel Translation template based on the lines of the html input
        This template is meant to be distributed to be translated
        Engine = openpyxl
        Therefore it:
        1): Creates Dictionary (english:translation) through self.create_dictionary() method
        2): Sets Default export name equal to the LineEdit above the tab widget
        3): Alters column width so the content fits in the cells
        :return:
        """
        translation_dict = self.create_dictionary(error=False)
        df = pd.DataFrame(data=translation_dict.items(), columns=["English", "Translation"])
        export_title = self.lineEdit_notification_template.text()

        filename = QFileDialog.getSaveFileName(self, 'Select File', export_title, filter='*.xlsx')
        if filename[0] == '':
            pass
        else:
            # Create an Excel writer and set the engine to 'openpyxl'
            excel_writer = pd.ExcelWriter(filename[0], engine='openpyxl')

            # Convert the DataFrame to an Excel sheet
            df.to_excel(excel_writer, sheet_name='Sheet1', index=False)

            # Access the openpyxl workbook and worksheet objects
            workbook = excel_writer.book
            worksheet = excel_writer.sheets['Sheet1']

            # Autofit columns
            for column in worksheet.columns:
                max_length = max(len(str(cell.value)) for cell in column)
                adjusted_width = (max_length + 2) * 1.2  # Add some buffer space
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            workbook.save(filename[0])

            # Close the Excel writer
            excel_writer.close()

    def button_clicked_import(self):
        """
        Opens Explorer with an Excel Filter
        - This functions imports the Translations from the "button_clicked_export" created template
        - uses pandas to convert Excel into DataFrame

        :return: Populates LineEdits in Translation tab
        """
        filename = QFileDialog.getOpenFileName(self, 'Open File', "", "Excel (*.xls *.xlsx)")
        if filename[0] == '':  # Does nothing when no file is passed
            pass
        else:
            df = pd.read_excel(filename[0])
            self.delete_textEdits()
            line_num = 1  # Unused counter, to check number of LineEdits created

            # self.label_text_over_500px.hide()
            for index, row in df.iterrows():
                eng_text = str(row["English"])
                trans_text = str(row["Translation"])

                text_edit_eng = AutoResizingLineEdit()  # Resizes LineEdits to contents
                text_edit_trans = AutoResizingLineEdit()

                text_edit_eng.setText(eng_text)  # Sets text of LineEdit to Excel content Column "English"
                text_edit_trans.setText(trans_text)

                # if text_edit_eng.width() > self.maximum_lineEdit_width:
                #     self.label_text_over_500px.show()

                self.layout_eng.addWidget(text_edit_eng)  # Adds LineEdit to QVBoxLayout (groupBox_eng_values)
                self.layout_trans.addWidget(text_edit_trans)
                line_num += 1

    # --------------------------------------------------------------
    # ---------------------- HTML TAB METHODS ----------------------
    # --------------------------------------------------------------
    def textEdit_html_eng_changed(self):
        """
        Method is triggered everytime the text within Self.textEdit_eng is changed.
        This textEdit is meant to give the Original (english) html
        Then it will:
        1): Convert the HTML into rich text
        2): Sets rich text in textEdit_eng_rich_text
        3): Recognize Line Breaks to create multiple LineEdits
        4): Remove spaces, and recognize text within {# and } (ILX field names)
        
        :return: 
        -Adds Rich text to English LineEdits
        -Adds ILX field text ({#[text]} to Translation LineEdits
        """""
        html = self.textEdit_eng.toPlainText()  # Convert HTML into Rich text
        self.textEdit_eng_rich_text.setHtml(html)  # Sets rich text in TextEdit
        document = QTextDocument()
        document.setHtml(html)
        rich_text_text = document.toPlainText()  # Get the rich_text HTML text without HTML tags

        # Split lines using re.split() with a pattern that matches different types of line breaks
        lines = re.split(r'[\r\n]', rich_text_text)
        self.delete_textEdits()

        line_num = 1
        # Add new LineEdit widgets to both groupBox and set text
        # self.label_text_over_500px.hide()
        for line in lines:
            line = line.strip()  # Remove leading and trailing spaces
            if line:
                # Regular expression pattern to match text within curly braces
                pattern = r'\{#.*?\}'

                # Find all matches within the line
                matches = re.findall(pattern, line)
                concatenated_values = ' '.join(matches)

                text_edit_eng = AutoResizingLineEdit()  # Create AutoResizingLineEdit instance
                text_edit_trans = AutoResizingLineEdit()  # Create AutoResizingLineEdit instance

                text_edit_eng.setText(line)  # Set text in AutoResizingLineEdit
                text_edit_trans.setText(concatenated_values)  # Set text in AutoResizingLineEdit

                # if text_edit_eng.width() > 499:
                #     self.label_text_over_500px.show()

                self.layout_eng.addWidget(text_edit_eng)  # Add AutoResizingLineEdit to layout
                self.layout_trans.addWidget(text_edit_trans)  # Add AutoResizingLineEdit to layout
                line_num += 1

    def textEdit_html_trans_changed(self):
        """
        Converts translated html into Rich text
        This textEdit allows easy comparison with original,
        and quickly validates if the translation went well
        :return:  Translated Rich text in textEdit_trans_rich_text
        """
        html = self.textEdit_trans.toPlainText()
        self.textEdit_trans_rich_text.setHtml(html)

    # -----------------------------------------------------------------------------
    # ---------------------- REPLACEMENT/TRANSLATION METHODS ----------------------
    # -----------------------------------------------------------------------------
    def create_dictionary(self, error):
        """
        Creates a python Dictionary based from LineEdits in Translation tab.
        Key = English
        [Value] = Translated
        :return: Dictionary { English : Translation }
        """
        translation_dict = {}
        for i in range(self.layout_eng.count()):
            text_edit_eng = self.layout_eng.itemAt(i).widget()
            text_edit_trans = self.layout_trans.itemAt(i).widget()

            if text_edit_eng and text_edit_trans:  # Additional check, to see if both items/objects exist
                eng_text = text_edit_eng.text()
                trans_text = text_edit_trans.text()
                if trans_text == "" and error:
                    errortype = "Missing Translation"
                    text = "Warning: Missing Translation"
                    info = "In the Translation tab an English value has not been translated.\n" \
                           "However, you can still proceed, the value will be replaced by a blank."
                    messagebox(errortype, text, info)
                    error = False

                translation_dict[eng_text] = trans_text

        return translation_dict

    def button_clicked_generate(self):
        # TODO: error message when html eng is empty
        """
        Method which replaces the english text with the translation text
        :return: Creates the translated html and populates in self.textEdit_trans
        """
        html = self.textEdit_eng.toPlainText()
        cleaned_html = re.sub(' +', ' ', html)  # Removes duplicate/multiple spaces from original html
        translation_dict = self.create_dictionary(error=True)

        for old_text, new_text in translation_dict.items():
            # Remove extra whitespace and handle case insensitivity
            clean_old_text = old_text.strip()
            pattern = re.compile(re.escape(clean_old_text), re.IGNORECASE | re.DOTALL)

            # Find and skip content between {# and }
            def replace(match):
                if match.group(0).startswith("{#") and match.group(0).endswith("}"):
                    return match.group(0)  # Skip the matched content
                return new_text

            cleaned_html = re.sub(pattern, replace, cleaned_html, count=1)

        self.textEdit_trans.setPlainText(cleaned_html)

    def aboutQT(self):
        msg = QApplication.aboutQt()

    def aboutProgram(self):
        title = "About this Program"

        text = """<html> <p> 
        This program has been designed to reduce Translation efforts for Intelex Notification 
        templates. The program replaces the english text in the HTML code of the Notification Template with the 
        provided translated text, without affecting the Intelex Fields. The html code of each notification can be 
        found in the Application Translation tab with the ID. <br> <br> The program converts HTMl text into Rich text 
        and creates a line-by-line Excel translation template to be send to the translator. The translated template 
        can be imported, and generate the translated HTML code. Subsequently, this code can be copied into the 
        Application Translation export and imported into Intelex. <br> <br> The Intelex html replacer is a Python 
        based GUI developed with PyQT. Arcadis 2023 </p> </html> """

        msg = QMessageBox()
        # msg.setIconPixmap(QPixmap(":/images/Arcadis_logo.ico"))
        msg.setWindowTitle(title)
        msg.setText(text)

        msg.exec()

    def instructions(self):
        title = "How to use this Program"
        text = """\
                    <html>
                    <p>
                    <b>1: Find the desired e-mail template in the respective Application Translation Excel export </b><br>
                    In the Application Translate export you can find email template through the RecordID (GUID)
                    You can find this ID either through Inspect, or by creating a Report in Intelex.
                    Note: it doesnt matter which language you export. <br>
                    <b>2: Check the English html and rich text formatting. </b><br>
                    We want to achieve uniform formatting throughout all cultures. 
                    Therefore, you should first double check if the English html has the desired rich text output. 
                    You can correct it in the notification template (html editor). 
                    Be Aware that you have to press "Extract" again in the Application Translate tab. 
                    Or you can change the rich text by editing the html code. 
                    Be Aware that this should be compatible with the html editor within Notification templates. <br>
                    <b>3: Copy html of "English Value" into "Html English" box within the ILX html replacer application </b><br>
                    If the English notification looks correct in Intelex, you can copy the html code into the "html english" box within the "HTML Replacer" tab.
                    You can doulbe-check the output in the "Rich Text - English" tab below.
                    Note: Added pictures will not appear correct in the program. However, it will on Intelex.
                    To make it easier later, you can save this HTML message through the menu bar. <br>
                    <b>4: Export Translation template </b><br>
                    In the "Translation" tab you can check the export template.
                    Subsequently, with "Export Translation Template" you can export this template as an Excel file.
                    The default name can be specified in "Notification Template" text box. <br>
                    <b>5: Send the Excel notification template to the translator </b><br>
                    Translators should only add text in "Translation" column and not edit the {#fieldname} text. 
                    Also ask the translator to translate the "Subject Title" (in Intelex export with identical ID) <br>
                    <b>6: Re-open programm upon receiving all translation of a single notification template </b><br>
                    Open or copy the English html text again in the "html - english" textbox again.
                    Press "Import Translation Template" and select the desired translated Excel template.
                    Head over to the "Translation" to check the translations. <br>
                    <b>7: Generate Translated HTML text </b><br>
                    Press "Generate HTML". You can check the output in the "Rich text - Translated" box. <br>
                    <b>8: Copy HTMl into Intelex Import Export excel file </b><br>
                    In the Excel export file from which we retrieved the html text,
                    copy the generated translated html into the according "Translated Value" column.
                    Change the "Locale" to the translated culture. <br>
                    <b>9: Repeat translation for other languages. </b><br>
                    Copy the row into the next line and repeat step 6 to 8 for the other languages. <br>
                    <b>10: Import the Excel file into Intelex </b><br>
                    Through Application translation import the Excel file with the multiple HTML translations.
                    Press "Apply" and test if you translations are applied. <br>
                    <br>
                    <b>NOTE: The Notification subject title is described in another row (same key id) </b>
                    </p>
                    </html>
                    """

        msg = QMessageBox()
        # msg.setIconPixmap(QPixmap(":/images/Arcadis_logo.ico"))
        msg.setWindowTitle(title)
        msg.setText(text)

        msg.exec()


class AutoResizingLineEdit(QLineEdit):
    """
    This class Autoresizes the LineEdits in the Translations tab.
    It uses FontMetrics and SizeHint to calculate the Width and Height of each LineEdit, respectively.
    """
    # Use the shared maximum_lineEdit_width from MyMainWindow
    maximum_lineEdit_width = MyMainWindow.maximum_lineEdit_width

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setMinimumHeight(20)  # Set a minimum height
        self.setMaximumWidth(self.maximum_lineEdit_width - 2)
        # Set maximum size 2 below maximum size LineEdit,
        # keeps sizing sortoff equal while allowing error label to popup
        self.textChanged.connect(self.updateSize)

    def sizeHint(self):
        """
        Calculates the height of the LineEdit based on the Font characteristics
        :return: In px, the minimal width and height to fit its content.
        """
        size_hint = super().sizeHint()
        content_height = self.fontMetrics().height() + 6  # Add some padding
        max_size = QSize(self.maximumWidth(), content_height)
        return size_hint.expandedTo(self.minimumSizeHint()).boundedTo(max_size)

    def updateSize(self):
        """
        called from the __init__
        just uses fontMetrics to calculate the minimum width and height of each LineEdit to fit its contents.
        :return:
        """
        content_width = self.fontMetrics().width(self.text()) + 12  # Add some padding

        if content_width > self.maximum_lineEdit_width:
            content_width = self.maximum_lineEdit_width
            self.setStyleSheet("background-color: lightyellow;")
        else:
            self.setStyleSheet("")
        content_height = self.fontMetrics().height() + 6  # Add some padding
        self.setMinimumWidth(content_width)
        self.setMinimumHeight(content_height)
