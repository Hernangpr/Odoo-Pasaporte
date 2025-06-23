from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import base64
import io
from datetime import datetime, timedelta
import re

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
    passport_image = fields.Binary(string='Passport Image', attachment=True)
    passport_image_filename = fields.Char()
    passport_number = fields.Char()
    expiration_date = fields.Date()
    issue_date = fields.Date()

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

    def _extract_text_from_image(self):
        if not self.passport_image:
            raise UserError(_('No image to process.'))
        if not pytesseract:
            raise UserError(_('pytesseract is not installed.'))
        binary = base64.b64decode(self.passport_image)
        img = Image.open(io.BytesIO(binary))
        return pytesseract.image_to_string(img)

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
                exp_raw = second[21:27].replace('<', '')
                try:
                    self.expiration_date = datetime.strptime(exp_raw, '%y%m%d').date()
                except Exception:
                    pass
        # Fallback: try to find a number pattern
        if not self.passport_number:
            for line in lines:
                if line.isalnum() and len(line) >= 6:
                    self.passport_number = line
                    break

        date_candidates = []
        for line in lines:
            matches = re.findall(r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})', line)
            date_candidates.extend(matches)

        def _parse_date(d):
            for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
                try:
                    return datetime.strptime(d, fmt).date()
                except ValueError:
                    continue

        if date_candidates:
            self.issue_date = _parse_date(date_candidates[0]) or self.issue_date
            if len(date_candidates) > 1 and not self.expiration_date:
                self.expiration_date = _parse_date(date_candidates[1]) or self.expiration_date

        # Duplicate validation after parsing
        if self.passport_number:
            existing = self.env['res.partner'].search([
                ('passport_number', '=', self.passport_number)
            ], limit=1)
            if existing:
                raise UserError(_('Ya existe un contacto con este número de pasaporte.'))
        if not self.passport_number or not self.expiration_date:
            raise ValidationError(_("No se pudo extraer información válida del pasaporte."))

    def action_read_passport(self):
        for record in self:
            text = record._extract_text_from_file()
            if not text:
                raise UserError(_('Could not read passport.'))
            record.parse_passport_text(text)
            if record.contact_id:
                record.contact_id.write({
                    'passport_number': record.passport_number,
                    'passport_expiration_date': record.expiration_date,
                })
        return True

    def action_read_image(self):
        for record in self:
            text = record._extract_text_from_image()
            if not text:
                raise ValidationError(_('No se pudo extraer texto de la imagen.'))
            record.parse_passport_text(text)
            if record.contact_id:
                record.contact_id.write({
                    'passport_number': record.passport_number,
                    'passport_expiration_date': record.expiration_date,
                })
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.is_expired():
                raise UserError(_('Passport is expired.'))
        return records

    def write(self, vals):
        if 'file' in vals:
            vals.setdefault('passport_number', False)
            vals.setdefault('expiration_date', False)
        if 'passport_image' in vals:
            vals.setdefault('passport_number', False)
            vals.setdefault('expiration_date', False)
            vals.setdefault('issue_date', False)
        res = super().write(vals)
        for record in self:
            if record.is_expired():
                raise UserError(_('Passport is expired.'))
        return res
