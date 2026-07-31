document.addEventListener('DOMContentLoaded', () => {
    // 1. Create the offline overlay container
    const overlay = document.createElement('div');
    overlay.id = 'offline-overlay';
    
    // Style with premium glassmorphism and animations
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        z-index: 999999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-family: 'Outfit', 'Geist', sans-serif;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    `;
    
    overlay.innerHTML = `
        <div style="text-align: center; padding: 2.5rem; max-width: 420px; width: 90%; background: rgba(255, 255, 255, 0.07); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 28px; box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2); transform: scale(0.95); transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);">
            <!-- Icon -->
            <div class="offline-icon-container" style="display: inline-flex; align-items: center; justify-content: center; width: 72px; height: 72px; border-radius: 22px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25); margin-bottom: 1.5rem; position: relative;">
                <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-wifi-off"><line x1="2" y1="2" x2="22" y2="22"/><path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.5"/><path d="M5 12.5a10.94 10.94 0 0 1 5.17-2.39"/><path d="M10.71 5.05A16 16 0 0 1 22.58 9"/><path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/><path d="M8.5 16.5a5 5 0 0 1 7 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>
            </div>
            
            <h3 style="font-size: 1.625rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: -0.02em; color: #ffffff;">Connection Lost</h3>
            <p style="font-size: 0.9rem; color: #94a3b8; line-height: 1.6; margin-bottom: 1.5rem;">We couldn't connect to the internet. Please verify your network connection.</p>
            
            <!-- Loader -->
            <div style="display: inline-flex; align-items: center; justify-content: center; gap: 10px; font-size: 0.8rem; color: #3b82f6; background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.15); padding: 8px 16px; border-radius: 99px;">
                <span class="offline-spinner" style="width: 14px; height: 14px; border: 2px solid rgba(59, 130, 246, 0.2); border-top-color: #3b82f6; border-radius: 50%; animation: spin 1s linear infinite;"></span>
                <span style="font-weight: 600;">Attempting to reconnect...</span>
            </div>
        </div>
        
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            .offline-icon-container svg {
                animation: wifi-pulse 2s infinite ease-in-out;
            }
            @keyframes wifi-pulse {
                0%, 100% { transform: scale(1); opacity: 1; filter: drop-shadow(0 0 0px rgba(239, 68, 68, 0)); }
                50% { transform: scale(1.06); opacity: 0.8; filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.4)); }
            }
        </style>
    `;
    
    document.body.appendChild(overlay);
    
    const card = overlay.querySelector('div');
    
    function updateOnlineStatus() {
        if (navigator.onLine) {
            overlay.style.opacity = '0';
            overlay.style.pointerEvents = 'none';
            card.style.transform = 'scale(0.95)';
        } else {
            overlay.style.opacity = '1';
            overlay.style.pointerEvents = 'all';
            card.style.transform = 'scale(1)';
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Check status immediately on load
    updateOnlineStatus();
});
