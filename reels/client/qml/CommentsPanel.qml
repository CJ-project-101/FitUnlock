import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: panel
    property bool opened: false
    property int reelId: -1
    property bool loading: false
    property string error: ""
    property var review: null            // ReelGuard verdict while a flagged comment waits for the user
    property string reviewText: ""
    signal closed()

    width: Math.min(400, parent.width)
    height: parent.height
    y: 0
    x: opened ? parent.width - width : parent.width
    visible: x < parent.width - 0.5
    color: Theme.panel
    Behavior on x { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

    Rectangle { width: 1; height: parent.height; color: Theme.border }
    WheelHandler { }          // swallow wheel events so the feed does not change reels

    ListModel { id: cm }

    function openFor(id) {
        reelId = id
        cm.clear()
        error = ""
        review = null
        loading = true
        opened = true
        backend.loadComments(id)
        input.forceActiveFocus()
    }
    function close() { opened = false; closed() }
    function post() {
        var t = input.text.trim()
        if (t.length === 0) return
        review = null
        backend.submitComment(reelId, t)        // ReelGuard checks it first
    }

    Connections {
        target: backend
        function onCommentsLoaded(id, list) {
            if (id !== panel.reelId) return
            panel.loading = false
            panel.error = ""
            cm.clear()
            for (var i = 0; i < list.length; i++)
                cm.append({ author: list[i].author, text: list[i].text, avatar: list[i].avatar })
        }
        function onCommentsFailed(id, msg) {
            if (id !== panel.reelId) return
            panel.loading = false
            panel.error = msg
        }
        function onGuardFlagged(id, text, v) {
            if (id !== panel.reelId) return
            panel.review = v
            panel.reviewText = text
        }
        function onCommentPosted(id) {
            if (id !== panel.reelId) return
            input.clear()
            panel.review = null
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Text { text: "Comments"; color: Theme.text; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true }
            Item {
                width: 32; height: 32
                Icon { anchors.centerIn: parent; size: 20; path: Icons.close }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: panel.close() }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: cl
                anchors.fill: parent
                clip: true
                spacing: 16
                model: cm
                boundsBehavior: Flickable.StopAtBounds
                delegate: Row {
                    id: r
                    required property string author
                    required property string text
                    required property string avatar
                    spacing: 12
                    width: cl.width
                    Avatar { name: r.author; source: r.avatar; size: 34 }
                    Column {
                        width: r.width - 46
                        spacing: 2
                        Text { text: r.author; color: Theme.text; font.bold: true; font.pixelSize: 14 }
                        Text { width: parent.width; text: r.text; color: Theme.text; font.pixelSize: 14; wrapMode: Text.Wrap }
                    }
                }
            }
            Text { anchors.centerIn: parent; visible: panel.loading; text: "Loading comments…"; color: Theme.muted }
            Text {
                anchors.centerIn: parent
                width: parent.width - 32
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                visible: !panel.loading && panel.error !== ""
                text: "Couldn't load comments.\n" + panel.error
                color: Theme.muted
            }
            Text {
                anchors.centerIn: parent
                visible: !panel.loading && panel.error === "" && cm.count === 0
                text: "No comments yet.\nBe the first to comment."
                horizontalAlignment: Text.AlignHCenter
                color: Theme.muted
            }
        }

        // ---- ReelGuard review card ----
        Rectangle {
            id: card
            Layout.fillWidth: true
            visible: panel.review !== null
            implicitHeight: cardCol.implicitHeight + 28
            radius: 12
            color: Theme.card
            border.width: 1
            border.color: panel.review && panel.review.label === "threatening" ? Theme.like : "#f5a524"

            Column {
                id: cardCol
                x: 14; y: 14
                width: parent.width - 28
                spacing: 8
                Row {
                    spacing: 8
                    Icon {
                        size: 20; path: Icons.shield
                        color: card.border.color
                    }
                    Text {
                        text: panel.review ? "ReelGuard flagged this as " + panel.review.label : ""
                        color: Theme.text; font.bold: true; font.pixelSize: 14
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Theme.muted; font.pixelSize: 13
                    text: panel.review ? panel.review.reasons.join("\n") + "\nConfidence: " + Math.round(panel.review.score * 100) + "%" : ""
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Theme.text; font.pixelSize: 13
                    text: panel.review && panel.review.blocked
                          ? "Threats can't be posted. Please edit your comment."
                          : "Please review it. You can edit it, or post it anyway."
                }
                Row {
                    spacing: 8
                    PillButton {
                        text: "Edit comment"
                        fill: Theme.hover; textColor: Theme.text
                        onClicked: { panel.review = null; input.forceActiveFocus() }
                    }
                    PillButton {
                        visible: panel.review !== null && !panel.review.blocked
                        text: "Post anyway"
                        fill: "#f5a524"; textColor: "#1a1a1a"
                        onClicked: { backend.postComment(panel.reelId, panel.reviewText, true); panel.review = null }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            AppTextField {
                id: input
                Layout.fillWidth: true
                placeholderText: "Add a comment…"
                maximumLength: 500
                onAccepted: panel.post()
                onTextChanged: if (panel.review !== null && text.trim() !== panel.reviewText) panel.review = null
            }
            PillButton {
                text: "Post"
                enabled: input.text.trim().length > 0
                onClicked: panel.post()
            }
        }
    }
}