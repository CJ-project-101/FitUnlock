import QtQuick

Rectangle {
    id: toast
    property string message: ""
    function show(msg) { message = msg; opacity = 1; hide.restart() }

    z: 1000
    anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: 28 }
    width: Math.min(parent.width - 40, lbl.implicitWidth + 40)
    height: 42
    radius: 21
    color: "#F0262626"
    border.color: Theme.border
    opacity: 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: 180 } }

    Text {
        id: lbl
        anchors.centerIn: parent
        width: parent.width - 32
        horizontalAlignment: Text.AlignHCenter
        text: toast.message
        color: Theme.text
        elide: Text.ElideRight
        font.pixelSize: 14
    }
    Timer { id: hide; interval: 3200; onTriggered: toast.opacity = 0 }
}