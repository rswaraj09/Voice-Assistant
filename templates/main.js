$(document).ready(function () {

    eel.init()()

    $('.text').textillate({
        loop: true, sync: true,
        in: { effect: "bounceIn" },
        out: { effect: "bounceOut" },
    });

    var siriWave = new SiriWave({
        container: document.getElementById("siri-container"),
        width: 800, height: 200, style: "ios9",
        amplitude: "1", speed: "0.30", autostart: true
    });

    $('.siri-message').textillate({
        loop: true, sync: true,
        in: { effect: "fadeInUp", sync: true },
        out: { effect: "fadeOutUp", sync: true },
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

});

function SysDeleteID(clicked_id) {
    eel.deleteSysCommand(clicked_id); eel.displaySysCommand()();
}
function WebDeleteID(clicked_id) {
    eel.deleteWebCommand(clicked_id); eel.displayWebCommand()();
}
function ContactDeleteID(clicked_id) {
    eel.deletePhoneBookCommand(clicked_id); eel.displayPhoneBookCommand()();
}