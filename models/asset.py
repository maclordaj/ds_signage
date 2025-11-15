# -*- coding: utf-8 -*-
import base64
import mimetypes
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class DsAsset(models.Model):
    _name = "ds.asset"
    _description = "Digital Signage Asset"
    _order = "create_date desc, id desc"

    type = fields.Selection([
        ("image", "Image"),
        ("video", "Video (Uploaded)"),
        ("video_url", "Video (External URL)"),
        ("youtube", "YouTube"),
        ("webpage", "Web Page"),
        ("calendar", "Calendar (URL)"),
        ("qweb", "QWeb Template"),
    ], required=True, default="image")

    name = fields.Char(required=True, index=True)
    file = fields.Binary(string="File", attachment=True)
    file_name = fields.Char(string="File Name", help="Original filename for MIME type detection")

    @api.model
    def _detect_mime_from_content(self, file_data):
        """Detect MIME type from file content using magic bytes"""
        try:
            if len(file_data) >= 12:
                # JPEG: FF D8 FF
                if file_data[0:3] == b'\xFF\xD8\xFF':
                    return 'image/jpeg'
                # PNG: 89 50 4E 47 0D 0A 1A 0A
                if file_data[0:8] == b'\x89PNG\r\n\x1a\n':
                    return 'image/png'
                # GIF: 'GIF87a' or 'GIF89a'
                if file_data[0:6] in (b'GIF87a', b'GIF89a'):
                    return 'image/gif'
                # WebP: 'RIFF'....'WEBP'
                if file_data[0:4] == b'RIFF' and file_data[8:12] == b'WEBP':
                    return 'image/webp'
                # MP4: 'ftyp' at offset 4
                if file_data[4:8] == b'ftyp':
                    return 'video/mp4'
                # MOV: 'moov' or 'mdat' or 'ftyp'
                if b'moov' in file_data[0:32] or b'mdat' in file_data[0:32]:
                    return 'video/quicktime'
        except Exception:
            pass
        return None

    @api.model
    def _detect_mime_from_filename(self, filename):
        """Detect MIME type from filename extension"""
        if not filename:
            return None
        
        name_lower = filename.lower()
        if name_lower.endswith(('.jpg', '.jpeg')):
            return 'image/jpeg'
        elif name_lower.endswith('.png'):
            return 'image/png'
        elif name_lower.endswith('.gif'):
            return 'image/gif'
        elif name_lower.endswith('.webp'):
            return 'image/webp'
        elif name_lower.endswith(('.mp4', '.m4v')):
            return 'video/mp4'
        elif name_lower.endswith('.mov'):
            return 'video/quicktime'
        elif name_lower.endswith('.avi'):
            return 'video/x-msvideo'
        elif name_lower.endswith('.webm'):
            return 'video/webm'
        elif name_lower.endswith('.mkv'):
            return 'video/x-matroska'
        
        # Fallback to Python's mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type

    @api.onchange('file')
    def _onchange_file(self):
        """Auto-detect file_mimetype when file is uploaded"""
        if self.file:
            try:
                # Decode the file to analyze content
                file_data = base64.b64decode(self.file)
                
                # Try to detect from content first (most reliable)
                detected_mime = self._detect_mime_from_content(file_data)
                
                # If no content detection, try filename
                if not detected_mime and self.file_name:
                    detected_mime = self._detect_mime_from_filename(self.file_name)
                
                # If still no detection, try asset name
                if not detected_mime and self.name:
                    detected_mime = self._detect_mime_from_filename(self.name)
                
                # Set the detected MIME type
                if detected_mime:
                    self.file_mimetype = detected_mime
                    _logger.info(f"Auto-detected MIME type '{detected_mime}' for asset")
                
                # Auto-set asset type based on MIME type
                if detected_mime:
                    if detected_mime.startswith('image/'):
                        self.type = 'image'
                    elif detected_mime.startswith('video/'):
                        self.type = 'video'
                        
            except Exception as e:
                _logger.warning(f"Failed to auto-detect MIME type: {e}")

    file_mimetype = fields.Char(string="MIME Type")
    url = fields.Char(string="URL")
    qweb_key = fields.Char(string="QWeb XML ID", help="XML ID of a QWeb template to render for this slide (e.g., module.template_id)")
    duration = fields.Integer(string="Duration (seconds)", default=10, help="Default time to show this asset if not a video with natural length")
    cache_content = fields.Boolean(string="Cache Content", default=True,
                                    help="For webpages and calendars: cache the iframe and reuse it when cycling. Disable for dynamic content like weather or live data.")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_not_empty", "CHECK(name <> '')", "Name must not be empty."),
    ]

    @api.constrains("type", "file", "url", "qweb_key")
    def _check_required_per_type(self):
        for rec in self:
            if rec.type in ("image", "video") and not rec.file:
                # Keep minimal, just warn in logs to avoid blocking early setup.
                _logger.debug("Asset %s of type %s has no file set.", rec.name, rec.type)
            if rec.type in ("video_url", "webpage", "calendar", "youtube") and not rec.url:
                _logger.debug("Asset %s of type %s has no URL set.", rec.name, rec.type)
            if rec.type == "qweb" and not (rec.qweb_key):
                _logger.debug("Asset %s of type qweb has no qweb_key set.", rec.name)
