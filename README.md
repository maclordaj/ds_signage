# Digital Signage Module for Odoo 18

A comprehensive digital signage solution for Odoo 18 that supports playlists with multiple content types including images, videos, webpages, and custom QWeb templates.

## Features

### Content Types Supported
- **Images**: Upload PNG, JPG, GIF files
- **Videos**: Upload MP4/other video files or use external URLs
- **YouTube**: Paste YouTube URLs (automatically converted to embeds)
- **Web Pages**: Display any webpage via iframe
- **Calendar Views**: Display calendar URLs
- **QWeb Templates**: Custom HTML content using Odoo's QWeb templating system

### Core Models
- **Assets** (`ds.asset`): Individual content items with type, duration, and content
- **Playlists** (`ds.playlist`): Collections of assets with sequencing
- **Playlist Items** (`ds.playlist.item`): Links assets to playlists with custom durations
- **Screens** (`ds.screen`): Display endpoints with unique tokens and assigned playlists

## Installation

1. Ensure the module is in your addons path
2. Update the app list: **Apps > Update Apps List**
3. Search for "Digital Signage" and click **Install**

Or via command line:
```bash
# Docker example
docker compose exec odoo odoo -u ds_signage -d your_database_name
```

## Usage

### 1. Create Assets
Navigate to **Digital Signage > Assets** and create content:
- Set the content type (Image, Video, YouTube, etc.)
- Upload files or enter URLs as appropriate
- Set default duration in seconds
- For QWeb assets, specify the XML ID of your template

### 2. Build Playlists
Go to **Digital Signage > Playlists**:
- Create a new playlist
- Add assets using the Items tab
- Set sequence order and override durations if needed

### 3. Configure Screens
In **Digital Signage > Screens**:
- Create a screen and assign a playlist
- Each screen gets a unique token for security
- Click **Open Player** to launch the display

### 4. Display Content
Access your signage display via:
- **Screen URL**: `/ds/s/<screen_token>` (recommended)
- **Direct Playlist**: `/ds/p/<playlist_id>` (for testing)

## Public Routes

- `GET /ds/s/<token>`: Screen player (requires valid screen token)
- `GET /ds/p/<playlist_id>`: Direct playlist player (public)
- `GET /ds/a/<asset_id>/content`: Serves uploaded asset files (public, cached)

## Customization

### QWeb Templates
Create custom slide content using Odoo's QWeb system:

1. Create a QWeb template in your module:
```xml
<template id="my_custom_slide" name="Custom Slide">
    <div class="custom-slide">
        <h1>Welcome to <t t-esc="screen.name"/></h1>
        <p>Current playlist: <t t-esc="playlist.name"/></p>
        <!-- Your custom HTML here -->
    </div>
</template>
```

2. Reference it in an asset with `qweb_key = "your_module.my_custom_slide"`

### Player Template
Override the main player template by inheriting `ds_signage.player`:
```xml
<template id="custom_player" inherit_id="ds_signage.player">
    <xpath expr="//div[@id='ds_player_root']" position="before">
        <!-- Add custom overlays, branding, etc. -->
    </xpath>
</template>
```

## Technical Details

### Asset Bundle
The player uses a dedicated asset bundle `ds_signage.assets_player` containing:
- `ds_signage/static/src/css/player.css`: Fullscreen styling
- `ds_signage/static/src/js/player.js`: Slide rotation logic

### Player Behavior
- Automatically cycles through playlist items in sequence order
- Respects individual asset durations or playlist item overrides
- Handles video autoplay restrictions with user interaction hints
- Supports fullscreen display with proper aspect ratio handling

### Security
- All public routes are accessible without authentication
- Screen tokens provide access control for displays
- Asset content is served with appropriate caching headers

## Future Roadmap

### Planned Features
- **Scheduling**: Time-based playlist activation and content scheduling
- **CRM Integration**: Link screens and content to contacts/customers
- **Subscription Management**: Content access based on subscription levels
- **Analytics**: View tracking and engagement metrics
- **Multi-zone Layouts**: Split-screen and multi-region displays
- **Remote Management**: Bulk screen updates and monitoring
- **Content Approval**: Workflow for content review and publishing

### Extensibility Points
The module is designed for easy extension:
- Add custom asset types by extending the `type` selection field
- Implement scheduling via additional models linking to `ds.playlist.item`
- Add CRM features through Many2many relationships to `res.partner`
- Create custom player layouts by inheriting the QWeb template

## Troubleshooting

### Common Issues
- **Videos not playing**: Check autoplay policies; users may need to interact first
- **External content not loading**: Verify the target site allows iframe embedding
- **QWeb templates not rendering**: Ensure the XML ID exists and is accessible

### Browser Compatibility
- Modern browsers with ES6 support required
- Autoplay policies vary by browser and user settings
- Fullscreen API support recommended for kiosk mode

## Support

For issues and feature requests, contact the development team or check the module documentation in your Odoo instance.
