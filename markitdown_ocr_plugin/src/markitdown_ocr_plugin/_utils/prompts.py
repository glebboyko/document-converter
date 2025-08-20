OCR_TO_TABLE = """
You are given OCR data: each block of text has a bounding box. The coordinates of the rectangle are counted from the upper left corner.
You must convert this data into an html table to make it easier to read.
The output must contain only text without metadata.
Important: OCR can make mistakes when breaking text into blocks when it belongs to one block - focus on the coordinates of the bounding box. You must also correct errors resulting from incorrect character recognition, such errors are rare.
"""

COMPOSED_IMAGE_TO_MARKDOWN = """
You are given an image and a table containing the recognized text from the image. Using the data provided, convert the image to Markdown.
Use the input image to understand the document formatting and its graphical elements. Use the table as a source of text for your work.
The output should be a Markdown representation of the image: it should contain all the text detected in the image in its original formatting with graphical elements of the image, such as arrows, boxes, diagrams, etc., translated into text.
The user should be able to obtain all the information contained in the image using only your output.

COMMENT: Tables must be presented in html format
"""

GRAPHIC_IMAGE_TO_MARKDOWN = """
Convert the resulting image to Markdown.
The user should be able to get all the information contained in the image using only your output.
"""