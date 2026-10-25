import QtQuick
import QtQuick.Shapes

Item {
    id: root
    property string path: ""
    property color color: Theme.text
    property bool filled: false
    property real size: 24
    property real strokeWidth: 2

    width: size; height: size
    implicitWidth: size; implicitHeight: size

    Shape {
        width: 24; height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        ShapePath {
            strokeColor: root.color
            strokeWidth: root.strokeWidth
            fillColor: root.filled ? root.color : "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.path }
        }
    }
}