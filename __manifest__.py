# -*- coding: utf-8 -*-
{
    "name": "Digital Signage",
    "summary": "Playlists of images, videos, webpages, and QWeb templates for screens",
    "version": "18.0.1.0.0",
    "category": "Marketing",
    "author": "A Brand Inc.",
    "website": "https://abrandinc.com",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/asset_views.xml",
        "views/playlist_views.xml",
        "views/screen_views.xml",
        "views/player_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ds_signage/static/src/css/player.css",
            "ds_signage/static/src/js/player.js",
        ],
    },
    "application": True,
    "installable": True,
}
