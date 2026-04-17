// ── PDF Upload Panel ──────────────────────────────────────────────────────

eel.expose(showPDFUpload);
function showPDFUpload() {
    // Remove existing panel if any
    const existing = document.getElementById('pdf-upload-panel');
    if (existing) existing.remove();

    const panel = document.createElement('div');
    panel.id = 'pdf-upload-panel';
    panel.innerHTML = `
        <div id="pdf-upload-box">
            <p id="pdf-upload-title">📄 Upload your PDF</p>
            <p id="pdf-upload-sub">Drag & drop or click to browse</p>
            <input type="file" id="pdf-file-input" accept=".pdf" />
            <label for="pdf-file-input" id="pdf-upload-btn">Choose PDF</label>
            <p id="pdf-upload-status"></p>
        </div>
    `;
    document.body.appendChild(panel);

    // Inject styles
    const style = document.createElement('style');
    style.id = 'pdf-upload-style';
    style.textContent = `
        #pdf-upload-panel {
            position: fixed; bottom: 100px; left: 50%;
            transform: translateX(-50%);
            z-index: 9999; animation: fadeInUp 0.3s ease;
        }
        #pdf-upload-box {
            background: rgba(15,15,25,0.95);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 16px; padding: 24px 32px;
            text-align: center; min-width: 320px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }
        #pdf-upload-title { color: #fff; font-size: 16px; font-weight: 600; margin-bottom: 6px; }
        #pdf-upload-sub   { color: rgba(255,255,255,0.5); font-size: 13px; margin-bottom: 16px; }
        #pdf-file-input   { display: none; }
        #pdf-upload-btn {
            display: inline-block; padding: 10px 24px;
            background: #1F4E79; color: #fff;
            border-radius: 8px; cursor: pointer;
            font-size: 14px; transition: background 0.2s;
        }
        #pdf-upload-btn:hover { background: #2E75B6; }
        #pdf-upload-status { color: #90EE90; font-size: 13px; margin-top: 12px; min-height: 20px; }
        @keyframes fadeInUp {
            from { opacity:0; transform: translateX(-50%) translateY(20px); }
            to   { opacity:1; transform: translateX(-50%) translateY(0); }
        }
    `;
    document.head.appendChild(style);

    // Handle file selection
    document.getElementById('pdf-file-input').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;

        document.getElementById('pdf-upload-status').textContent = 'Uploading ' + file.name + '...';

        const reader = new FileReader();
        reader.onload = async function(ev) {
            // Send base64 to Python
            const base64Data = ev.target.result.split(',')[1];
            const savedPath  = await eel.receivePDFUpload(file.name, base64Data)();

            document.getElementById('pdf-upload-status').textContent = '✓ Uploaded! Converting now...';

            setTimeout(() => {
                const panel = document.getElementById('pdf-upload-panel');
                if (panel) panel.remove();
                const style = document.getElementById('pdf-upload-style');
                if (style) style.remove();
            }, 2500);
        };
        reader.readAsDataURL(file);
    });
}
