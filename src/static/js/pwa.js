/**
 * BioSecure AI — Progressive Web App (PWA) Client Manager
 */

(function () {
  'use strict';

  let deferredPrompt = null;

  // Register Service Worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js', { scope: '/' })
        .then((registration) => {
          console.log('[PWA Manager] ServiceWorker registered with scope:', registration.scope);

          // Check for Service Worker updates
          registration.addEventListener('updatefound', () => {
            const installingWorker = registration.installing;
            if (installingWorker) {
              installingWorker.addEventListener('statechange', () => {
                if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  showUpdateToast(registration);
                }
              });
            }
          });
        })
        .catch((error) => {
          console.error('[PWA Manager] ServiceWorker registration failed:', error);
        });
    });
  }

  // Intercept beforeinstallprompt event
  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent standard automatic browser prompt banner
    e.preventDefault();
    deferredPrompt = e;
    console.log('[PWA Manager] beforeinstallprompt event captured.');

    // Reveal custom PWA install buttons across app UI
    showInstallButtons();
  });

  // Handle app installed event
  window.addEventListener('appinstalled', (evt) => {
    console.log('[PWA Manager] BioSecure AI PWA was installed successfully.');
    deferredPrompt = null;
    hideInstallButtons();
    showToast('BioSecure AI App Installed Successfully!', 'success');
  });

  // Function to reveal install buttons in navbar/sidebar/modal
  function showInstallButtons() {
    const installBtns = document.querySelectorAll('.pwa-install-btn');
    installBtns.forEach((btn) => {
      btn.classList.remove('hidden');
      btn.style.display = 'inline-flex';
    });

    // Auto show install banner/modal if user hasn't dismissed it this session
    if (!sessionStorage.getItem('pwa_banner_dismissed')) {
      const banner = document.getElementById('pwaInstallBanner');
      if (banner) {
        banner.classList.remove('hidden');
        banner.style.display = 'flex';
      }
    }
  }

  function hideInstallButtons() {
    const installBtns = document.querySelectorAll('.pwa-install-btn');
    installBtns.forEach((btn) => {
      btn.classList.add('hidden');
      btn.style.display = 'none';
    });
    const banner = document.getElementById('pwaInstallBanner');
    if (banner) {
      banner.classList.add('hidden');
      banner.style.display = 'none';
    }
  }

  // Global trigger function for install buttons
  window.installPWA = async function () {
    if (!deferredPrompt) {
      console.log('[PWA Manager] No deferred prompt available or app already installed.');
      showToast('App is already installed or standard install prompt is unavailable.', 'info');
      return;
    }

    // Trigger the stored prompt
    deferredPrompt.prompt();

    const choiceResult = await deferredPrompt.userChoice;
    console.log('[PWA Manager] User prompt outcome:', choiceResult.outcome);

    if (choiceResult.outcome === 'accepted') {
      console.log('[PWA Manager] User accepted the PWA install prompt');
      hideInstallButtons();
    } else {
      console.log('[PWA Manager] User dismissed the PWA install prompt');
    }
    deferredPrompt = null;
  };

  window.dismissPWABanner = function () {
    sessionStorage.setItem('pwa_banner_dismissed', 'true');
    const banner = document.getElementById('pwaInstallBanner');
    if (banner) {
      banner.classList.add('hidden');
      banner.style.display = 'none';
    }
  };

  // Toast notification system
  function showToast(message, type = 'info') {
    let toastContainer = document.getElementById('pwa-toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'pwa-toast-container';
      toastContainer.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 99999;
        display: flex;
        flex-direction: column;
        gap: 10px;
        pointer-events: none;
      `;
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    const borderCol = type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : '#3b82f6';
    toast.style.cssText = `
      background: rgba(15, 23, 42, 0.92);
      border: 1px solid ${borderCol};
      color: #ffffff;
      padding: 12px 20px;
      border-radius: 12px;
      font-family: 'Outfit', 'Geist', sans-serif;
      font-size: 0.875rem;
      font-weight: 500;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      backdrop-filter: blur(12px);
      display: flex;
      align-items: center;
      gap: 10px;
      pointer-events: auto;
      transform: translateY(20px);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    `;

    toast.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${borderCol}" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
      <span>${message}</span>
    `;

    toastContainer.appendChild(toast);
    requestAnimationFrame(() => {
      toast.style.transform = 'translateY(0)';
      toast.style.opacity = '1';
    });

    setTimeout(() => {
      toast.style.transform = 'translateY(10px)';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function showUpdateToast(registration) {
    let updateToast = document.getElementById('pwa-update-toast');
    if (updateToast) return;

    updateToast = document.createElement('div');
    updateToast.id = 'pwa-update-toast';
    updateToast.style.cssText = `
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%) translateY(30px);
      background: rgba(11, 19, 38, 0.95);
      border: 1px solid rgba(59, 130, 246, 0.4);
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      padding: 14px 24px;
      border-radius: 16px;
      z-index: 999999;
      display: flex;
      align-items: center;
      gap: 16px;
      backdrop-filter: blur(16px);
      color: white;
      font-family: 'Outfit', sans-serif;
      opacity: 0;
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    `;

    updateToast.innerHTML = `
      <div style="display: flex; flex-direction: column;">
        <span style="font-weight: 700; font-size: 0.95rem; color: #60a5fa;">New Version Available</span>
        <span style="font-size: 0.8rem; color: #94a3b8;">A new version of BioSecure AI is ready.</span>
      </div>
      <button id="pwa-refresh-btn" style="background: linear-gradient(135deg, #3b82f6, #2563eb); border: none; color: white; padding: 8px 16px; border-radius: 10px; font-weight: 600; font-size: 0.85rem; cursor: pointer; box-shadow: 0 4px 12px rgba(59,130,246,0.3);">
        Refresh App
      </button>
    `;

    document.body.appendChild(updateToast);
    requestAnimationFrame(() => {
      updateToast.style.transform = 'translateX(-50%) translateY(0)';
      updateToast.style.opacity = '1';
    });

    document.getElementById('pwa-refresh-btn').addEventListener('click', () => {
      if (registration.waiting) {
        registration.waiting.postMessage({ action: 'skipWaiting' });
      }
      window.location.reload();
    });
  }
})();
