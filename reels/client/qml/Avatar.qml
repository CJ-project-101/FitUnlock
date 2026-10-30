import QtQuick

Rectangle {
    id: av
    property string name: ""
    property string source: ""
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
        visible: img.status !== Image.Ready
        text: av.name.length ? av.name[0].toUpperCase() : "?"
        color: "white"
        font.pixelSize: av.size * 0.45
        font.bold: true
    }
    Image {
        id: img
        anchors.fill: parent
        source: av.source
        asynchronous: true
        smooth: true
        mipmap: true
        fillMode: Image.PreserveAspectCrop
        visible: status === Image.Ready        // the server already makes the picture round
    }
}