import QtQuick

FocusScope {
    id: feed
    property bool active: true
    property bool muted: false
    // CHANGED: the page can show different lists
    property var feedModel: backend.reels
    property string source: "feed"        // "feed" or "viewer": tells the backend which list a like belongs to
    property bool showClose: false
    signal closeRequested()

    // CHANGED: Shell adds up everything that is playing and reports it to the backend
    readonly property bool watching: list.currentItem !== null && list.currentItem.playing

    function step(d) {
        var n = list.currentIndex + d
        if (n >= 0 && n < list.count) list.currentIndex = n
    }
    // CHANGED: jump to a given reel (used when a tile is clicked)
    function jumpTo(i) {
        if (i >= 0 && i < list.count) {
            list.currentIndex = i
            list.positionViewAtIndex(i, ListView.Beginning)
        }
    }

    onActiveChanged: if (active) feed.forceActiveFocus()
    Component.onCompleted: if (active) feed.forceActiveFocus()      // CHANGED: only the active page takes focus

    Keys.onDownPressed: step(1)
    Keys.onUpPressed: step(-1)
    Keys.onEscapePressed: if (feed.showClose) feed.closeRequested()  // CHANGED
    Keys.onSpacePressed: if (list.currentItem) list.currentItem.togglePlay()
    Keys.onPressed: (e) => {
        if (e.key === Qt.Key_L && list.currentItem) { list.currentItem.likeRequested(); e.accepted = true }
        else if (e.key === Qt.Key_M) { feed.muted = !feed.muted; e.accepted = true }
    }

    WheelHandler {
        onWheel: (e) => {
            if (cooldown.running || Math.abs(e.angleDelta.y) < 1) return
            feed.step(e.angleDelta.y > 0 ? -1 : 1)
            cooldown.restart()
        }
    }
    Timer { id: cooldown; interval: 450 }

    Connections {
        target: backend
        function onFeedReloaded() {
            if (feed.source === "feed") { list.currentIndex = 0; list.positionViewAtBeginning() }   // CHANGED
        }
    }

    ListView {
        id: list
        anchors.fill: parent
        model: feed.feedModel                  // CHANGED
        orientation: ListView.Vertical
        interactive: false
        clip: true
        cacheBuffer: 0                         // only the visible reel exists
        boundsBehavior: Flickable.StopAtBounds
        highlightRangeMode: ListView.StrictlyEnforceRange
        preferredHighlightBegin: 0
        preferredHighlightEnd: 0
        highlightMoveDuration: 260
        highlightMoveVelocity: -1

        // CHANGED: only the main feed loads more pages
        onCurrentIndexChanged: if (feed.source === "feed" && count > 0 && currentIndex >= count - 3) backend.loadMore()

        delegate: ReelItem {
            width: list.width
            height: list.height
            isCurrent: ListView.isCurrentItem && feed.active && !backend.locked && !commentsPanel.opened
            muted: feed.muted
            onLikeRequested: backend.toggleLikeIn(feed.source, index)     // CHANGED
            onCommentsRequested: commentsPanel.openFor(reelId)
            onMuteRequested: feed.muted = !feed.muted
        }
    }

    // empty / loading states
    Text {
        anchors.centerIn: parent
        visible: list.count === 0 && !backend.loading
        horizontalAlignment: Text.AlignHCenter
        text: "No reels yet\nTap Create to share the first one"
        color: Theme.muted
        font.pixelSize: 16
    }
    Text {
        anchors.centerIn: parent
        visible: list.count === 0 && backend.loading
        text: "Loading reels…"
        color: Theme.muted
        font.pixelSize: 16
    }

    // end of feed hint
    Rectangle {
        anchors { top: parent.top; horizontalCenter: parent.horizontalCenter; topMargin: 10 }
        visible: feed.source === "feed" && list.count > 0 && list.currentIndex === list.count - 1 && !backend.hasMore && !backend.loading
        width: hint.implicitWidth + 28; height: 32; radius: 16
        color: "#CC171a28"
        Text { id: hint; anchors.centerIn: parent; text: "You're all caught up"; color: Theme.text; font.pixelSize: 13 }
    }

    // minutes left
    Rectangle {
        anchors { top: parent.top; right: parent.right; margins: 14 }
        visible: backend.gateText !== "" && !backend.locked
        width: pillText.implicitWidth + 28; height: 32; radius: 16
        color: "#CC171a28"
        border.color: Theme.border
        Text { id: pillText; anchors.centerIn: parent; text: backend.gateText; color: Theme.text; font.pixelSize: 13 }
    }

    // CHANGED: close button, only shown in the viewer
    Rectangle {
        visible: feed.showClose
        z: 30
        anchors { top: parent.top; left: parent.left; margins: 14 }
        width: 40; height: 40; radius: 20
        color: "#99000000"
        border.color: Theme.border
        Icon { anchors.centerIn: parent; size: 20; path: Icons.close }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: feed.closeRequested()
        }
    }

    CommentsPanel {
        id: commentsPanel
        z: 10
        onClosed: feed.forceActiveFocus()
    }

    // FitPlay gate
    Rectangle {
        anchors.fill: parent
        z: 20
        visible: backend.locked
        color: "#EE06070d"
        Column {
            anchors.centerIn: parent
            width: Math.min(420, feed.width - 48)
            spacing: 14
            Icon { anchors.horizontalCenter: parent.horizontalCenter; size: 56; path: Icons.lock }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Reels are locked"
                color: Theme.text; font.pixelSize: 22; font.bold: true
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: "Earn minutes in FitPlay to keep watching"
                color: Theme.muted; font.pixelSize: 15
            }
            PillButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Open FitPlay"
                onClicked: backend.openFitPlay()
            }
        }
    }
}