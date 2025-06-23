# Odoo Passport Reader

This repository contains a sample Odoo 17 module `passport_reader` which can
read passports from images or PDF files using OCR. It manages expiration dates
and keeps multiple passports for a contact. A new wizard allows reading
passport data directly from an uploaded image using `pytesseract`.

Install the Python dependencies from `requirements.txt` and ensure the
`tesseract-ocr` binary is available in the system. The module also defines a
scheduled action that posts a message on contacts whose passports are expired
or close to expire.
