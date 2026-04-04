OCR_TO_TABLE = """
You are given OCR data: each block of text has a bounding box. The coordinates of the rectangle are counted from the upper left corner.
You must convert this data into an html table to make it easier to read.
The output must contain only text without metadata.
Important: OCR can make mistakes when breaking text into blocks when it belongs to one block - focus on the coordinates of the bounding box. You must also correct errors resulting from incorrect character recognition, such errors are rare.

Get straight to the answer: don't add any extra data like ```md etc.
"""

COMPOSED_IMAGE_TO_MARKDOWN = """
You are given an image and a table containing the recognized text from the image. Using the data provided, convert the image to Markdown.
Use the input image to understand the document formatting and its graphical elements. Use the table as a source of text for your work. Be conscious: styles should be inherited from the image, not from the recognized text. You may use any Markdown syntax: headings, paragraphs, boldness, italic, blockquotes, lists, code blocks, etc. 
The output should be a Markdown representation of the image: it should contain all the text detected in the image in its original formatting and description of all graphical elements of the image, such as arrows, boxes, diagrams, etc., translated into text.
If the image contains drawings, a full description of them must also be provided.

The user should be able to obtain all the information contained in the image using only your output.

Get straight to the answer: don't add any extra data like ```md etc.

## Tables
Do not add tables if the source image may be represented without it. For example, if you received the document with header that contain some data horizontally (author -> title -> date), it can be represented without tables:
```
# Title
_$autor_
_$date_

...
```
Table should be added to the result only if the source image contains it. The table must be presented in html format supported by md, any other element must be presented in Markdown format. 
"""

GRAPHIC_IMAGE_TO_MARKDOWN = """
Convert the resulting image to Markdown.
The user should be able to get all the information contained in the image using only your output.
If there is nothing in the image, indicate this.

Get straight to the answer: don't add any extra data like ```md etc.
"""

MERGE_SEGMENTED_IMAGE_TO_MARKDOWN = """
You are given:
1. The full source image.
2. Recognition artifacts produced for multiple overlapping 2000x2000 image chunks. Each artifact contains the chunk coordinates, whether OCR text was found, the OCR-derived text table if available, and the Markdown generated for that chunk.

Your task is to produce one final Markdown representation for the full source image.

Rules:
- Use the full image to recover the global reading order, full-page layout, and relationships between distant elements.
- Use the chunk artifacts as hints for text and local details.
- The chunks overlap, so the artifacts may contain duplicates. You must deduplicate repeated content and merge partial fragments into complete text.
- Preserve the original document structure and formatting in Markdown.
- If the source image contains a real table, render it as HTML supported by Markdown. Otherwise prefer normal Markdown structure.
- Include descriptions of meaningful graphics, diagrams, arrows, callouts, and other visual elements.
- Do not mention the chunking process or the artifacts in the output.

The user should be able to obtain all information from the source image using only your output.

Get straight to the answer: don't add any extra data like ```md etc.
"""