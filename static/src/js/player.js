document.addEventListener('DOMContentLoaded', function() {
  'use strict';
  
  console.log('DS Player: DOM loaded');

  function readJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) {
      console.log('DS Player: Script element not found:', id);
      return null;
    }
    try {
      const data = JSON.parse(el.textContent || 'null');
      console.log('DS Player: Parsed JSON for', id, ':', data);
      return data;
    } catch (e) {
      console.error('DS Player: JSON parse error for', id, ':', e);
      return null;
    }
  }

  const slides = Array.isArray(readJsonScript('ds_slides')) ? readJsonScript('ds_slides') : [];
  const meta = readJsonScript('ds_meta') || {};
  const autoUnmute = meta.auto_unmute || false;
  const preloaderConfig = meta.preloader || null;
  const showFullscreenButton = meta.show_fullscreen_button !== false; // Default to true
  const root = document.getElementById('ds_player_root');
  const container = document.getElementById('ds_player');
  
  console.log('DS Player: Elements found - root:', !!root, 'container:', !!container);
  console.log('DS Player: Slides count:', slides.length);
  console.log('DS Player: Meta:', meta);
  
  if (!container) {
    console.error('DS Player: Container not found');
    return;
  }

  document.title = meta.title || 'Digital Signage';

  let idx = -1;
  let timer = null;
  let preloaderOverlay = null;
  let preloadedPreloaderElement = null;

  function clear() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    while (container.firstChild) container.removeChild(container.firstChild);
  }

  function next() {
    if (!slides.length) {
      console.log('DS Player: No slides available in next()');
      return;
    }
    idx = (idx + 1) % slides.length;
    console.log('DS Player: Moving to slide', idx, 'of', slides.length);
    render(slides[idx]);
  }

  function wait(ms) {
    timer = setTimeout(next, ms);
  }

  function mk(tag, attrs) {
    const el = document.createElement(tag);
    if (attrs) Object.entries(attrs).forEach(([k, v]) => {
      if (k in el) el[k] = v; else el.setAttribute(k, v);
    });
    return el;
  }

  // Preload the preloader asset once at startup
  function preloadPreloaderAsset() {
    if (!preloaderConfig || !preloaderConfig.src) {
      console.log('DS Player: No preloader configured');
      return;
    }
    
    console.log('DS Player: Preloading preloader asset');
    
    if (preloaderConfig.type === 'image') {
      preloadedPreloaderElement = mk('img', { src: preloaderConfig.src, className: 'ds-preloader-content' });
      // Preload by setting src - browser will cache it
      preloadedPreloaderElement.addEventListener('load', () => {
        console.log('DS Player: Preloader asset cached and ready');
      });
      preloadedPreloaderElement.addEventListener('error', () => {
        console.error('DS Player: Failed to preload preloader asset');
      });
    } else if (preloaderConfig.type === 'video') {
      preloadedPreloaderElement = mk('video', {
        muted: true,
        loop: true,
        playsInline: true,
        className: 'ds-preloader-content',
        preload: 'auto'
      });
      const sourceEl = mk('source', { src: preloaderConfig.src });
      preloadedPreloaderElement.appendChild(sourceEl);
      // Preload video metadata
      preloadedPreloaderElement.load();
    }
  }

  function showPreloader() {
    if (!preloadedPreloaderElement) {
      console.log('DS Player: No preloader configured');
      return;
    }
    
    console.log('DS Player: Showing preloader');
    hidePreloader(); // Remove any existing preloader first
    
    preloaderOverlay = mk('div', { className: 'ds-preloader-overlay' });
    
    // Clone the preloaded element to reuse it
    const preloaderClone = preloadedPreloaderElement.cloneNode(true);
    
    // If video, restart playback
    if (preloaderConfig.type === 'video') {
      preloaderClone.muted = true;
      preloaderClone.autoplay = true;
      preloaderClone.load();
      preloaderClone.play().catch(err => {
        console.log('DS Player: Preloader video autoplay failed:', err);
      });
    }
    
    preloaderOverlay.appendChild(preloaderClone);
    container.appendChild(preloaderOverlay);
  }

  function hidePreloader() {
    if (preloaderOverlay && preloaderOverlay.parentNode) {
      console.log('DS Player: Hiding preloader');
      preloaderOverlay.parentNode.removeChild(preloaderOverlay);
      preloaderOverlay = null;
    }
  }

  function render(slide) {
    console.log('DS Player: Rendering slide:', slide);
    const type = slide.type;
    const dur = Math.max(1, parseInt(slide.duration || 10, 10)) * 1000;
    
    // Show preloader on top BEFORE clearing and loading the new slide
    // This ensures no gap or browser loading indicators show
    const needsPreloader = (type === 'video' || type === 'video_url' || type === 'youtube' || type === 'webpage' || type === 'calendar');
    if (needsPreloader) {
      showPreloader();
    }
    
    // Now clear and load the slide underneath the preloader
    clear();

    if (type === 'image') {
      console.log('DS Player: Creating image element with src:', slide.src);
      const img = mk('img', { src: slide.src, className: 'ds-fit' });
      
      img.addEventListener('load', () => {
        console.log('DS Player: Image loaded successfully:', slide.src);
      });
      
      img.addEventListener('error', (e) => {
        console.error('DS Player: Image failed to load:', slide.src, e);
        console.log('DS Player: Testing image URL access...');
        
        // Test if URL is accessible
        fetch(slide.src)
          .then(response => {
            console.log('DS Player: Image URL fetch response:', response.status, response.headers.get('content-type'));
            if (!response.ok) {
              console.error('DS Player: Image URL returned', response.status, response.statusText);
            }
          })
          .catch(err => {
            console.error('DS Player: Image URL fetch failed:', err);
          });
        
        const errorMsg = mk('div', { 
          className: 'ds-error', 
          innerText: `Image Error: Failed to load ${slide.name}. URL: ${slide.src}`
        });
        container.appendChild(errorMsg);
      });
      
      container.appendChild(img);
      wait(dur);
      return;
    }

    if (type === 'video' || type === 'video_url') {
      console.log('DS Player: Creating video element with src:', slide.src);
      
      const video = mk('video', {
        autoplay: true,
        muted: !autoUnmute,
        loop: false,
        playsInline: true,
        className: 'ds-contain',
        controls: false
      });
      // Provide explicit MIME hint via <source> to help Safari determine codec/container
      const lname = String(slide.name || '').toLowerCase();
      let guessedType = '';
      if (lname.endsWith('.mp4') || lname.endsWith('.m4v')) guessedType = 'video/mp4';
      else if (lname.endsWith('.mov')) guessedType = 'video/quicktime';
      else if (lname.endsWith('.webm')) guessedType = 'video/webm';
      const sourceEl = mk('source', guessedType ? { src: slide.src, type: guessedType } : { src: slide.src });
      video.appendChild(sourceEl);
      
      video.addEventListener('loadstart', () => {
        console.log('DS Player: Video load started');
      });
      
      video.addEventListener('loadedmetadata', () => {
        console.log('DS Player: Video metadata loaded');
      });
      
      video.addEventListener('loadeddata', () => {
        console.log('DS Player: Video data loaded, attempting play');
        video.play().catch(err => {
          console.log('DS Player: Video autoplay failed:', err);
          // Show click hint for user interaction
          const hint = mk('div', { 
            className: 'ds-hint', 
            innerText: 'Click to start video playback',
            style: 'cursor: pointer; z-index: 10001;'
          });
          hint.addEventListener('click', () => {
            if (!autoUnmute) {
              video.muted = false; // Unmute on user interaction only if not auto-unmuted
            }
            video.play().then(() => {
              hint.remove();
            }).catch(console.error);
          });
          root.appendChild(hint);
        });
      });
      
      // Hide preloader when video actually starts playing
      video.addEventListener('playing', () => {
        console.log('DS Player: Video is now playing');
        hidePreloader();
      }, { once: true });
      
      video.addEventListener('error', (e) => {
        hidePreloader(); // Hide preloader on error too
        const errorCodes = {
          1: 'MEDIA_ERR_ABORTED - Video loading aborted',
          2: 'MEDIA_ERR_NETWORK - Network error loading video', 
          3: 'MEDIA_ERR_DECODE - Video decode error',
          4: 'MEDIA_ERR_SRC_NOT_SUPPORTED - Video format not supported or file not found'
        };
        const errorCode = video.error ? video.error.code : 0;
        const errorText = errorCodes[errorCode] || `Unknown error (${errorCode})`;
        
        console.error('DS Player: Video error:', errorText, 'URL:', slide.src);
        console.log('DS Player: Testing direct URL access...');
        
        // Test if URL is accessible
        fetch(slide.src)
          .then(response => {
            console.log('DS Player: URL fetch response:', response.status, response.headers.get('content-type'));
            if (!response.ok) {
              console.error('DS Player: URL returned', response.status, response.statusText);
            }
          })
          .catch(err => {
            console.error('DS Player: URL fetch failed:', err);
          });
        
        const errorMsg = mk('div', { 
          className: 'ds-error', 
          innerText: `Video Error: ${errorText}. URL: ${slide.src}`
        });
        container.appendChild(errorMsg);
        wait(5000); // Give more time to read error
      });
      
      video.addEventListener('ended', next, { once: true });
      
      // Fallback timer in case video doesn't end naturally
      wait(dur + 2000);
      container.appendChild(video);
      return;
    }

    if (type === 'youtube' || type === 'webpage' || type === 'calendar') {
      let src = slide.src;
      // For YouTube, modify URL to include autoplay and mute parameters based on auto_unmute setting
      if (type === 'youtube' && src.includes('youtube.com/embed/')) {
        const url = new URL(src);
        url.searchParams.set('autoplay', '1');
        url.searchParams.set('mute', autoUnmute ? '0' : '1');
        src = url.toString();
      }
      
      const iframe = mk('iframe', {
        src: src,
        allow: 'autoplay; fullscreen; encrypted-media',
        referrerPolicy: 'no-referrer-when-downgrade',
        frameBorder: '0',
        className: 'ds-frame'
      });
      
      // Hide preloader when iframe loads
      iframe.addEventListener('load', () => {
        console.log('DS Player: Iframe loaded');
        // Delay hiding preloader for YouTube/webpages to ensure content is visible
        setTimeout(() => {
          hidePreloader();
        }, type === 'youtube' ? 2000 : 500);
      });
      
      // Fallback: hide preloader after a timeout if load event doesn't fire
      setTimeout(() => {
        console.log('DS Player: Fallback timeout - hiding preloader');
        hidePreloader();
      }, 8000);
      
      container.appendChild(iframe);
      wait(dur);
      return;
    }

    if (type === 'qweb') {
      const wrap = mk('div', { className: 'ds-qweb' });
      wrap.innerHTML = slide.html || '';
      container.appendChild(wrap);
      wait(dur);
      return;
    }

    // Unknown type
    const err = mk('div', { className: 'ds-error', innerText: 'Unsupported slide type: ' + String(type) });
    container.appendChild(err);
    wait(3000);
  }

  // Fullscreen functionality
  const fullscreenBtn = document.getElementById('ds_fullscreen_btn');
  let hideTimeout;

  // Hide fullscreen button if disabled in screen configuration
  if (fullscreenBtn && !showFullscreenButton) {
    fullscreenBtn.style.display = 'none';
    console.log('DS Player: Fullscreen button hidden by screen configuration');
  }

  function enterFullscreen() {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
      elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) {
      elem.msRequestFullscreen();
    }
  }

  function autoHideButton() {
    if (hideTimeout) clearTimeout(hideTimeout);
    fullscreenBtn.classList.remove('auto-hide');
    hideTimeout = setTimeout(() => {
      fullscreenBtn.classList.add('auto-hide');
    }, 5000);
  }

  if (fullscreenBtn) {
    fullscreenBtn.addEventListener('click', enterFullscreen);
    
    // Auto-hide button after 5 seconds, show on mouse move
    autoHideButton();
    document.addEventListener('mousemove', autoHideButton);
    document.addEventListener('touchstart', autoHideButton);
    
    // Auto-fullscreen requires user interaction - show prominent button on kiosk devices
    setTimeout(() => {
      console.log('DS Player: Auto-fullscreen check - UserAgent:', navigator.userAgent);
      console.log('DS Player: Window dimensions:', window.innerWidth, 'x', window.innerHeight);
      console.log('DS Player: Screen dimensions:', window.screen.width, 'x', window.screen.height);
      
      const isAndroid = navigator.userAgent.includes('Android');
      const isTV = navigator.userAgent.includes('TV') || navigator.userAgent.includes('SmartTV');
      const hasAddressBar = window.innerHeight < (window.screen.height * 0.9);
      const isKioskCandidate = isAndroid || isTV || hasAddressBar;
      
      console.log('DS Player: Auto-fullscreen conditions - Android:', isAndroid, 'TV:', isTV, 'HasAddressBar:', hasAddressBar);
      
      if (isKioskCandidate && !document.fullscreenElement) {
        console.log('DS Player: Showing fullscreen prompt for kiosk device');
        // Make button more prominent and don't auto-hide on kiosk devices
        fullscreenBtn.style.background = 'rgba(255,255,0,0.9)';
        fullscreenBtn.style.color = '#000';
        fullscreenBtn.style.fontSize = '20px';
        fullscreenBtn.style.padding = '12px 16px';
        fullscreenBtn.classList.remove('auto-hide');
        clearTimeout(hideTimeout);
      }
    }, 2000);
  }

  // Preload the preloader asset if configured
  preloadPreloaderAsset();

  if (slides.length) {
    console.log('DS Player: Starting slideshow with', slides.length, 'slides');
    next();
  } else {
    console.log('DS Player: No slides to display');
    const msg = mk('div', { className: 'ds-error', innerText: 'No slides in playlist' });
    container.appendChild(msg);
  }
});
