/**
 * BioSecure AI - Persistent Shell Client Navigation Engine
 * High-performance native Web Platform client-side router for zero-delay PWA tab switching.
 * Features:
 *  - 0ms instant touch feedback on pointerdown/touchstart
 *  - In-memory pre-warming cache (window.__pwaPageCache) via requestIdleCallback & pointerdown
 *  - Outgoing view teardown (stops webcam hardware tracks, wake locks, DataTables, timers)
 *  - View Transitions API (<main> swap, modal sync, document.title update, smooth cross-fade)
 *  - Script dependency loader & safe inline execution (let/const to var transpilation)
 *  - 60ms latency-gated glowing top progress bar (#pwa-nav-bar)
 *  - Browser history synchronization & mobile swipe gestures
 */

(function () {
  'use strict';

  if (window.__pwaNavInitialized) return;
  window.__pwaNavInitialized = true;

  // Global registries for in-memory page cache and media streams
  window.__pwaPageCache = window.__pwaPageCache || new Map();
  window.__activeMediaStreams = window.__activeMediaStreams || [];

  // Core navigation routes to pre-warm
  const CORE_ROUTES = ['/', '/viewer', '/students', '/add_student', '/admin'];

  // Intercept and track all created media streams to guarantee clean teardown
  if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function') {
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async function (constraints) {
      const stream = await originalGetUserMedia(constraints);
      if (stream && !window.__activeMediaStreams.includes(stream)) {
        window.__activeMediaStreams.push(stream);
      }
      return stream;
    };
  }

  // --- Top Progress Bar Controller (60ms latency-gated) ---
  let progressBar = null;
  let progressTimer = null;

  function ensureProgressBar() {
    if (!progressBar) {
      progressBar = document.getElementById('pwa-nav-bar');
      if (!progressBar) {
        progressBar = document.createElement('div');
        progressBar.id = 'pwa-nav-bar';
        document.body.appendChild(progressBar);
      }
    }
    return progressBar;
  }

  function startProgress() {
    clearTimeout(progressTimer);
    const bar = ensureProgressBar();
    bar.classList.remove('active');
    bar.style.width = '0%';
    progressTimer = setTimeout(() => {
      bar.classList.add('active');
      bar.style.width = '35%';
      setTimeout(() => {
        if (bar.classList.contains('active')) {
          bar.style.width = '75%';
        }
      }, 200);
    }, 60);
  }

  function completeProgress() {
    clearTimeout(progressTimer);
    if (progressBar && progressBar.classList.contains('active')) {
      progressBar.style.width = '100%';
      setTimeout(() => {
        progressBar.classList.remove('active');
        setTimeout(() => {
          progressBar.style.width = '0%';
        }, 200);
      }, 150);
    }
  }

  // --- Active Navigation Indicator Sync (0ms Touch Feedback) ---
  function updateNavActive(targetPath) {
    const normalizedTarget = targetPath === '' ? '/' : targetPath;

    // Desktop sidebar links
    const sidebarLinks = document.querySelectorAll('aside nav a[href]');
    sidebarLinks.forEach((link) => {
      try {
        const linkPath = new URL(link.href, location.origin).pathname;
        if (linkPath === normalizedTarget) {
          link.classList.add('bg-blue-500/10', 'text-blue-400', 'border', 'border-blue-500/20');
          link.classList.remove('text-gray-300');
        } else {
          link.classList.remove('bg-blue-500/10', 'text-blue-400', 'border', 'border-blue-500/20');
          link.classList.add('text-gray-300');
        }
      } catch (_) {}
    });

    // Mobile bottom dock links
    const mobileLinks = document.querySelectorAll('nav.fixed.bottom-0 a[href]');
    mobileLinks.forEach((link) => {
      try {
        const linkPath = new URL(link.href, location.origin).pathname;
        // Don't strip custom styles on center circular FAB button
        const isFab = link.classList.contains('mobile-fab-btn') || linkPath === '/add_student';
        if (linkPath === normalizedTarget) {
          link.classList.add('text-blue-400');
          link.classList.remove('text-gray-400');
        } else {
          link.classList.remove('text-blue-400');
          if (!isFab) {
            link.classList.add('text-gray-400');
          }
        }
      } catch (_) {}
    });
  }

  // --- Safe Link Qualification ---
  function isNavigable(a) {
    if (!a || !a.href) return false;
    if (a.target && a.target !== '_self') return false;
    if (a.hasAttribute('download')) return false;
    if (a.getAttribute('rel') === 'external') return false;

    let url;
    try {
      url = new URL(a.href, location.origin);
    } catch (_) {
      return false;
    }

    if (url.origin !== location.origin) return false;

    // In-page anchor hash navigation
    if (url.pathname === location.pathname && url.search === location.search && url.hash) {
      return false;
    }

    // Explicit server-only authentication and system paths
    const bypassRoutes = ['/login', '/logout', '/manifest.json', '/sw.js', '/offline'];
    if (bypassRoutes.includes(url.pathname) || url.pathname.startsWith('/login/oauth/')) {
      return false;
    }

    return true;
  }

  // --- In-Memory Page Cache & Fetcher ---
  async function fetchPage(url) {
    const targetUrl = new URL(url, location.origin);
    const cacheKey = targetUrl.pathname;

    const cached = window.__pwaPageCache.get(cacheKey);
    // Serve from cache if available and fresh (< 2 minutes)
    if (cached && (Date.now() - cached.timestamp < 120000)) {
      return cached;
    }

    const response = await fetch(targetUrl.href, {
      headers: { 'X-Requested-With': 'PWA-Nav' }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status} fetching ${targetUrl.pathname}`);
    }

    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const entry = { html, doc, timestamp: Date.now() };
    window.__pwaPageCache.set(cacheKey, entry);
    return entry;
  }

  // --- Idle Pre-warming ---
  function prewarmCoreRoutes() {
    const prewarm = () => {
      CORE_ROUTES.forEach((route) => {
        if (!window.__pwaPageCache.has(route)) {
          fetchPage(route).catch(() => {});
        }
      });
    };

    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => prewarm(), { timeout: 2500 });
    } else {
      setTimeout(prewarm, 1200);
    }
  }

  // --- Outgoing View Teardown ---
  function teardownCurrentView() {
    // 1. Stop all video elements in the DOM
    document.querySelectorAll('video').forEach((video) => {
      try {
        if (video.srcObject && typeof video.srcObject.getTracks === 'function') {
          video.srcObject.getTracks().forEach((track) => {
            try { track.stop(); } catch (_) {}
          });
          video.srcObject = null;
        }
      } catch (_) {}
    });

    // 2. Stop all globally tracked media streams
    if (window.__activeMediaStreams && window.__activeMediaStreams.length > 0) {
      window.__activeMediaStreams.forEach((stream) => {
        try {
          if (stream && typeof stream.getTracks === 'function') {
            stream.getTracks().forEach((track) => {
              try { track.stop(); } catch (_) {}
            });
          }
        } catch (_) {}
      });
      window.__activeMediaStreams = [];
    }

    // 3. Stop specific camera controller instances if defined
    if (window.guidedCam && typeof window.guidedCam.stopCamera === 'function') {
      try { window.guidedCam.stopCamera(); } catch (_) {}
    }
    if (window.idScanner && typeof window.idScanner.stopCamera === 'function') {
      try { window.idScanner.stopCamera(); } catch (_) {}
    }
    if (typeof window.stopWebcam === 'function') {
      try { window.stopWebcam(); } catch (_) {}
    }
    if (typeof window.stopModalCamera === 'function') {
      try { window.stopModalCamera(); } catch (_) {}
    }

    // 4. Release screen wake locks
    if (typeof window.releaseScreenWakeLock === 'function') {
      try { window.releaseScreenWakeLock(); } catch (_) {}
    }

    // 5. Clean up DataTables instances to avoid memory leaks and re-init warnings
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.DataTable) {
      document.querySelectorAll('table').forEach((table) => {
        try {
          if (window.jQuery.fn.DataTable.isDataTable(table)) {
            window.jQuery(table).DataTable().destroy();
          }
        } catch (_) {}
      });
    }

    // 6. Dispatch viewleave lifecycle event
    document.dispatchEvent(new CustomEvent('pwa:viewleave'));
  }

  // --- Dynamic Style and External Script Dependency Loader ---
  async function loadMissingExternalStyles(newDoc) {
    const existingHrefs = new Set(
      Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(l => l.getAttribute('href'))
    );

    newDoc.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
      const href = link.getAttribute('href');
      if (href && !existingHrefs.has(href)) {
        const newLink = document.createElement('link');
        newLink.rel = 'stylesheet';
        newLink.href = href;
        document.head.appendChild(newLink);
        existingHrefs.add(href);
      }
    });
  }

  async function loadMissingExternalScripts(newDoc) {
    const existingSrcs = new Set(
      Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src'))
    );

    const scriptsToLoad = [];
    newDoc.querySelectorAll('script[src]').forEach((script) => {
      const src = script.getAttribute('src');
      if (src && !existingSrcs.has(src) && !src.includes('pwa.js') && !src.includes('pwa-nav.js')) {
        scriptsToLoad.push(src);
        existingSrcs.add(src);
      }
    });

    for (const src of scriptsToLoad) {
      await new Promise((resolve) => {
        const s = document.createElement('script');
        s.src = src;
        s.async = false;
        s.onload = () => resolve();
        s.onerror = () => {
          console.warn(`[PWA Nav] Failed to load external script: ${src}`);
          resolve(); // Resolve anyway so navigation is not permanently blocked
        };
        document.head.appendChild(s);
      });
    }
  }

  // --- Safe Inline Script Execution (let/const -> var) ---
  function executeInlineScripts(newDoc) {
    const scripts = [];
    newDoc.querySelectorAll('script:not([src])').forEach((s) => {
      const content = s.textContent.trim();
      // Skip serviceWorker registration or offline scripts if already executed
      if (content && !content.includes('serviceWorker.register')) {
        scripts.push(content);
      }
    });

    scripts.forEach((code) => {
      try {
        // Transpile top-level `let ` and `const ` declarations to `var `
        // to prevent `SyntaxError: Identifier has already been declared` on repeat visits
        const sanitized = code
          .replace(/(^|[;\n\r]\s*)let\s+/g, '$1var ')
          .replace(/(^|[;\n\r]\s*)const\s+/g, '$1var ');

        const scriptEl = document.createElement('script');
        scriptEl.textContent = sanitized;
        document.body.appendChild(scriptEl);
        scriptEl.remove();
      } catch (err) {
        console.warn('[PWA Nav] Inline script execution notice:', err);
      }
    });
  }

  // --- Modal Container Synchronization ---
  function swapPageModals(newDoc) {
    // Preserve persistent shell components (pwaInstallModal, pwaInstallBanner)
    // Synchronize page-level modals located outside <main> (e.g. #studentModal, #historyModal, #delete-modal)
    const knownModals = ['#studentModal', '#historyModal', '#delete-modal'];
    knownModals.forEach((selector) => {
      const currentModal = document.querySelector(selector);
      const incomingModal = newDoc.querySelector(selector);

      if (currentModal && !incomingModal) {
        currentModal.remove();
      } else if (incomingModal) {
        if (currentModal) currentModal.remove();
        document.body.appendChild(incomingModal.cloneNode(true));
      }
    });

    // Also pick up any generic modal overlays outside <main>
    newDoc.body.querySelectorAll('.fixed.inset-0[id]').forEach((incoming) => {
      if (incoming.id === 'pwaInstallModal' || incoming.id === 'pwaInstallBanner') return;
      const existing = document.getElementById(incoming.id);
      if (existing) existing.remove();
      document.body.appendChild(incoming.cloneNode(true));
    });
  }

  // --- Navigation Core Engine ---
  async function navigateTo(targetUrl, pushState = true) {
    const urlObj = new URL(targetUrl, location.origin);
    const targetPath = urlObj.pathname;

    // Immediately trigger 0ms touch feedback indicator
    updateNavActive(targetPath);
    startProgress();

    try {
      const entry = await fetchPage(urlObj.pathname + urlObj.search);
      const newDoc = entry.doc;
      const newMain = newDoc.querySelector('main');
      const currentMain = document.querySelector('main');

      if (!newMain || !currentMain) {
        // Fallback to standard full navigation if page structure differs
        window.location.href = targetUrl;
        return;
      }

      // 1. Teardown departing view
      teardownCurrentView();

      // 2. Load missing external assets
      await loadMissingExternalStyles(newDoc);
      await loadMissingExternalScripts(newDoc);

      // 3. Perform the DOM Swap
      const performSwap = () => {
        // Update document title
        if (newDoc.title) {
          document.title = newDoc.title;
        }

        // Push history state if requested
        if (pushState) {
          history.pushState({ path: targetUrl }, '', targetUrl);
        }

        // Swap main content and classes
        currentMain.innerHTML = newMain.innerHTML;
        currentMain.className = newMain.className;

        // Synchronize modals outside <main>
        swapPageModals(newDoc);

        // Synchronize active navigation indicator
        updateNavActive(targetPath);

        // Re-execute incoming page inline scripts
        executeInlineScripts(newDoc);

        // Re-render Lucide icons
        if (window.lucide && typeof window.lucide.createIcons === 'function') {
          try { window.lucide.createIcons(); } catch (_) {}
        }

        // Dispatch page lifecycle events
        document.dispatchEvent(new CustomEvent('pwa:pagechange', { detail: { path: targetUrl } }));
        document.dispatchEvent(new Event('DOMContentLoaded', { bubbles: true, cancelable: true }));

        // Scroll to top of the view
        window.scrollTo(0, 0);
      };

      // Use native View Transitions API if supported, or fallback immediately
      if ('startViewTransition' in document) {
        await document.startViewTransition(() => performSwap()).finished;
      } else {
        performSwap();
      }
    } catch (err) {
      console.warn('[PWA Nav] Navigation failure, falling back to full reload:', err);
      window.location.href = targetUrl;
    } finally {
      completeProgress();
    }
  }

  // --- Global Event Listeners ---

  // 1. Instant 0ms Visual Touch Feedback on pointerdown / touchstart
  document.addEventListener('pointerdown', (e) => {
    const anchor = e.target.closest('a[href]');
    if (!anchor || !isNavigable(anchor)) return;

    const url = new URL(anchor.href, location.origin);
    updateNavActive(url.pathname);

    // Subtle haptic pulse on supported devices
    if (navigator.vibrate) {
      try { navigator.vibrate(10); } catch (_) {}
    }

    // Pre-warm into in-memory cache immediately on touch
    if (!window.__pwaPageCache.has(url.pathname)) {
      fetchPage(url.pathname + url.search).catch(() => {});
    }
  }, { passive: true });

  // 2. Click Interception
  document.addEventListener('click', (e) => {
    // Bypass on modified clicks (Cmd/Ctrl/Shift/Alt) or non-left clicks
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
      return;
    }

    const anchor = e.target.closest('a[href]');
    if (!anchor || !isNavigable(anchor)) return;

    const url = new URL(anchor.href, location.origin);

    // Ignore clicks on already active identical path
    if (url.pathname === location.pathname && url.search === location.search) {
      e.preventDefault();
      return;
    }

    e.preventDefault();
    navigateTo(url.pathname + url.search, true);
  });

  // 3. Browser History Back/Forward Gestures (popstate)
  window.addEventListener('popstate', () => {
    navigateTo(location.pathname + location.search, false);
  });

  // 4. Initial Launch: Pre-warm core routes during idle time & set active indicator
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      updateNavActive(location.pathname);
      prewarmCoreRoutes();
    });
  } else {
    updateNavActive(location.pathname);
    prewarmCoreRoutes();
  }

  // Expose API for programmatic navigation if needed
  window.__pwaNavigate = navigateTo;
})();
