import QtQuick

Item {
    id: pv
    property string who: ""
    property var info: null
    property string error: ""
    property bool loading: false

    readonly property int cell: Math.max(90, Math.floor(Math.min(240, (width - 32) / 3)))

    function reload() {
        if (who === "") { info = null; error = ""; return }
        loading = true
        error = ""
        backend.loadProfile(who)
    }
    onWhoChanged: reload()
    onVisibleChanged: if (visible) reload()

    Connections {
        target: backend
        function onProfileLoaded(name, data) {
            if (name !== pv.who) return
            pv.loading = false; pv.info = data
        }
        function onProfileFailed(name, msg) {
            if (name !== pv.who) return
            pv.loading = false; pv.info = null; pv.error = msg
        }
    }

    Text {
        anchors.centerIn: parent
        visible: pv.loading && pv.info === null
        text: "Loading profile…"
        color: Theme.muted
    }
    Text {
        anchors.centerIn: parent
        visible: !pv.loading && pv.error !== ""
        text: pv.error
        color: Theme.muted
        font.pixelSize: 16
    }

    GridView {
        id: grid
        visible: pv.info !== null
        anchors { top: parent.top; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
        width: pv.cell * 3
        cellWidth: pv.cell
        cellHeight: Math.round(pv.cell * 16 / 9)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: pv.info ? pv.info.reels : []

        header: Item {
            width: grid.width
            height: head.implicitHeight + 40
            Row {
                id: head
                y: 24
                spacing: 28
                Avatar { name: pv.info ? pv.info.username : ""; size: 96 }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    Text {
                        text: pv.info ? pv.info.username : ""
                        color: Theme.text; font.pixelSize: 22; font.bold: true
                    }
                    Row {
                        spacing: 22
                        Text { textFormat: Text.StyledText; color: Theme.text; text: "<b>" + (pv.info ? pv.info.reels.length : 0) + "</b> reels" }
                        Text { textFormat: Text.StyledText; color: Theme.text; text: "<b>" + (pv.info ? pv.info.followers : 0) + "</b> followers" }
                        Text { textFormat: Text.StyledText; color: Theme.text; text: "<b>" + (pv.info ? pv.info.following : 0) + "</b> following" }
                    }
                    PillButton {
                        visible: pv.info && !pv.info.is_me
                        text: pv.info && pv.info.i_follow ? "Following" : "Follow"
                        fill: pv.info && pv.info.i_follow ? Theme.card : Theme.accent
                        textColor: pv.info && pv.info.i_follow ? Theme.text : "white"
                        onClicked: backend.setFollow(pv.info.username, !pv.info.i_follow)
                    }
                    Text {
                        visible: pv.info && pv.info.reels.length === 0
                        text: "No reels yet"
                        color: Theme.muted
                    }
                }
            }
        }

        delegate: Item {
            id: tile
            required property var modelData
            width: grid.cellWidth
            height: grid.cellHeight
            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                color: Theme.card
                clip: true
                Image {
                    anchors.fill: parent
                    source: tile.modelData.thumbUrl
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: tile.modelData.thumbUrl !== ""
                }
                Text {
                    anchors.centerIn: parent
                    width: parent.width - 16
                    visible: tile.modelData.thumbUrl === ""
                    text: tile.modelData.caption || "Reel"
                    color: Theme.muted
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }
        }
    }
}