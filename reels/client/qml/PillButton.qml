import QtQuick
import QtQuick.Controls

Button {
    id: b
    property color fill: Theme.accent
    property color textColor: "white"
    implicitHeight: 40
    leftPadding: 18; rightPadding: 18
    contentItem: Text {
        text: b.text
        color: b.textColor
        font.pixelSize: 14; font.bold: true
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 10
        opacity: b.enabled ? 1 : 0.45
        color: b.down ? Qt.darker(b.fill, 1.2) : b.hovered ? Qt.lighter(b.fill, 1.12) : b.fill
        Behavior on color { ColorAnimation { duration: 120 } }
    }
    HoverHandler { cursorShape: Qt.PointingHandCursor }
}