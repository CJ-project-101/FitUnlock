import QtQuick

Item {
    id: ex
    signal openReel(int index)

    readonly property int cols: Math.max(2, Math.floor((width - 48) / 230))
    readonly property real cell: Math.floor((width - 48) / cols)

    Text { id: title; x: 28; y: 22; text: "Explore"; color: Theme.text; font.pixelSize: 26; font.bold: true }
    Text {
        anchors { left: title.right; leftMargin: 12; baseline: title.baseline }
        text: "Reels from everyone"
        color: Theme.muted; font.pixelSize: 14
    }

    GridView {
        id: grid
        anchors { top: title.bottom; topMargin: 14; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
        width: ex.cell * ex.cols
        cellWidth: ex.cell
        cellHeight: Math.round(ex.cell * 1.5)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: backend.reels
        onAtYEndChanged: if (atYEnd && count > 0) backend.loadMore()

        delegate: Item {
            id: tile
            required property int index
            required property string author
            required property string thumbUrl
            required property int likes
            required property int comments
            width: grid.cellWidth
            height: grid.cellHeight

            Rectangle {
                anchors.fill: parent
                anchors.margins: 3
                radius: 10
                color: Theme.card
                clip: true
                scale: area.containsMouse ? 1.025 : 1.0
                Behavior on scale { NumberAnimation { duration: 120 } }

                Image {
                    anchors.fill: parent
                    source: tile.thumbUrl
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: tile.thumbUrl !== ""
                }
                Icon { anchors.centerIn: parent; visible: tile.thumbUrl === ""; path: Icons.reels; color: Theme.muted; size: 36 }

                Rectangle {
                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                    height: 70
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#00000000" }
                        GradientStop { position: 1.0; color: "#CC000000" }
                    }
                }
                Row {
                    anchors { left: parent.left; bottom: parent.bottom; margins: 10 }
                    spacing: 8
                    Avatar { name: tile.author; size: 22 }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: tile.author
                        color: "white"; font.pixelSize: 13; font.bold: true
                    }
                }
                Row {
                    anchors { right: parent.right; bottom: parent.bottom; margins: 10 }
                    spacing: 5
                    Icon { anchors.verticalCenter: parent.verticalCenter; size: 15; path: Icons.heart; color: "white" }
                    Text { anchors.verticalCenter: parent.verticalCenter; text: tile.likes; color: "white"; font.pixelSize: 13 }
                }
                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: ex.openReel(tile.index)
                }
            }
        }
    }

    Text {
        anchors.centerIn: parent
        visible: backend.locked
        horizontalAlignment: Text.AlignHCenter
        text: "Reels are locked\nEarn minutes in FitPlay to browse"
        color: Theme.muted; font.pixelSize: 16
    }
    Text {
        anchors.centerIn: parent
        visible: !backend.locked && grid.count === 0 && !backend.loading
        horizontalAlignment: Text.AlignHCenter
        text: "No reels yet\nBe the first to share one"
        color: Theme.muted; font.pixelSize: 16
    }
}