$(document).ready(function () {

    eel.init()()



    var siriWave = new SiriWave({
        container: document.getElementById("siri-container"),
        width: 800, height: 200, style: "ios9",
        amplitude: "1", speed: "0.30", autostart: true
    });

    // ── ASSISTANT STATE ───────────────────────────────────────────────────
    var isAssistantRunning = false;

    // ── EEL EXPOSED FUNCTIONS ─────────────────────────────────────────────
    eel.expose(ShowHood)
    function ShowHood() {
        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
        isAssistantRunning = false;
    }

    eel.expose(DisplayMessage)
    function DisplayMessage(message) {
        $(".siri-message li").text(message);
    }

    eel.expose(senderText)
    function senderText(message) {
        if (message && message.length > 0)
            $(".siri-message li").text(message);
    }

    eel.expose(receiverText)
    function receiverText(message) {
        if (message && message.length > 0)
            $(".siri-message li").text(message);
    }

    // ── SHOW SIRI WAVE ────────────────────────────────────────────────────
    function showSiriWave() {
        isAssistantRunning = true;
        eel.playAssistantSound()
        $("#Oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
        console.log("[Nora] Siri wave activated");
    }

    // ── MANUAL ACTIVATION ─────────────────────────────────────────────────
    function activateAssistant() {
        if (isAssistantRunning) return;
        showSiriWave();
        eel.allCommands()()
    }

    $("#MicBtn").click(function () { activateAssistant(); });

    document.addEventListener('keyup', function (e) {
        if (e.key === 'j' && e.altKey) activateAssistant();
    }, false);


    // ── HOTWORD POLLING — polls ui_trigger.txt ────────────────────────────
    // Python watcher writes ui_trigger.txt → JS shows Siri wave
    // Python also calls allCommands() directly so JS does NOT call it again
    setInterval(function () {
        eel.checkUITrigger()(function (triggered) {
            if (triggered) {
                console.log("[Nora] UI trigger detected — showing Siri wave");
                showSiriWave();
                // DO NOT call allCommands() — Python already handles listening
            }
        });
    }, 200);


    // ── CHAT BOX ──────────────────────────────────────────────────────────
    function PlayAssistant(message) {
        if (message != "") {
            showSiriWave();
            eel.allCommands(message);
            $("#chatbox").val("")
            $("#MicBtn").attr('hidden', false);
            $("#SendBtn").attr('hidden', true);
        }
    }

    function ShowHideButton(message) {
        if (message.length == 0) {
            $("#MicBtn").attr('hidden', false);
            $("#SendBtn").attr('hidden', true);
        } else {
            $("#MicBtn").attr('hidden', true);
            $("#SendBtn").attr('hidden', false);
        }
    }

    $("#chatbox").keyup(function () { ShowHideButton($("#chatbox").val()); });
    $("#SendBtn").click(function () { PlayAssistant($("#chatbox").val()); });
    $("#chatbox").keypress(function (e) {
        if (e.which == 13) PlayAssistant($("#chatbox").val());
    });


    // ── SETTINGS ──────────────────────────────────────────────────────────
    eel.personalInfo()();
    eel.displaySysCommand()();
    eel.displayWebCommand()();
    eel.displayPhoneBookCommand()();
    refreshModesList();

    eel.expose(showSiriWaveFromPython)
    function showSiriWaveFromPython() {
        isAssistantRunning = true;
        $("#Oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
        console.log("[Nora] Siri wave shown from Python call");
    }

    eel.expose(getData)
    function getData(user_info) {
        let data = JSON.parse(user_info);
        let idsPersonalInfo = ['OwnerName', 'Designation', 'MobileNo', 'Email', 'City']
        let idsInputInfo    = ['InputOwnerName', 'InputDesignation', 'InputMobileNo', 'InputEmail', 'InputCity']
        for (let i = 0; i < data.length; i++) {
            $("#" + idsPersonalInfo[i]).text(data[i]);
            $("#" + idsInputInfo[i]).val(data[i]);
        }
    }

    $("#UpdateBtn").click(function () {
        let OwnerName = $("#InputOwnerName").val(), Designation = $("#InputDesignation").val();
        let MobileNo  = $("#InputMobileNo").val(),  Email = $("#InputEmail").val(), City = $("#InputCity").val();
        if (OwnerName.length > 0 && Designation.length > 0 && MobileNo.length > 0 && Email.length > 0 && City.length > 0) {
            eel.updatePersonalInfo(OwnerName, Designation, MobileNo, Email, City)
            swal({ title: "Updated Successfully", icon: "success" });
        } else {
            const toast = new bootstrap.Toast(document.getElementById('liveToast'))
            $("#ToastMessage").text("All Fields Mandatory"); toast.show()
        }
    });

    eel.expose(displaySysCommand)
    function displaySysCommand(array) {
        let data = JSON.parse(array), out = "", index = 0;
        for (let i = 0; i < data.length; i++) {
            index++
            out += `<tr>
                <td class="text-light">${index}</td>
                <td class="text-light">${data[i][1]}</td>
                <td class="text-light">${data[i][2]}</td>
                <td class="text-light"><button id="${data[i][0]}" onClick="SysDeleteID(this.id)" class="btn btn-sm btn-glow-red">Delete</button></td>
            </tr>`;
        }
        document.querySelector("#TableData").innerHTML = out;
    }

    $("#SysCommandAddBtn").click(function () {
        let key = $("#SysCommandKey").val(), value = $("#SysCommandValue").val();
        if (key.length > 0 && value.length > 0) {
            eel.addSysCommand(key, value)
            swal({ title: "Updated Successfully", icon: "success" });
            eel.displaySysCommand()();
            $("#SysCommandKey").val(""); $("#SysCommandValue").val("");
        } else {
            const toast = new bootstrap.Toast(document.getElementById('liveToast'))
            $("#ToastMessage").text("All Fields Mandatory"); toast.show()
        }
    });

    eel.expose(displayWebCommand)
    function displayWebCommand(array) {
        let data = JSON.parse(array), out = "", index = 0;
        for (let i = 0; i < data.length; i++) {
            index++
            out += `<tr>
                <td class="text-light">${index}</td>
                <td class="text-light">${data[i][1]}</td>
                <td class="text-light">${data[i][2]}</td>
                <td class="text-light"><button id="${data[i][0]}" onClick="WebDeleteID(this.id)" class="btn btn-sm btn-glow-red">Delete</button></td>
            </tr>`;
        }
        document.querySelector("#WebTableData").innerHTML = out;
    }

    $("#WebCommandAddBtn").click(function () {
        let key = $("#WebCommandKey").val(), value = $("#WebCommandValue").val();
        if (key.length > 0 && value.length > 0) {
            eel.addWebCommand(key, value)
            swal({ title: "Updated Successfully", icon: "success" });
            eel.displayWebCommand()();
            $("#WebCommandKey").val(""); $("#WebCommandValue").val("");
        } else {
            const toast = new bootstrap.Toast(document.getElementById('liveToast'))
            $("#ToastMessage").text("All Fields Mandatory"); toast.show()
        }
    });

    eel.expose(displayPhoneBookCommand)
    function displayPhoneBookCommand(array) {
        let data = JSON.parse(array), out = "", index = 0;
        for (let i = 0; i < data.length; i++) {
            index++
            out += `<tr>
                <td class="text-light">${index}</td>
                <td class="text-light">${data[i][1]}</td>
                <td class="text-light">${data[i][2]}</td>
                <td class="text-light">${data[i][3]}</td>
                <td class="text-light">${data[i][4]}</td>
                <td class="text-light"><button id="${data[i][0]}" onClick="ContactDeleteID(this.id)" class="btn btn-sm btn-glow-red">Delete</button></td>
            </tr>`;
        }
        document.querySelector("#ContactTableData").innerHTML = out;
    }

    $("#AddContactBtn").click(function () {
        let Name = $("#InputContactName").val(), MobileNo = $("#InputContactMobileNo").val();
        let Email = $("#InputContactEmail").val(), City = $("#InputContactCity").val();
        if (Name.length > 0 && MobileNo.length > 0) {
            eel.InsertContacts(Name, MobileNo, Email, City)
            swal({ title: "Updated Successfully", icon: "success" });
            $("#InputContactName").val(""); $("#InputContactMobileNo").val("");
            $("#InputContactEmail").val(""); $("#InputContactCity").val("");
            eel.displayPhoneBookCommand()()
        } else {
            const toast = new bootstrap.Toast(document.getElementById('liveToast'))
            $("#ToastMessage").text("Name and Mobile number Mandatory"); toast.show()
        }
    });

    // ── MODES ─────────────────────────────────────────────────────────────
    function refreshModesList() {
        eel.uiListModes()(function (raw) {
            let modes = JSON.parse(raw || "[]");
            let host = document.querySelector("#ModesList");
            if (!host) return;
            if (modes.length === 0) {
                host.innerHTML = '<p class="text-light"><em>No modes yet. Create one above.</em></p>';
                return;
            }
            let out = "";
            for (let m of modes) {
                out += `
                <div class="mode-card mb-3 p-3" style="border:${m.is_active ? '2px solid #00ff88' : '1px solid rgba(0,170,255,0.4)'};border-radius:6px;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong class="text-light text-capitalize">${m.name}</strong>
                            ${m.is_active ? '<span class="badge bg-success ms-2">active</span>' : ''}
                            <span class="text-light" style="opacity:0.7;"> — ${m.description || ""}</span>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-glow me-2" onClick="ModeActivate('${m.name}')">Activate</button>
                            <button class="btn btn-sm btn-glow-red" onClick="ModeDelete('${m.name}')">Delete</button>
                        </div>
                    </div>
                    <div class="d-flex mt-2">
                        <select id="ItemType-${m.id}" class="form-control glassy-form me-2" style="max-width:110px;">
                            <option value="app">App</option>
                            <option value="link">Link</option>
                        </select>
                        <input type="text" class="form-control glassy-form me-2"
                               id="ItemRef-${m.id}" placeholder="app name or URL">
                        <button class="btn btn-glow" onClick="ModeAddItem('${m.name}', ${m.id})">Add</button>
                    </div>
                    <div id="ModeItems-${m.id}" class="mt-2"></div>
                </div>`;
            }
            host.innerHTML = out;
            for (let m of modes) { refreshModeItems(m.name, m.id); }
        });
    }
    window.refreshModesList = refreshModesList;

    eel.expose(noraActiveModeChanged);
    function noraActiveModeChanged(_name) { refreshModesList(); }

    function refreshModeItems(name, modeId) {
        eel.uiGetModeItems(name)(function (raw) {
            let items = JSON.parse(raw || "[]");
            let host = document.querySelector(`#ModeItems-${modeId}`);
            if (!host) return;
            if (items.length === 0) {
                host.innerHTML = '<small class="text-light" style="opacity:0.6;">No items.</small>';
                return;
            }
            let out = '<ul class="list-unstyled mb-0">';
            for (let it of items) {
                out += `<li class="text-light" style="font-size:0.9em;">
                    <span style="opacity:0.8;">[${it.type}]</span> ${it.ref}
                    <button class="btn btn-sm btn-glow-red ms-2" style="padding:2px 8px;"
                            onClick="ModeRemoveItem(${it.id}, '${name}', ${modeId})">×</button>
                </li>`;
            }
            out += "</ul>";
            host.innerHTML = out;
        });
    }
    window.refreshModeItems = refreshModeItems;

    // ── NEWS ──────────────────────────────────────────────────────────────
    window._newsCache = { feed: [], saved: [] };
    function esc(s) { return String(s || "").replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]); }
    function renderNewsList(articles, hostSel, saved) {
        let host = document.querySelector(hostSel);
        if (!host) return;
        if (!articles || articles.length === 0) {
            host.innerHTML = '<p class="text-light" style="opacity:0.6;"><em>No articles.</em></p>';
            return;
        }
        let cacheKey = saved ? "saved" : "feed";
        window._newsCache[cacheKey] = articles;
        let out = "";
        articles.forEach((a, idx) => {
            let title   = esc(a.title);
            let summary = esc((a.summary || "").slice(0, 280));
            let url     = esc(a.url || "#");
            let source  = esc(a.source || "");
            let idAttr  = a.id != null ? a.id : "";
            let action  = saved
                ? `<button class="btn btn-sm btn-glow-red" onClick="NewsDeleteSaved(${idAttr})">Remove</button>`
                : `<button class="btn btn-sm btn-glow" onClick="NewsSave(${idx})">Save</button>`;
            out += `<div class="mb-3 p-2" style="border:1px solid rgba(0,170,255,0.3);border-radius:6px;">
                <div class="text-light" style="font-weight:bold;">${title}</div>
                <div class="text-light" style="opacity:0.7;font-size:0.85em;">${source}</div>
                <div class="text-light" style="font-size:0.9em;">${summary}</div>
                <div class="mt-2">
                    <a href="${url}" target="_blank" class="btn btn-sm btn-glow me-2">Open</a>
                    ${action}
                </div>
            </div>`;
        });
        host.innerHTML = out;
    }
    window.renderNewsList = renderNewsList;

    function refreshSavedNews() {
        eel.uiListSavedArticles()(function (raw) {
            renderNewsList(JSON.parse(raw || "[]"), "#SavedNewsList", true);
        });
    }
    window.refreshSavedNews = refreshSavedNews;

    $("#FetchNewsBtn").click(function () {
        let cat = $("#NewsCategory").val();
        let kw  = $("#NewsKeyword").val().trim();
        if (kw) {
            eel.uiSearchNews(kw, 10)(function (raw) { renderNewsList(JSON.parse(raw || "[]"), "#NewsList", false); });
        } else {
            eel.uiFetchNews(cat, 10)(function (raw) { renderNewsList(JSON.parse(raw || "[]"), "#NewsList", false); });
        }
    });

    refreshSavedNews();

    // ── AVATARS ───────────────────────────────────────────────────────────
    function refreshAvatarStyles() {
        eel.uiAvatarStyles()(function (raw) {
            let styles = JSON.parse(raw || "[]");
            let sel = document.querySelector("#AvatarStyle");
            if (!sel) return;
            sel.innerHTML = styles.map(s => `<option value="${s}">${s}</option>`).join("");
        });
    }

    function refreshAvatarsList() {
        eel.uiListAvatars()(function (raw) {
            let avatars = JSON.parse(raw || "[]");
            let host = document.querySelector("#AvatarsList");
            if (!host) return;
            if (avatars.length === 0) {
                host.innerHTML = '<p class="text-light" style="opacity:0.6;"><em>No avatars yet.</em></p>';
                return;
            }
            let out = "";
            for (let a of avatars) {
                let border = a.is_active ? "2px solid #00ff88" : "1px solid rgba(0,170,255,0.3)";
                out += `<div class="p-2" style="border:${border};border-radius:8px;text-align:center;">
                    <img src="${a.image_path}" style="width:100%;height:120px;object-fit:contain;" />
                    <div class="text-light mt-1" style="font-weight:bold;">${a.name}</div>
                    <div class="mt-2" style="display:flex;gap:4px;justify-content:center;flex-wrap:wrap;">
                        <button class="btn btn-sm btn-glow" onClick="AvatarActivate(${a.id})">Use</button>
                        <button class="btn btn-sm btn-glow-red" onClick="AvatarDelete(${a.id})">×</button>
                    </div>
                </div>`;
            }
            host.innerHTML = out;
        });
    }
    window.refreshAvatarsList = refreshAvatarsList;

    $("#CreateAvatarBtn").click(function () {
        let name  = $("#AvatarName").val().trim();
        let style = $("#AvatarStyle").val() || "avataaars";
        let seed  = $("#AvatarSeed").val().trim() || null;
        if (!name) {
            const toast = new bootstrap.Toast(document.getElementById('liveToast'));
            $("#ToastMessage").text("Name required"); toast.show();
            return;
        }
        eel.uiCreateAvatar(name, style, seed, "")(function (raw) {
            let res = JSON.parse(raw);
            if (res.ok) {
                swal({ title: res.message, icon: "success" });
                $("#AvatarName").val(""); $("#AvatarSeed").val("");
                refreshAvatarsList();
            } else {
                const toast = new bootstrap.Toast(document.getElementById('liveToast'));
                $("#ToastMessage").text(res.message); toast.show();
            }
        });
    });

    eel.expose(noraAvatarsChanged);
    function noraAvatarsChanged() { refreshAvatarsList(); refreshActiveAvatar(); }

    eel.expose(noraUpdateActiveAvatar);
    function noraUpdateActiveAvatar(imagePath) {
        let host = document.getElementById("ActiveAvatarHost");
        let img  = document.getElementById("ActiveAvatarImg");
        if (!host || !img) return;
        if (imagePath) {
            img.src = imagePath;
            host.hidden = false;
        } else {
            host.hidden = true;
        }
        refreshAvatarsList();
    }

    function refreshActiveAvatar() {
        eel.uiGetActiveAvatar()(function (raw) {
            try {
                let data = JSON.parse(raw || "{}");
                noraUpdateActiveAvatar(data && data.image_path ? data.image_path : null);
            } catch (_) {}
        });
    }
    window.refreshActiveAvatar = refreshActiveAvatar;

    // Speaking / thinking animation hooks — Python flips these via Eel.
    eel.expose(noraAvatarState);
    function noraAvatarState(state) {
        let host = document.getElementById("ActiveAvatarHost");
        if (!host) return;
        host.classList.remove("speaking", "thinking");
        if (state === "speaking" || state === "thinking") host.classList.add(state);
    }

    refreshAvatarStyles();
    refreshAvatarsList();
    refreshActiveAvatar();

    $("#CreateModeBtn").click(function () {
        let name = $("#ModeName").val().trim();
        let desc = $("#ModeDescription").val().trim();
        if (!name) {
            const toast = new bootstrap.Toast(document.getElementById('liveToast'));
            $("#ToastMessage").text("Mode name required"); toast.show();
            return;
        }
        eel.uiCreateMode(name, desc)(function (raw) {
            let res = JSON.parse(raw);
            if (res.ok) {
                swal({ title: res.message, icon: "success" });
                $("#ModeName").val(""); $("#ModeDescription").val("");
                refreshModesList();
            } else {
                const toast = new bootstrap.Toast(document.getElementById('liveToast'));
                $("#ToastMessage").text(res.message); toast.show();
            }
        });
    });
});

function ModeActivate(name) {
    eel.uiActivateMode(name);
}
function ModeDelete(name) {
    eel.uiDeleteMode(name)(function () { refreshModesList(); });
}
function ModeAddItem(name, modeId) {
    let type = document.querySelector(`#ItemType-${modeId}`).value;
    let ref  = document.querySelector(`#ItemRef-${modeId}`).value.trim();
    if (!ref) return;
    eel.uiAddToMode(name, type, ref)(function () {
        document.querySelector(`#ItemRef-${modeId}`).value = "";
        refreshModeItems(name, modeId);
    });
}
function ModeRemoveItem(itemId, name, modeId) {
    eel.uiRemoveModeItem(itemId)(function () { refreshModeItems(name, modeId); });
}

function NewsSave(index) {
    let a = (window._newsCache && window._newsCache.feed) ? window._newsCache.feed[index] : null;
    if (!a) return;
    eel.uiSaveArticle(a.title || "", a.summary || "", a.source || "", a.url || "", a.category || "general")(function () {
        if (window.refreshSavedNews) window.refreshSavedNews();
        swal({ title: "Saved", icon: "success" });
    });
}
function NewsDeleteSaved(id) {
    eel.uiDeleteSavedArticle(id)(function () {
        if (window.refreshSavedNews) window.refreshSavedNews();
    });
}
function AvatarActivate(id) {
    eel.uiSetActiveAvatar(id)(function () { if (window.refreshAvatarsList) window.refreshAvatarsList(); });
}
function AvatarDelete(id) {
    eel.uiDeleteAvatar(id)(function () { if (window.refreshAvatarsList) window.refreshAvatarsList(); });
}

function SysDeleteID(clicked_id) {
    eel.deleteSysCommand(clicked_id); eel.displaySysCommand()();
}
function WebDeleteID(clicked_id) {
    eel.deleteWebCommand(clicked_id); eel.displayWebCommand()();
}
function ContactDeleteID(clicked_id) {
    eel.deletePhoneBookCommand(clicked_id); eel.displayPhoneBookCommand()();
}