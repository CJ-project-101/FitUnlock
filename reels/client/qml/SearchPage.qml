import QtQuick
import QtQuick.Layouts

Item {
    id: sp
    signal messageRequested(string name)
    AppTextField {
        id: field
        anchors { top: parent.top; horizontalCenter: parent.horizontalCenter; topMargin: 24 }
        width: Math.min(480, parent.width - 48)
        placeholderText: "Search by exact username, then press Enter"
        onAccepted: view.who = text.trim().toLowerCase()
    }
    ProfileView {
        id: view
        anchors { top: field.bottom; topMargin: 8; left: parent.left; right: parent.right; bottom: parent.bottom }
        onMessageRequested: (name) => sp.messageRequested(name)
    }
    Text {
        anchors.centerIn: parent
        visible: view.who === ""
        text: "Find a creator by username"
        color: Theme.muted
        font.pixelSize: 16
    }
}