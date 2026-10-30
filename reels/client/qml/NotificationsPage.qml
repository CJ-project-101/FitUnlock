import QtQuick
import QtQuick.Layouts

Item {
    id: np

    function ago(iso) {
        var s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
        if (s < 60) return "now"
        if (s < 3600) return Math.floor(s / 60) + "m"
        if (s < 86400) return Math.floor(s / 3600) + "h"
        return Math.floor(s / 86400) + "d"
    }
    function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") }
    function describe(kind, detail) {
        if (kind === "like") return "liked your reel"
        if (kind === "follow") return "started following you"
        return "commented: " + esc(detail)
    }

    onVisibleChanged: if (visible) { backend.loadNotifications(); markTimer.restart() }
    Timer { id: markTimer; interval: 2500; onTriggered: backend.markNotificationsRead() }

    ListModel { id: nm }
    Connections {
        target: backend
        function onNotificationsLoaded(rows) {
            nm.clear()
            for (var i = 0; i < rows.length; i++) nm.append(rows[i])
        }
    }

    Text { id: title; x: 28; y: 22; text: "Notifications"; color: Theme.text; font.pixelSize: 26; font.bold: true }

    ListView {
        id: list
        anchors { top: title.bottom; topMargin: 14; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
        width: Math.min(640, parent.width - 48)
        clip: true
        spacing: 4
        model: nm
        boundsBehavior: Flickable.StopAtBounds

        delegate: Rectangle {
            required property string kind
            required property string actor
            required property string avatar_url
            required property string detail
            required property bool read
            required property string created_at
            width: list.width
            height: 64
            radius: 12
            color: read ? "transparent" : "#187c5cff"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 12
                Avatar { name: actor; source: avatar_url; size: 40 }
                Text {
                    Layout.fillWidth: true
                    textFormat: Text.StyledText
                    text: "<b>" + np.esc(actor) + "</b> " + np.describe(kind, detail)
                    color: Theme.text
                    font.pixelSize: 14
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
                Text { text: np.ago(created_at); color: Theme.muted; font.pixelSize: 13 }
            }
        }
    }
    Text {
        anchors.centerIn: parent
        visible: nm.count === 0
        horizontalAlignment: Text.AlignHCenter
        text: "No notifications yet\nLikes, comments and new followers show up here"
        color: Theme.muted; font.pixelSize: 16
    }
}