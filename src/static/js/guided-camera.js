/**
 * Guided Camera & Real-Time Auto-Capture Engine
 * BioSecure AI — Student Registration
 */

(function () {
  'use strict';

  class GuidedCameraEngine {
    constructor(config = {}) {
      this.video = document.getElementById(config.videoId || 'guidedVideo');
      this.canvas = document.getElementById(config.canvasId || 'guidedCanvas');
      this.stencil = document.getElementById(config.stencilId || 'guidedStencil');
      this.statusBadge = document.getElementById(config.statusBadgeId || 'guidanceStatusBadge');
      this.statusText = document.getElementById(config.statusTextId || 'guidanceStatusText');
      this.statusIcon = document.getElementById(config.statusIconId || 'guidanceStatusIcon');
      this.progressRing = document.getElementById(config.progressRingId || 'autoCaptureRing');
      this.progressText = document.getElementById(config.progressTextId || 'autoCaptureCountdownText');
      this.shutterFlash = document.getElementById(config.shutterFlashId || 'shutterFlash');
      
      // Control UI Elements
      this.autoCaptureToggle = document.getElementById(config.autoCaptureToggleId || 'autoCaptureToggle');
      this.manualSnapBtn = document.getElementById(config.manualSnapBtnId || 'manualSnapBtn');
      this.retakeBtn = document.getElementById(config.retakeBtnId || 'retakeBtn');
      this.cameraSelect = document.getElementById(config.cameraSelectId || 'cameraSelect');
      this.capturedPreview = document.getElementById(config.capturedPreviewId || 'capturedPreview');
      this.capturedImg = document.getElementById(config.capturedImgId || 'capturedImg');
      this.cameraContainer = document.getElementById(config.cameraContainerId || 'guidedCameraContainer');
      this.fileInput = document.querySelector(config.fileInputSelector || 'input[name="photo"]');

      // State variables
      this.stream = null;
      this.animFrameId = null;
      this.isAutoCaptureEnabled = true;
      this.isCapturing = false;
      this.isCaptured = false;

      // Guideline & Auto-Capture parameters
      this.stableStartTime = null;
      this.requiredStableDuration = 1200; // ms (1.2 seconds)
      this.lastFaceBox = null;
      this.audioCtx = null;
      this.faceDetectorInstance = null;
      this.isModelLoading = false;

      this.init();
    }

    async init() {
      this.bindEvents();
      this.initFaceDetector();
    }

    bindEvents() {
      if (this.autoCaptureToggle) {
        this.autoCaptureToggle.addEventListener('change', (e) => {
          this.isAutoCaptureEnabled = e.target.checked;
          if (!this.isAutoCaptureEnabled) {
            this.resetProgressRing();
            this.updateStatus('manual', 'Manual Capture Mode (Click Snap Photo)', 'camera');
          }
        });
      }

      if (this.manualSnapBtn) {
        this.manualSnapBtn.addEventListener('click', () => {
          this.capturePhoto('Manual Capture');
        });
      }

      if (this.retakeBtn) {
        this.retakeBtn.addEventListener('click', () => {
          this.resetToLiveStream();
        });
      }

      if (this.cameraSelect) {
        this.cameraSelect.addEventListener('change', () => {
          if (this.stream) {
            this.startCamera();
          }
        });
      }

      // Wake lock handling when page visibility changes
      document.addEventListener('visibilitychange', async () => {
        if (document.visibilityState === 'visible' && this.stream && !this.isCaptured) {
          await this.requestWakeLock();
        }
      });
    }

    async initFaceDetector() {
      // 1. Try native HTML5 FaceDetector API if available in browser
      if ('FaceDetector' in window) {
        try {
          // @ts-ignore
          this.faceDetectorInstance = new window.FaceDetector({ fastMode: true, maxFaces: 4 });
          console.log('GuidedCamera: Using Native HTML5 FaceDetector API.');
        } catch (e) {
          console.warn('Native FaceDetector initialization failed, using fallback engine.', e);
        }
      }

      // 2. Try loading face-api.js or vladmandic/face-api if window.faceapi present
      if (!this.faceDetectorInstance && window.faceapi) {
        try {
          this.isModelLoading = true;
          await window.faceapi.nets.tinyFaceDetector.loadFromUri('https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model');
          this.isModelLoading = false;
          console.log('GuidedCamera: Loaded face-api.js TinyFaceDetector.');
        } catch (e) {
          console.warn('face-api.js model download error, using high-speed fallback analysis.', e);
          this.isModelLoading = false;
        }
      }
    }

    async startCamera() {
      try {
        if (this.stream) {
          this.stopCamera();
        }

        const isRemoteIP = location.hostname !== 'localhost' && location.hostname !== '127.0.0.1';
        const isSecureCtx = window.isSecureContext && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function';

        if (isRemoteIP && !isSecureCtx) {
          console.warn('GuidedCamera: Live camera stream requires HTTPS when accessing over IP on mobile browsers.');
          this.updateStatus('warning', 'HTTPS Required for Live Mobile Stream (Or use Upload File tab)', 'shield-alert');
          
          // Switch tab to file upload where native mobile camera snap works over HTTP
          const tabFileUpload = document.getElementById('tabFileUpload');
          if (tabFileUpload) {
            setTimeout(() => {
              const msg = document.getElementById('messageBox');
              if (msg) {
                msg.className = "p-4 mb-6 rounded-xl font-medium text-center shadow-md bg-amber-500/10 text-amber-300 border border-amber-500/30 text-xs";
                msg.innerHTML = `🔒 <strong>Browser Security Notice:</strong> Live streaming on mobile browsers requires <strong>HTTPS</strong> when opening over IP (<code>${location.origin}</code>).<br>Switched to <strong>Upload File</strong> mode where you can snap photos directly with your phone's native camera!`;
                msg.classList.remove('hidden');
              }
              tabFileUpload.click();
            }, 800);
          }
          return;
        }

        const selectedDeviceId = this.cameraSelect ? this.cameraSelect.value : null;
        const constraints = {
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: selectedDeviceId ? undefined : 'user',
            deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined
          },
          audio: false
        };

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('navigator.mediaDevices.getUserMedia unavailable');
        }

        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
        this.video.srcObject = this.stream;
        await this.video.play();

        // Enumerate video devices for selection dropdown
        this.enumerateDevices();

        // Request Screen Wake Lock so display stays active on mobile
        await this.requestWakeLock();

        this.isCaptured = false;
        if (this.cameraContainer) this.cameraContainer.classList.remove('hidden');
        if (this.capturedPreview) this.capturedPreview.classList.add('hidden');
        this.resetProgressRing();

        // Start real-time analysis loop
        this.detectLoop();
      } catch (err) {
        console.error('GuidedCamera: Camera access error:', err);
        const isRemoteIP = location.hostname !== 'localhost' && location.hostname !== '127.0.0.1';
        if (isRemoteIP && !window.isSecureContext) {
          this.updateStatus('warning', 'HTTPS Required on Remote Mobile IP', 'shield-alert');
        } else {
          this.updateStatus('warning', 'Camera Access Denied or Unavailable', 'alert-triangle');
        }
      }
    }

    async enumerateDevices() {
      if (!this.cameraSelect || this.cameraSelect.options.length > 1) return;

      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');

        this.cameraSelect.innerHTML = '<option value="">Default Front Camera</option>';
        videoDevices.forEach((device, index) => {
          const option = document.createElement('option');
          option.value = device.deviceId;
          option.text = device.label || `Camera ${index + 1}`;
          this.cameraSelect.appendChild(option);
        });

        if (videoDevices.length > 1) {
          this.cameraSelect.classList.remove('hidden');
        }
      } catch (e) {
        console.warn('Could not enumerate cameras:', e);
      }
    }

    stopCamera() {
      if (this.animFrameId) {
        cancelAnimationFrame(this.animFrameId);
        this.animFrameId = null;
      }
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }
    }

    resetToLiveStream() {
      this.isCaptured = false;
      if (this.capturedPreview) this.capturedPreview.classList.add('hidden');
      if (this.cameraContainer) this.cameraContainer.classList.remove('hidden');
      this.resetProgressRing();
      
      if (!this.stream) {
        this.startCamera();
      } else {
        this.detectLoop();
      }
    }

    async requestWakeLock() {
      try {
        if ('wakeLock' in navigator) {
          await navigator.wakeLock.request('screen');
        }
      } catch (_) {}
    }

    detectLoop() {
      if (this.isCaptured || !this.stream) return;

      this.processFrame();
      this.animFrameId = requestAnimationFrame(() => this.detectLoop());
    }

    async processFrame() {
      if (this.video.readyState !== 4 || this.video.paused) return;

      const videoWidth = this.video.videoWidth;
      const videoHeight = this.video.videoHeight;
      if (!videoWidth || !videoHeight) return;

      // Define target guided oval coordinates relative to video dimensions
      const targetOval = {
        cx: videoWidth / 2,
        cy: videoHeight / 2,
        rx: (videoWidth * 0.62) / 2,
        ry: (videoHeight * 0.72) / 2,
        w: videoWidth * 0.62,
        h: videoHeight * 0.72
      };

      let faces = await this.detectFaces(videoWidth, videoHeight);

      if (!faces || faces.length === 0) {
        this.updateStencilState('searching');
        this.updateStatus('searching', 'Position your face inside the oval', 'scan');
        this.resetProgressRing();
        return;
      }

      if (faces.length > 1) {
        this.updateStencilState('warning');
        this.updateStatus('warning', 'Multiple faces detected! Ensure 1 person only', 'users');
        this.resetProgressRing();
        return;
      }

      const face = faces[0];
      const faceBox = face.box; // { x, y, width, height }
      const faceCenterX = faceBox.x + faceBox.width / 2;
      const faceCenterY = faceBox.y + faceBox.height / 2;

      // Guidelines Checks
      // 1. Centering check (tolerance 16% of oval size)
      const maxOffCenterX = targetOval.w * 0.16;
      const maxOffCenterY = targetOval.h * 0.16;
      const dx = Math.abs(faceCenterX - targetOval.cx);
      const dy = Math.abs(faceCenterY - targetOval.cy);

      if (dx > maxOffCenterX || dy > maxOffCenterY) {
        this.updateStencilState('warning');
        let hint = 'Center your face in the oval';
        if (faceCenterX < targetOval.cx - maxOffCenterX) hint = 'Move slightly Right ➡️';
        else if (faceCenterX > targetOval.cx + maxOffCenterX) hint = 'Move slightly Left ⬅️';
        else if (faceCenterY < targetOval.cy - maxOffCenterY) hint = 'Move slightly Down ⬇️';
        else if (faceCenterY > targetOval.cy + maxOffCenterY) hint = 'Move slightly Up ⬆️';
        
        this.updateStatus('warning', hint, 'move');
        this.resetProgressRing();
        return;
      }

      // 2. Scale / Distance check (Face height should be 38% - 78% of target oval height)
      const minFaceHeight = targetOval.h * 0.38;
      const maxFaceHeight = targetOval.h * 0.78;

      if (faceBox.height < minFaceHeight) {
        this.updateStencilState('warning');
        this.updateStatus('warning', 'Too far away — Move closer to camera 🔍', 'zoom-in');
        this.resetProgressRing();
        return;
      }

      if (faceBox.height > maxFaceHeight) {
        this.updateStencilState('warning');
        this.updateStatus('warning', 'Too close — Step back slightly 🔍', 'zoom-out');
        this.resetProgressRing();
        return;
      }

      // All guidelines satisfied! Face is perfectly positioned!
      this.updateStencilState('success');
      this.updateStatus('success', '✨ Perfect Alignment! Hold Still...', 'check-circle');

      if (this.isAutoCaptureEnabled && !this.isCapturing) {
        this.handleAutoCaptureCountdown(faceBox);
      }
    }

    async detectFaces(vWidth, vHeight) {
      // Path 1: Native HTML5 FaceDetector
      if (this.faceDetectorInstance) {
        try {
          const detected = await this.faceDetectorInstance.detect(this.video);
          if (detected && detected.length > 0) {
            return detected.map(d => ({
              box: {
                x: d.boundingBox.x,
                y: d.boundingBox.y,
                width: d.boundingBox.width,
                height: d.boundingBox.height
              }
            }));
          }
        } catch (_) {}
      }

      // Path 2: face-api.js TinyFaceDetector
      if (window.faceapi && window.faceapi.nets && window.faceapi.nets.tinyFaceDetector.params) {
        try {
          const detections = await window.faceapi.detectAllFaces(
            this.video,
            new window.faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.4 })
          );
          if (detections && detections.length > 0) {
            return detections.map(d => ({
              box: {
                x: d.box.x,
                y: d.box.y,
                width: d.box.width,
                height: d.box.height
              }
            }));
          }
        } catch (_) {}
      }

      // Path 3: Built-in Canvas Facial Region Analysis (Skin tone & luminance bounding algorithm)
      return this.analyzeCanvasFaceRegion(vWidth, vHeight);
    }

    analyzeCanvasFaceRegion(vWidth, vHeight) {
      if (!this.canvas) return [];
      const ctx = this.canvas.getContext('2d', { willReadFrequently: true });
      this.canvas.width = 160;
      this.canvas.height = 120;
      ctx.drawImage(this.video, 0, 0, 160, 120);

      const imgData = ctx.getImageData(0, 0, 160, 120);
      const data = imgData.data;

      let minX = 160, maxX = 0, minY = 120, maxY = 0;
      let count = 0;

      for (let y = 0; y < 120; y += 2) {
        for (let x = 0; x < 160; x += 2) {
          const idx = (y * 160 + x) * 4;
          const r = data[idx];
          const g = data[idx + 1];
          const b = data[idx + 2];

          // Normalized skin tone thresholding in YCbCr / RGB space
          if (r > 60 && g > 40 && b > 20 && r > b && Math.abs(r - g) > 12 && (r - Math.min(g, b)) > 15) {
            count++;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
          }
        }
      }

      if (count > 180 && (maxX - minX) > 20 && (maxY - minY) > 25) {
        const scaleX = vWidth / 160;
        const scaleY = vHeight / 120;

        return [{
          box: {
            x: minX * scaleX,
            y: minY * scaleY,
            width: (maxX - minX) * scaleX,
            height: (maxY - minY) * scaleY
          }
        }];
      }

      return [];
    }

    handleAutoCaptureCountdown(currentBox) {
      const now = performance.now();

      if (!this.stableStartTime || !this.lastFaceBox) {
        this.stableStartTime = now;
        this.lastFaceBox = currentBox;
        return;
      }

      const dx = Math.abs((currentBox.x + currentBox.width / 2) - (this.lastFaceBox.x + this.lastFaceBox.width / 2));
      const dy = Math.abs((currentBox.y + currentBox.height / 2) - (this.lastFaceBox.y + this.lastFaceBox.height / 2));

      if (dx > currentBox.width * 0.08 || dy > currentBox.height * 0.08) {
        this.stableStartTime = now;
        this.lastFaceBox = currentBox;
        this.resetProgressRing();
        return;
      }

      const elapsed = now - this.stableStartTime;
      const progressRatio = Math.min(elapsed / this.requiredStableDuration, 1.0);

      this.updateProgressRing(progressRatio);

      if (elapsed >= this.requiredStableDuration && !this.isCapturing) {
        this.isCapturing = true;
        this.capturePhoto('Auto Capture (Guidelines Verified)');
      }
    }

    updateProgressRing(ratio) {
      if (!this.progressRing) return;

      const circle = this.progressRing;
      const radius = circle.r.baseVal.value;
      const circumference = 2 * Math.PI * radius;

      circle.style.strokeDasharray = `${circumference} ${circumference}`;
      const offset = circumference - (ratio * circumference);
      circle.style.strokeDashoffset = offset;

      if (this.progressText) {
        const remaining = Math.max(Math.ceil((1.0 - ratio) * 1.5), 0);
        this.progressText.textContent = remaining > 0 ? `${remaining}s` : '✓';
      }
    }

    resetProgressRing() {
      this.stableStartTime = null;
      this.updateProgressRing(0);
      if (this.progressText) this.progressText.textContent = '';
    }

    updateStencilState(state) {
      if (!this.stencil) return;
      this.stencil.className = `guided-oval-stencil state-${state}`;
    }

    updateStatus(type, text, iconName) {
      if (!this.statusText) return;
      this.statusText.textContent = text;

      if (this.statusBadge) {
        this.statusBadge.className = 'px-4 py-2 rounded-full backdrop-blur-md text-xs font-semibold flex items-center gap-2 border shadow-lg transition-all duration-300 ';
        if (type === 'success') {
          this.statusBadge.classList.add('bg-emerald-500/20', 'text-emerald-300', 'border-emerald-500/40');
        } else if (type === 'warning') {
          this.statusBadge.classList.add('bg-rose-500/20', 'text-rose-300', 'border-rose-500/40');
        } else if (type === 'searching') {
          this.statusBadge.classList.add('bg-blue-500/20', 'text-blue-300', 'border-blue-500/40');
        } else {
          this.statusBadge.classList.add('bg-gray-800/60', 'text-gray-300', 'border-gray-600/40');
        }
      }

      if (this.statusIcon && window.lucide) {
        this.statusIcon.setAttribute('data-lucide', iconName || 'camera');
        window.lucide.createIcons();
      }
    }

    capturePhoto(sourceTag = 'Guided Capture') {
      if (this.isCaptured) return;
      this.isCaptured = true;

      // 1. Play Camera Shutter Flash Animation
      if (this.shutterFlash) {
        this.shutterFlash.classList.add('active');
        setTimeout(() => this.shutterFlash.classList.remove('active'), 150);
      }

      // 2. Play Web Audio Synthetic Shutter Sound
      this.playShutterSound();

      // 3. Draw high resolution frame to Canvas
      const vW = this.video.videoWidth;
      const vH = this.video.videoHeight;
      this.canvas.width = vW;
      this.canvas.height = vH;

      const ctx = this.canvas.getContext('2d');
      ctx.drawImage(this.video, 0, 0, vW, vH);

      const dataUrl = this.canvas.toDataURL('image/jpeg', 0.95);

      // 4. Update Preview UI
      if (this.capturedImg) {
        this.capturedImg.src = dataUrl;
      }
      if (this.cameraContainer) this.cameraContainer.classList.add('hidden');
      if (this.capturedPreview) this.capturedPreview.classList.remove('hidden');

      // 5. Convert to Blob & populate HTML form File Input using DataTransfer
      this.canvas.toBlob((blob) => {
        if (blob && this.fileInput) {
          const file = new File([blob], `student_photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
          const dt = new DataTransfer();
          dt.items.add(file);
          this.fileInput.files = dt.files;

          this.fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }, 'image/jpeg', 0.95);

      // 6. Stop camera loop until retake
      this.stopCamera();
      this.isCapturing = false;
    }

    playShutterSound() {
      try {
        if (!this.audioCtx) {
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          if (AudioContext) this.audioCtx = new AudioContext();
        }

        if (this.audioCtx && this.audioCtx.state === 'suspended') {
          this.audioCtx.resume();
        }

        if (!this.audioCtx) return;

        const now = this.audioCtx.currentTime;
        
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(120, now + 0.08);

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);
        osc.start(now);
        osc.stop(now + 0.08);

        const osc2 = this.audioCtx.createOscillator();
        const gain2 = this.audioCtx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(1400, now + 0.04);
        osc2.frequency.exponentialRampToValueAtTime(400, now + 0.12);

        gain2.gain.setValueAtTime(0.2, now + 0.04);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.12);

        osc2.connect(gain2);
        gain2.connect(this.audioCtx.destination);
        osc2.start(now + 0.04);
        osc2.stop(now + 0.12);
      } catch (e) {
        console.warn('Audio synth failed:', e);
      }
    }
  }

  window.GuidedCameraEngine = GuidedCameraEngine;
})();
