# Partner Passport OCR

This module adds basic passport management with OCR capabilities.

## Requirements
- Odoo 16.0 or newer
- Python packages: `pytesseract`, `Pillow`
- System package: `tesseract-ocr`

## Usage
1. Install the module in Odoo.
2. Attach a scanned passport image to a passport record.
3. Click **Scan Passport** to populate fields using OCR.
4. A scheduled job checks expirations daily and posts messages on the contact.

## Cron
The job `Passport Expiry Check` runs every day and notifies when a passport is
expired or near expiration (30/90/180/360 days).

## Permissions
Only members of the **Passport Officer** group can scan or edit passport data.
