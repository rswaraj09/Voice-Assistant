// ── PDF Upload Panel ──────────────────────────────────────────────────────

eel.expose(showPDFUpload);
function showPDFUpload() {
    console.log("[PDF] Showing upload panel...");
    // Remove existing panel if any
    const existing = document.getElementById('pdf-upload-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'pdf-upload-overlay';
    overlay.innerHTML = `
        <div id="pdf-upload-box">
            <div id="pdf-close-btn">&times;</div>
            <div class="pdf-icon">📄</div>
            <p id="pdf-upload-title">Convert PDF to Excel</p>
            <p id="pdf-upload-sub">Select the file you want to transform</p>
            
            <div id="pdf-drop-zone">
                <input type="file" id="pdf-file-input" accept=".pdf" />
                <label for="pdf-file-input" id="pdf-upload-btn">Choose PDF File</label>
                <p style="margin-top: 10px; font-size: 12px; color: rgba(255,255,255,0.4);">or drag and drop here</p>
            </div>
            
            <p id="pdf-upload-status"></p>
        </div>
    `;
    document.body.appendChild(overlay);

    // Inject styles
    const style = document.createElement('style');
    style.id = 'pdf-upload-style';
    style.textContent = `
        #pdf-upload-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            display: flex; align-items: center; justify-content: center;
            z-index: 10000; animation: fadeIn 0.4s ease;
        }
        #pdf-upload-box {
            background: linear-gradient(145deg, #0f0f1a, #1a1a2e);
            border: 1px solid rgba(0, 170, 255, 0.4);
            border-radius: 24px; padding: 40px;
            text-align: center; width: 420px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6), 0 0 20px rgba(0, 170, 255, 0.1);
            position: relative;
        }
        #pdf-close-btn {
            position: absolute; top: 15px; right: 20px;
            color: rgba(255,255,255,0.3); font-size: 24px; cursor: pointer;
            transition: color 0.2s;
        }
        #pdf-close-btn:hover { color: #ff4d4d; }
        .pdf-icon { font-size: 48px; margin-bottom: 15px; }
        #pdf-upload-title { color: #fff; font-size: 22px; font-weight: 700; margin-bottom: 5px; }
        #pdf-upload-sub   { color: rgba(255,255,255,0.6); font-size: 14px; margin-bottom: 30px; }
        
        #pdf-drop-zone {
            border: 2px dashed rgba(0, 170, 255, 0.3);
            border-radius: 16px; padding: 30px 20px;
            background: rgba(255,255,255,0.03);
            transition: all 0.3s;
        }
        #pdf-drop-zone.dragover {
            background: rgba(0, 170, 255, 0.05);
            border-color: #00AAFF;
        }
        
        #pdf-file-input { display: none; }
        #pdf-upload-btn {
            display: inline-block; padding: 12px 30px;
            background: #00AAFF; color: #fff;
            border-radius: 12px; cursor: pointer;
            font-size: 15px; font-weight: 600;
            transition: all 0.2s; box-shadow: 0 4px 15px rgba(0, 170, 255, 0.3);
        }
        #pdf-upload-btn:hover { background: #0088cc; transform: translateY(-2px); }
        #pdf-upload-status { color: #00FF99; font-size: 14px; margin-top: 20px; min-height: 20px; }
        
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    `;
    document.head.appendChild(style);

    const closeBtn = document.getElementById('pdf-close-btn');
    closeBtn.onclick = () => {
        overlay.remove(); style.remove();
    };

    // Handle file selection
    const fileInput = document.getElementById('pdf-file-input');
    fileInput.addEventListener('change', function(e) {
        handleFile(e.target.files[0]);
    });

    // Drag and drop logic
    const dropZone = document.getElementById('pdf-drop-zone');
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFile(e.dataTransfer.files[0]);
    });

    async function handleFile(file) {
        if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
            alert("Please select a valid PDF file.");
            return;
        }

        document.getElementById('pdf-upload-status').textContent = '📤 Uploading ' + file.name + '...';
        document.getElementById('pdf-upload-btn').style.opacity = '0.5';
        document.getElementById('pdf-upload-btn').style.pointerEvents = 'none';

        const reader = new FileReader();
        reader.onload = async function(ev) {
            const base64Data = ev.target.result.split(',')[1];
            try {
                const savedPath = await eel.receivePDFUpload(file.name, base64Data)();
                document.getElementById('pdf-upload-status').textContent = '🏁 Done! Converting now...';
                
                setTimeout(() => {
                    overlay.remove(); style.remove();
                }, 2000);
            } catch (err) {
                console.error(err);
                document.getElementById('pdf-upload-status').textContent = '❌ Upload failed. Try again.';
                document.getElementById('pdf-upload-btn').style.opacity = '1';
                document.getElementById('pdf-upload-btn').style.pointerEvents = 'auto';
            }
        };
        reader.readAsDataURL(file);
    }
}
