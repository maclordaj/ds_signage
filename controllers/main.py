# -*- coding: utf-8 -*-
import base64
import json
import logging
from urllib.parse import parse_qs, urlparse

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def _youtube_embed_from_url(url):
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.endswith("youtu.be"):
            vid = parsed.path.strip("/")
            return f"https://www.youtube.com/embed/{vid}?autoplay=1&mute=1&controls=0&rel=0"
        if "youtube.com" in host:
            if parsed.path.startswith("/watch"):
                q = parse_qs(parsed.query or "")
                vid = (q.get("v") or [""])[0]
                if vid:
                    return f"https://www.youtube.com/embed/{vid}?autoplay=1&mute=1&controls=0&rel=0"
            if parsed.path.startswith("/embed/"):
                vid = parsed.path.split("/")[-1]
                return f"https://www.youtube.com/embed/{vid}?autoplay=1&mute=1&controls=0&rel=0"
        # fallback
        return url
    except Exception:  # noqa: BLE001
        return url


class DsSignageController(http.Controller):

    @http.route(['/ds/s/<string:token>'], type='http', auth='public', methods=['GET'], csrf=False)
    def screen_player(self, token, **kwargs):
        Screen = request.env['ds.screen'].sudo()
        screen = Screen.search([('token', '=', token), ('active', '=', True)], limit=1)
        if not screen or not screen.playlist_id:
            return request.not_found()
        playlist = screen.playlist_id
        slides = []
        for item in playlist.item_ids.sorted(key=lambda r: (r.sequence, r.id)):
            asset = item.asset_id
            s = {
                'id': asset.id,
                'name': asset.name,
                'type': asset.type,
                'duration': item.duration_override or asset.duration or 10,
            }
            if asset.type in ('image', 'video'):
                # Cache buster so browser refetches when asset changes and to avoid stale headers
                ver_dt = asset.write_date or asset.create_date
                ver = ver_dt.strftime('%Y%m%d%H%M%S') if ver_dt else '0'
                s['src'] = f"/ds/a/{asset.id}/content?v={ver}"
            elif asset.type == 'video_url':
                s['src'] = asset.url
            elif asset.type == 'youtube':
                s['src'] = _youtube_embed_from_url(asset.url or '')
            elif asset.type in ('webpage', 'calendar'):
                s['src'] = asset.url
            elif asset.type == 'qweb':
                html = ''
                if asset.qweb_key:
                    try:
                        html = request.env['ir.ui.view']._render_template(asset.qweb_key, {
                            'asset': asset,
                            'playlist': playlist,
                            'screen': screen,
                        })
                    except Exception as e:  # noqa: BLE001
                        _logger.exception("Failed to render qweb template %s: %s", asset.qweb_key, e)
                        html = f"<div class=\"ds-error\">QWeb template '{asset.qweb_key}' not found</div>"
                s['html'] = html
            slides.append(s)

        values = {
            'screen': screen,
            'playlist': playlist,
            'slides_json': json.dumps(slides),
            'meta_json': json.dumps({'title': f"{playlist.name} — Digital Signage", 'playlist_id': playlist.id, 'screen_token': screen.token, 'auto_unmute': playlist.auto_unmute}),
            'title': f"{playlist.name} — Digital Signage",
        }
        return request.render('ds_signage.player', values)

    @http.route(['/ds/p/<int:playlist_id>'], type='http', auth='public', methods=['GET'], csrf=False)
    def playlist_player(self, playlist_id, **kwargs):
        playlist = request.env['ds.playlist'].sudo().browse(int(playlist_id))
        if not playlist or not playlist.exists():
            return request.not_found()
        # Fake a transient screen context
        class O:
            pass
        screen = O()
        screen.name = f"Playlist #{playlist.id}"
        screen.token = ""
        slides = []
        for item in playlist.item_ids.sorted(key=lambda r: (r.sequence, r.id)):
            asset = item.asset_id
            s = {
                'id': asset.id,
                'name': asset.name,
                'type': asset.type,
                'duration': item.duration_override or asset.duration or 10,
            }
            if asset.type in ('image', 'video'):
                s['src'] = f"/ds/a/{asset.id}/content"
            elif asset.type == 'video_url':
                s['src'] = asset.url
            elif asset.type == 'youtube':
                s['src'] = _youtube_embed_from_url(asset.url or '')
            elif asset.type in ('webpage', 'calendar'):
                s['src'] = asset.url
            elif asset.type == 'qweb':
                html = ''
                if asset.qweb_key:
                    try:
                        html = request.env['ir.ui.view']._render_template(asset.qweb_key, {
                            'asset': asset,
                            'playlist': playlist,
                            'screen': screen,
                        })
                    except Exception as e:  # noqa: BLE001
                        _logger.exception("Failed to render qweb template %s: %s", asset.qweb_key, e)
                        html = f"<div class=\"ds-error\">QWeb template '{asset.qweb_key}' not found</div>"
                s['html'] = html
            slides.append(s)

        values = {
            'screen': screen,
            'playlist': playlist,
            'slides_json': json.dumps(slides),
            'meta_json': json.dumps({'title': f"{playlist.name} — Digital Signage", 'playlist_id': playlist.id, 'auto_unmute': playlist.auto_unmute}),
            'title': f"{playlist.name} — Digital Signage",
        }
        return request.render('ds_signage.player', values)

    @http.route(['/ds/a/<int:asset_id>/content'], type='http', auth='public', methods=['GET'], csrf=False)
    def asset_content(self, asset_id, **kwargs):
        asset = request.env['ds.asset'].sudo().browse(int(asset_id))
        _logger.info(f"Asset content request for ID {asset_id}: exists={asset.exists()}, has_file={bool(asset.file)}, type={asset.type if asset.exists() else 'N/A'}")
        
        if not asset or not asset.exists():
            _logger.warning(f"Asset {asset_id} not found")
            return request.not_found()
            
        if not asset.file:
            _logger.warning(f"Asset {asset_id} has no file content")
            return request.not_found()
            
        try:
            data = base64.b64decode(asset.file)
            _logger.info(f"Asset {asset_id}: decoded {len(data)} bytes, mimetype={asset.file_mimetype}")
        except Exception as e:
            _logger.error(f"Failed to decode asset {asset_id}: {e}")
            return request.not_found()
            
        # Determine proper MIME type with strong preference for the asset.type
        raw_mime = (asset.file_mimetype or '').lower()
        filename = asset.file_name or asset.name or ''
        name_lower = filename.lower()

        def mime_from_ext(nl):
            if nl.endswith(('.jpg', '.jpeg')):
                return 'image/jpeg'
            if nl.endswith('.png'):
                return 'image/png'
            if nl.endswith('.gif'):
                return 'image/gif'
            if nl.endswith(('.mp4', '.m4v')):
                return 'video/mp4'
            if nl.endswith('.mov'):
                return 'video/quicktime'
            if nl.endswith('.avi'):
                return 'video/x-msvideo'
            if nl.endswith('.webm'):
                return 'video/webm'
            if nl.endswith('.mkv'):
                return 'video/x-matroska'
            return None

        def sniff_image_mime(binary: bytes):
            try:
                if len(binary) >= 12:
                    # JPEG: FF D8 FF
                    if binary[0:3] == b'\xFF\xD8\xFF':
                        return 'image/jpeg'
                    # PNG: 89 50 4E 47 0D 0A 1A 0A
                    if binary[0:8] == b'\x89PNG\r\n\x1a\n':
                        return 'image/png'
                    # GIF: 'GIF87a' or 'GIF89a'
                    if binary[0:6] in (b'GIF87a', b'GIF89a'):
                        return 'image/gif'
                    # WebP: 'RIFF'....'WEBP'
                    if binary[0:4] == b'RIFF' and binary[8:12] == b'WEBP':
                        return 'image/webp'
            except Exception:  # noqa: BLE001
                pass
            return None

        if asset.type == 'image':
            mimetype = raw_mime if raw_mime.startswith('image/') else (mime_from_ext(name_lower) or 'image/jpeg')
        elif asset.type == 'video':
            mimetype = raw_mime if raw_mime.startswith('video/') else (mime_from_ext(name_lower) or 'video/mp4')
        else:
            mimetype = raw_mime or (mime_from_ext(name_lower) or 'application/octet-stream')

        # As a final guard, if asset says it's an image but MIME doesn't, sniff the bytes
        if asset.type == 'image' and not (mimetype or '').startswith('image/'):
            sniffed = sniff_image_mime(data)
            if sniffed:
                _logger.info(f"Asset {asset_id}: Overriding MIME to '{sniffed}' based on image signature")
                mimetype = sniffed

        _logger.info(f"Asset {asset_id}: Using MIME type '{mimetype}' for file '{filename}', asset.type={asset.type}, raw_mime={asset.file_mimetype}")

        # Enable browser streaming by handling HTTP Range requests (videos only)
        total_size = len(data)
        range_header = request.httprequest.headers.get('Range')
        disposition_name = filename or f"asset_{asset_id}"
        is_video = (mimetype or '').startswith('video/')

        if is_video and range_header:
            # Typical format: 'bytes=start-end'
            _logger.info(f"Asset {asset_id}: Received Range header '{range_header}' (total {total_size} bytes)")
            try:
                units, rng = range_header.split('=')
                if units.strip() != 'bytes':
                    raise ValueError('Unsupported range unit')
                start_str, end_str = (rng or '').split('-')
                if start_str == '':
                    # suffix length: '-N' means last N bytes
                    length = int(end_str)
                    start = max(total_size - length, 0)
                    end = total_size - 1
                else:
                    start = int(start_str)
                    end = int(end_str) if end_str else total_size - 1
                # Clamp values
                if start < 0 or end < start or start >= total_size:
                    raise ValueError('Invalid range values')
                end = min(end, total_size - 1)

                chunk = data[start:end + 1]
                headers = [
                    ('Content-Type', mimetype),
                    ('Cache-Control', 'public, max-age=3600'),
                    ('Accept-Ranges', 'bytes'),
                    ('Content-Range', f'bytes {start}-{end}/{total_size}'),
                    ('Content-Length', str(len(chunk))),
                    ('Content-Disposition', f'inline; filename="{disposition_name}"'),
                    ('Access-Control-Allow-Origin', '*'),
                    ('Access-Control-Expose-Headers', 'Content-Type, Content-Length, Accept-Ranges, Content-Range'),
                    ('Cross-Origin-Resource-Policy', 'cross-origin'),
                ]
                response = request.make_response(chunk, headers=headers)
                # Set Partial Content status for range responses
                try:
                    response.status_code = 206
                except Exception:  # noqa: BLE001
                    pass
                return response
            except Exception as e:  # noqa: BLE001
                _logger.warning(f"Asset {asset_id}: Failed to parse Range header '{range_header}': {e}")
                # Fall back to full content

        # No (valid) Range header or not a video: return full content
        headers = [
            ('Content-Type', mimetype),
            ('Cache-Control', 'public, max-age=3600'),
            ('Content-Length', str(total_size)),
            ('Content-Disposition', f'inline; filename="{disposition_name}"'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Expose-Headers', 'Content-Type, Content-Length'),
            ('Cross-Origin-Resource-Policy', 'cross-origin'),
        ]
        if is_video:
            headers.append(('Accept-Ranges', 'bytes'))
        return request.make_response(data, headers=headers)

    @http.route(['/ds/calendar'], type='http', auth='public', methods=['GET'], csrf=False)
    def calendar_events(self, **kwargs):
        """Public calendar events list for embedding in digital signage"""
        try:
            # Get today's events from calendar.event model
            from datetime import datetime, timedelta
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            # Search for today's events
            events = request.env['calendar.event'].sudo().search([
                ('start', '>=', today),
                ('start', '<', tomorrow),
            ], order='start asc', limit=10)
            
            values = {
                'events': events,
                'today': today,
            }
            return request.render('ds_signage.calendar_list', values)
            
        except Exception as e:
            _logger.warning(f"Calendar events error: {e}")
            # Fallback with empty events
            values = {
                'events': [],
                'today': datetime.now().date(),
            }
            return request.render('ds_signage.calendar_list', values)
