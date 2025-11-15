# -*- coding: utf-8 -*-
import uuid
from odoo import api, fields, models


class DsScreen(models.Model):
    _name = "ds.screen"
    _description = "Digital Signage Screen"

    name = fields.Char(required=True)
    token = fields.Char(default=lambda self: str(uuid.uuid4()), copy=False, index=True, readonly=True)
    playlist_id = fields.Many2one("ds.playlist", string="Playlist", ondelete="set null")
    preloader_asset_id = fields.Many2one("ds.asset", string="Preloader Asset", ondelete="set null", 
                                         help="Asset (usually an image or video) to display while loading each slide. Helps avoid browser default loading icons for external videos and YouTube.")
    show_fullscreen_button = fields.Boolean(string="Show Fullscreen Button", default=True,
                                            help="Display the fullscreen button on the player. Some browsers already provide fullscreen controls.")
    cache_slides = fields.Boolean(string="Cache Slides", default=False, 
                                   help="Keep rendered slides in memory and reuse them when cycling through playlist. Improves performance by avoiding re-rendering. Best for images and videos.")
    preload_next_slide = fields.Boolean(string="Preload Next Slide", default=False,
                                        help="Load the next slide in background while current slide plays. Provides smoother transitions but uses more bandwidth and memory.")
    is_public = fields.Boolean(string="Public", default=True)
    active = fields.Boolean(default=True)
    last_ping = fields.Datetime(readonly=True)
    note = fields.Text()

    _sql_constraints = [
        ("token_unique", "unique(token)", "Screen token must be unique."),
    ]

    def action_open_player(self):
        self.ensure_one()
        url = f"/ds/s/{self.token}"
        return {
            "type": "ir.actions.act_url",
            "name": "Open Player",
            "target": "new",
            "url": url,
        }
