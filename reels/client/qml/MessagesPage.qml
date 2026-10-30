import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: mp
    property string current: ""
    property string threadError: ""
    property var peer: ({ username: "", avatar_url: "" })

    function open(name) {
        current = name.trim().toLowerCase()
        threadError = ""
        tm.clear()
        peer = ({ username: current, avatar_url: "" })
        if (current !== "") backend.loadThread(current)
    }
    function refresh() {
        backend.loadConversations()
        if (current !== "") backend.loadThread(current)
    }
    function send() {
        var t = composer.text.trim()
        if (t === "") return
        backend.sendMessage(current, t)
        composer.clear()
    }
    function ago(iso) {
        var s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
        if (s < 60) return "now"
        if (s < 3600) return Math.floor(s / 60) + "m"
        if (s < 86400) return Math.floor(s / 3600) + "h"
        return Math.floor(s / 86400) + "d"
    }

    onVisibleChanged: if (visible) refresh()
    Timer { interval: 4000; repeat: true; running: mp.visible; onTriggered: mp.refresh() }

    ListModel { id: cm }      // conversations
    ListModel { id: tm }      // messages of the open chat

    Connections {
        target: backend
        function onConversationsLoaded(rows) {
            cm.clear()
            for (var i = 0; i < rows.length; i++) cm.append(rows[i])
        }
        function onThreadLoaded(name, d) {
            if (name !== mp.current) return
            mp.threadError = ""
            mp.peer = d.user
            var n = d.messages.length
            // rebuild only when something changed, so the scroll position survives the refresh
            if (n === tm.count && (n === 0 || d.messages[n - 1].mid === tm.get(n - 1).mid)) return
            tm.clear()
            for (var i = 0; i < n; i++) tm.append(d.messages[i])
            Qt.callLater(view.positionViewAtEnd)
        }
        function onThreadFailed(name, msg) { if (name === mp.current) mp.threadError = msg }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---- conversation list ----
        Item {
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            Rectangle { width: 1; height: parent.height; anchors.right: parent.right; color: Theme.border }
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                Text { text: "Messages"; color: Theme.text; font.pixelSize: 24; font.bold: true }
                AppTextField {
                    id: newChat
                    Layout.fillWidth: true
                    placeholderText: "New chat: type a username"
                    onAccepted: { mp.open(text); clear() }
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: cm
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: Rectangle {
                        id: conv
                        required property string username
                        required property string avatar_url
                        required property string last
                        required property bool mine
                        required property int unread
                        width: ListView.view.width
                        height: 60
                        radius: 10
                        color: mp.current === username ? Theme.hover : (cArea.containsMouse ? "#12ffffff" : "transparent")
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 10
                            Avatar { name: conv.username; source: conv.avatar_url; size: 42 }
                            Column {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: conv.username; color: Theme.text; font.bold: conv.unread > 0; font.pixelSize: 14 }
                                Text {
                                    width: parent.width
                                    text: (conv.mine ? "You: " : "") + conv.last
                                    elide: Text.ElideRight
                                    color: conv.unread > 0 ? Theme.text : Theme.muted
                                    font.pixelSize: 12
                                }
                            }
                            Rectangle {
                                visible: conv.unread > 0
                                width: 20; height: 20; radius: 10; color: Theme.accent
                                Text { anchors.centerIn: parent; text: conv.unread; color: "white"; font.pixelSize: 11; font.bold: true }
                            }
                        }
                        MouseArea {
                            id: cArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: mp.open(conv.username)
                        }
                    }
                }
            }
        }

        // ---- open chat ----
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Item {
                visible: mp.current !== ""
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                Row {
                    x: 20
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    Avatar { name: mp.peer.username; source: mp.peer.avatar_url; size: 38 }
                    Text { anchors.verticalCenter: parent.verticalCenter; text: mp.peer.username; color: Theme.text; font.pixelSize: 16; font.bold: true }
                }
                Rectangle { width: parent.width; height: 1; anchors.bottom: parent.bottom; color: Theme.border }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: view
                    anchors.fill: parent
                    anchors.margins: 12
                    clip: true
                    spacing: 6
                    model: tm
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: Item {
                        id: row
                        required property bool mine
                        required property string text
                        readonly property real maxW: Math.max(120, view.width * 0.7 - 28)
                        width: view.width
                        height: bubble.height
                        // hidden copy of the text, only used to measure its natural width
                        Text { id: probe; visible: false; text: row.text; font.pixelSize: 14 }
                        Rectangle {
                            id: bubble
                            x: row.mine ? row.width - width - 4 : 4
                            width: Math.min(Math.ceil(probe.implicitWidth) + 2, row.maxW) + 28
                            height: msg.implicitHeight + 22
                            radius: 16
                            color: row.mine ? Theme.accent : Theme.card
                            Text {
                                id: msg
                                x: 14; y: 11
                                width: parent.width - 28
                                text: row.text
                                color: "white"; font.pixelSize: 14
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: mp.current === ""
                    horizontalAlignment: Text.AlignHCenter
                    text: "Your messages\nPick a chat, or type a username to start one"
                    color: Theme.muted; font.pixelSize: 16
                }
                Text {
                    anchors.centerIn: parent
                    visible: mp.current !== "" && mp.threadError !== ""
                    text: mp.threadError
                    color: Theme.muted; font.pixelSize: 15
                }
                Text {
                    anchors.centerIn: parent
                    visible: mp.current !== "" && mp.threadError === "" && tm.count === 0
                    text: "No messages yet. Say hello!"
                    color: Theme.muted; font.pixelSize: 15
                }
            }

            RowLayout {
                visible: mp.current !== "" && mp.threadError === ""
                Layout.fillWidth: true
                Layout.margins: 14
                spacing: 8
                AppTextField {
                    id: composer
                    Layout.fillWidth: true
                    placeholderText: "Message…"
                    maximumLength: 1000
                    onAccepted: mp.send()
                }
                PillButton { text: "Send"; enabled: composer.text.trim().length > 0; onClicked: mp.send() }
            }
        }
    }
}