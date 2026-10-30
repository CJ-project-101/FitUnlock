import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: nb
    property string label
    property string icon
    property bool selected: false
    property bool available: true
    property bool showLabel: true
    property int badge: 0
    signal clicked()

    implicitHeight: 48
    radius: 10
    color: hover.hovered && available ? Theme.hover : "transparent"
    Behavior on color { ColorAnimation { duration: 120 } }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        spacing: 16
        Icon {
            path: nb.icon
            size: 26
            color: Theme.text
            strokeWidth: nb.selected ? 2.7 : 2
            opacity: nb.available ? 1 : 0.4
        }
        Text {
            visible: nb.showLabel
            Layout.fillWidth: true
            text: nb.label
            elide: Text.ElideRight
            color: Theme.text
            opacity: nb.available ? 1 : 0.4
            font.pixelSize: 16
            font.bold: nb.selected
        }
    }
    Rectangle {
        visible: nb.badge > 0
        x: 34; y: 6
        width: Math.max(18, badgeText.implicitWidth + 8); height: 18; radius: 9
        color: Theme.like
        Text {
            id: badgeText
            anchors.centerIn: parent
            text: nb.badge > 99 ? "99+" : nb.badge
            color: "white"; font.pixelSize: 11; font.bold: true
        }
    }
    HoverHandler { id: hover; cursorShape: nb.available ? Qt.PointingHandCursor : Qt.ArrowCursor }
    TapHandler { onTapped: if (nb.available) nb.clicked() }

    ToolTip.visible: hover.hovered && (!nb.showLabel || !nb.available)
    ToolTip.delay: 350
    ToolTip.text: nb.available ? nb.label : nb.label + " (not available yet)"
}