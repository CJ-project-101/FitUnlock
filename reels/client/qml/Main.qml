import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: win
    visible: true
    width: 1280
    height: 860
    minimumWidth: 720
    minimumHeight: 520
    title: "Reelz"
    color: Theme.bg

    Loader {
        anchors.fill: parent
        source: backend.signedIn ? "Shell.qml" : "LoginPage.qml"
    }

    Toast { id: toast }
    Connections {
        target: backend
        function onToast(msg) { toast.show(msg) }
    }
}