from odoo import api, fields, models, _
from odoo.exceptions import UserError

import base64
import io
from datetime import datetime, timedelta

try:
    import pytesseract
except ImportError:  # pragma: no cover - dependency may not be installed
    pytesseract = None

try:
    from pdf2image import convert_from_bytes
except ImportError:  # pragma: no cover
    convert_from_bytes = None

from PIL import Image

class PassportReader(models.Model):
    _name = 'passport.reader'
    _description = 'Passport Reader'

    name = fields.Char('Name')
    contact_id = fields.Many2one('res.partner', string='Contact')
    file = fields.Binary(string='Passport File', attachment=True)
    file_filename = fields.Char()
    passport_number = fields.Char()
    expiration_date = fields.Date()

    _sql_constraints = [
        ('passport_contact_unique', 'unique(contact_id, passport_number)',
         'A passport with this number already exists for this contact.'),
    ]

    def is_expired(self):
        self.ensure_one()
        if self.expiration_date:
            return fields.Date.today() > self.expiration_date
        return False

    def is_expiring_soon(self):
        self.ensure_one()
        if self.expiration_date:
            soon = fields.Date.today() + timedelta(days=60)
            return fields.Date.today() <= self.expiration_date <= soon
        return False

    def _extract_text_from_file(self):
        if not self.file:
            raise UserError(_('No file to process.'))
        if not pytesseract:
            raise UserError(_('pytesseract is not installed.'))
        binary = base64.b64decode(self.file)
        filename = (self.file_filename or '').lower()
        images = []
        if filename.endswith('.pdf'):
            if not convert_from_bytes:
                raise UserError(_('pdf2image is not installed.'))
            images = convert_from_bytes(binary)
        else:
            images = [Image.open(io.BytesIO(binary))]
        text = ''
        for img in images:
            text += pytesseract.image_to_string(img)
        return text

    def parse_passport_text(self, text):
        # Very naive MRZ parser for demonstration
        if not text:
            return
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        mrz_lines = [l for l in lines if l.startswith('P<')]
        if mrz_lines:
            idx = lines.index(mrz_lines[0])
            if len(lines) > idx + 1:
                second = lines[idx + 1]
                self.passport_number = second[0:9].replace('<', '')
        # Fallback: try to find a number pattern
        if not self.passport_number:
            for line in lines:
                if line.isalnum() and len(line) >= 6:
                    self.passport_number = line
                    break

    def action_read_passport(self):
        for record in self:
            text = record._extract_text_from_file()
            if not text:
                raise UserError(_('Could not read passport.'))
            record.parse_passport_text(text)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.is_expired():
                raise UserError(_('Passport is expired.'))
        return records

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.is_expired():
                raise UserError(_('Passport is expired.'))
        return res
