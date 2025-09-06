# -*- coding: utf-8 -*-
from odoo import fields, models


class DsPlaylist(models.Model):
    _name = "ds.playlist"
    _description = "Digital Signage Playlist"
    _order = "name, id"

    name = fields.Char(required=True, index=True)
    item_ids = fields.One2many("ds.playlist.item", "playlist_id", string="Items")
    active = fields.Boolean(default=True)
    auto_unmute = fields.Boolean(string="Auto Unmute Audio", default=False, help="Automatically unmute audio for videos, YouTube, and other media with sound")


class DsPlaylistItem(models.Model):
    _name = "ds.playlist.item"
    _description = "Digital Signage Playlist Item"
    _order = "sequence, id"

    name = fields.Char(related="asset_id.name", store=True)
    sequence = fields.Integer(default=10)
    playlist_id = fields.Many2one("ds.playlist", required=True, ondelete="cascade")

    asset_id = fields.Many2one("ds.asset", required=True, ondelete="restrict")
    duration_override = fields.Integer(string="Duration Override (s)")
