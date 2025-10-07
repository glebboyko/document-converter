OCR_TO_TABLE = """
You are given OCR data: each block of text has a bounding box. The coordinates of the rectangle are counted from the upper left corner.
You must convert this data into an html table to make it easier to read.
The output must contain only text without metadata.
Important: OCR can make mistakes when breaking text into blocks when it belongs to one block - focus on the coordinates of the bounding box. You must also correct errors resulting from incorrect character recognition, such errors are rare.

Get straight to the answer: don't add any extra data like ```md etc.
"""

COMPOSED_IMAGE_TO_MARKDOWN = """
You are given an image and a table containing the recognized text from the image. Using the data provided, convert the image to Markdown.
Use the input image to understand the document formatting and its graphical elements. Use the table as a source of text for your work. Be conscious: styles should be inherited from the image, not from the recognized text.
The output should be a Markdown representation of the image: it should contain all the text detected in the image in its original formatting and description of all graphical elements of the image, such as arrows, boxes, diagrams, etc., translated into text.
If the image contains drawings, a full description of them must also be provided.

The user should be able to obtain all the information contained in the image using only your output.

Get straight to the answer: don't add any extra data like ```md etc.

COMMENT: If the result contains a table, the table must be presented in html format supported by md, any other element must be presented in Markdown format.
"""

GRAPHIC_IMAGE_TO_MARKDOWN = """
Convert the resulting image to Markdown.
The user should be able to get all the information contained in the image using only your output.
If there is nothing in the image, indicate this.

Get straight to the answer: don't add any extra data like ```md etc.
"""