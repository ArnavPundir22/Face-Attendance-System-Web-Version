/**
 * ID Card Camera Scanner & OCR Auto-Fill Engine
 * BioSecure AI
 */

class IDCardScanner {
  constructor(options = {}) {
    this.videoElement = document.getElementById(options.videoId || 'idCardVideo');
    this.canvasElement = document.getElementById(options.canvasId || 'idCardCanvas');
    this.stream = null;
    this.isScanning = false;
    this.selectedCameraId = null;

    this.onParsedCallback = options.onParsed || null;
  }

  async startCamera() {
    if (!this.videoElement) return;

    try {
      const constraints = {
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          facingMode: { ideal: "environment" } // Prefer back camera on mobile
        }
      };

      if (this.selectedCameraId) {
        constraints.video.deviceId = { exact: this.selectedCameraId };
      }

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.videoElement.srcObject = this.stream;
      await this.videoElement.play();

      this.populateCameraDevices();
    } catch (err) {
      console.error("ID Card Camera access error:", err);
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
  }

  async populateCameraDevices() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');
      const select = document.getElementById('idCameraSelect');
      if (!select) return;

      select.innerHTML = '';
      if (videoDevices.length > 1) {
        select.classList.remove('hidden');
        videoDevices.forEach((device, index) => {
          const option = document.createElement('option');
          option.value = device.deviceId;
          option.text = device.label || `Camera ${index + 1}`;
          if (this.stream && this.stream.getVideoTracks()[0].getSettings().deviceId === device.deviceId) {
            option.selected = true;
          }
          select.appendChild(option);
        });

        select.onchange = (e) => {
          this.selectedCameraId = e.target.value;
          this.stopCamera();
          this.startCamera();
        };
      }
    } catch (e) {
      console.warn("Could not enumerate camera devices:", e);
    }
  }

  captureFrameDataUrl() {
    if (!this.videoElement || !this.canvasElement) return null;
    const video = this.videoElement;
    const canvas = this.canvasElement;

    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.92);
  }

  async scanImageSource(imageSrc, statusCallback) {
    if (statusCallback) statusCallback("⚡ Sending image to Pretrained Neural OCR Engine...", 20);

    // Direct fast call to Flask Backend RapidOCR endpoint /api/ocr_id_card
    try {
      if (statusCallback) statusCallback("🔍 Detecting Text & Extracting Student Profile...", 60);

      const response = await fetch('/api/ocr_id_card', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_data: imageSrc
        })
      });

      const resData = await response.json();
      if (resData.success) {
        if (statusCallback) statusCallback("✨ Extraction complete! Auto-filling form...", 100);
        return {
          parsed: resData.parsed_data || {},
          raw_text: resData.raw_text || ""
        };
      }
    } catch (err) {
      console.error("Backend OCR error:", err);
    }

    if (statusCallback) statusCallback("Done.", 100);
    return { parsed: {}, raw_text: "" };
  }
}

// Attach to window object
window.IDCardScanner = IDCardScanner;
