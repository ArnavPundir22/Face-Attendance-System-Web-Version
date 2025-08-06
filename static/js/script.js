window.onload = () => {
  const video = document.getElementById('camera');
  const output = document.getElementById('output');

  const fields = ['id', 'name', 'program', 'branch', 'mobile', 'gmail', 'total', 'last', 'welcome', 'attendance-time'];
  const elements = {};
  fields.forEach(f => elements[f] = document.getElementById(f));

  const faceSnapshot = document.getElementById('face-snapshot');

  navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } })
    .then(stream => {
      video.srcObject = stream;
      setInterval(() => captureAndSendFrame(video), 3000);
    })
    .catch(err => {
      console.error('Camera error:', err);
      output.innerText = 'Failed to access camera';
    });

  function captureAndSendFrame(video) {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);

    const dataURL = canvas.toDataURL('image/jpeg');

    fetch('/process_frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataURL })
    })
      .then(res => res.json())
      .then(data => {
        if (data.name) {
          output.innerText = data.message || 'Matched';

          elements['id'].innerText = data.id;
          elements['name'].innerText = data.name;
          elements['program'].innerText = data.program;
          elements['branch'].innerText = data.branch;
          elements['mobile'].innerText = data.mobile;
          elements['gmail'].innerText = data.gmail || '';
          elements['total'].innerText = data.total || '';
          elements['last'].innerText = data.last;
          elements['welcome'].innerText = `✅ Welcome, ${data.name}`;
          elements['attendance-time'].innerText = `✅ Attendance marked at ${data.last}`;

          if (faceSnapshot && data.face_image) {
            faceSnapshot.src = `data:image/jpeg;base64,${data.face_image}`;
          }
        } else {
          output.innerText = data.message || 'Unknown face';
        }
      })
      .catch(err => {
        console.error('Error:', err);
        output.innerText = 'Error sending image';
      });
  }
};

