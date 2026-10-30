import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: pv
    property string who: ""
    property var info: null
    property string error: ""
    property bool loading: false
    signal messageRequested(string name)

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
        function onProfileSaved() { if (pv.visible) pv.reload() }
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
                Avatar { name: pv.info ? pv.info.username : ""; source: pv.info ? pv.info.avatar_url : ""; size: 96 }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    Text { text: pv.info ? pv.info.username : ""; color: Theme.text; font.pixelSize: 22; font.bold: true }
                    Row {
                        spacing: 20
                        Text { textFormat: Text.StyledText; color: Theme.text; text: "<b>" + (pv.info ? pv.info.reels.length : 0) + "</b> reels" }
                        Text { textFormat: Text.StyledText; color: Theme.text; text: "<b>" + (pv.info ? pv.info.followers : 0) + "</b> followers" }
                        Text { textFormat: Text.StyledText; color: Theme.text; text: "<b>" + (pv.info ? pv.info.following : 0) + "</b> following" }
                    }
                    Text {
                        visible: pv.info !== null && pv.info.bio !== ""
                        width: Math.max(160, grid.width - 96 - 28 - 8)
                        text: pv.info ? pv.info.bio : ""
                        color: Theme.text; font.pixelSize: 14
                        wrapMode: Text.Wrap
                    }
                    Row {
                        spacing: 8
                        PillButton {
                            visible: pv.info !== null && pv.info.is_me
                            text: "Edit profile"
                            fill: Theme.card; textColor: Theme.text
                            onClicked: edit.open()
                        }
                        PillButton {
                            visible: pv.info !== null && !pv.info.is_me
                            text: pv.info && pv.info.i_follow ? "Following" : "Follow"
                            fill: pv.info && pv.info.i_follow ? Theme.card : Theme.accent
                            textColor: pv.info && pv.info.i_follow ? Theme.text : "white"
                            onClicked: backend.setFollow(pv.info.username, !pv.info.i_follow)
                        }
                        PillButton {
                            visible: pv.info !== null && !pv.info.is_me
                            text: "Message"
                            fill: Theme.card; textColor: Theme.text
                            onClicked: pv.messageRequested(pv.info.username)
                        }
                    }
                    Text {
                        visible: pv.info !== null && pv.info.reels.length === 0
                        text: "No reels yet"
                        color: Theme.muted
                    }
                }
            }
        }

        delegate: Item {
            id: tile
            required property int index
            required property var modelData
            width: grid.cellWidth
            height: grid.cellHeight
            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                color: Theme.card
                clip: true
                scale: tileArea.containsMouse ? 1.025 : 1.0
                Behavior on scale { NumberAnimation { duration: 120 } }
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
                MouseArea {
                    id: tileArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: backend.openUserReels(pv.info.username, tile.index)
                }
            }
        }
    }

    // ---- edit profile (photo + bio) ----
    FileDialog {
        id: photoDialog
        title: "Choose a profile photo"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp)"]
        onAccepted: backend.chooseAvatar(selectedFile.toString())
    }
    Popup {
        id: edit
        modal: true
        padding: 24
        width: Math.min(420, pv.width - 40)
        anchors.centerIn: Overlay.overlay
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        onOpened: bioField.text = pv.info ? pv.info.bio : ""
        background: Rectangle { color: Theme.panel; radius: 16; border.color: Theme.border }
        Overlay.modal: Rectangle { color: "#AA000000" }

        contentItem: ColumnLayout {
            spacing: 14
            Text { text: "Edit profile"; color: Theme.text; font.pixelSize: 20; font.bold: true }
            RowLayout {
                spacing: 16
                Avatar { name: backend.username; source: backend.avatarUrl; size: 80 }
                PillButton { text: "Change photo"; fill: Theme.card; textColor: Theme.text; onClicked: photoDialog.open() }
            }
            Text { text: "Bio"; color: Theme.muted }
            AppTextField {
                id: bioField
                Layout.fillWidth: true
                maximumLength: 150
                placeholderText: "Tell people about yourself"
            }
            Text { Layout.alignment: Qt.AlignRight; text: bioField.text.length + " / 150"; color: Theme.muted; font.pixelSize: 12 }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 10
                PillButton { text: "Cancel"; fill: Theme.card; textColor: Theme.text; onClicked: edit.close() }
                PillButton { text: "Save"; onClicked: { backend.saveBio(bioField.text); edit.close() } }
            }
        }
    }
}