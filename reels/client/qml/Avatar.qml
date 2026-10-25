import QtQuick

Rectangle {
    id: av
    property string name: ""
    property real size: 36
    readonly property int hue: {
        var h = 0
        for (var i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360
        return h
    }
    width: size; height: size; radius: size / 2
    color: Qt.hsla(hue / 360, 0.45, 0.32, 1)
    Text {
        anchors.centerIn: parent
        text: av.name.length ? av.name[0].toUpperCase() : "?"
        color: "white"
        font.pixelSize: av.size * 0.45
        font.bold: true
    }
}