import QtQuick

Column {
    id: ab
    property string icon
    property bool filled: false
    property color iconColor: Theme.text
    property string label: ""
    signal clicked()

    spacing: 2
    width: 56

    onFilledChanged: if (filled) pop.restart()

    Rectangle {
        width: 48; height: 48; radius: 24
        anchors.horizontalCenter: parent.horizontalCenter
        color: area.containsMouse ? Theme.hover : "transparent"
        Behavior on color { ColorAnimation { duration: 120 } }

        Icon {
            id: ico
            anchors.centerIn: parent
            path: ab.icon
            size: 28
            filled: ab.filled
            color: ab.iconColor
            SequentialAnimation {
                id: pop
                NumberAnimation { target: ico; property: "scale"; to: 0.6; duration: 70 }
                NumberAnimation { target: ico; property: "scale"; to: 1.0; duration: 160; easing.type: Easing.OutBack }
            }
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: ab.clicked()
        }
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: ab.label
        color: Theme.text
        font.pixelSize: 13
    }
}