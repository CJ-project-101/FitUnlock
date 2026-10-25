import QtQuick

FocusScope {
    id: feed
    property bool active: true
    property bool muted: false

    // true only while a reel is really playing: this is what spends minutes
    readonly property bool watching: list.currentItem !== null && list.currentItem.playing
    onWatchingChanged: backend.setWatching(watching)
    Component.onDestruction: backend.setWatching(false)

    function step(d) {
        var n = list.currentIndex + d
        if (n >= 0 && n < list.count) list.currentIndex = n
    }

    onActiveChanged: if (active) feed.forceActiveFocus()
    Component.onCompleted: feed.forceActiveFocus()

    Keys.onDownPressed: step(1)
    Keys.onUpPressed: step(-1)
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
        function onFeedReloaded() { list.currentIndex = 0; list.positionViewAtBeginning() }
    }

    ListView {
        id: list
        anchors.fill: parent
        model: backend.reels
        orientation: ListView.Vertical
        interactive: false
        clip: true
        cacheBuffer: 0                       // only the visible reel exists
        boundsBehavior: Flickable.StopAtBounds
        highlightRangeMode: ListView.StrictlyEnforceRange
        preferredHighlightBegin: 0
        preferredHighlightEnd: 0
        highlightMoveDuration: 260
        highlightMoveVelocity: -1

        onCurrentIndexChanged: if (count > 0 && currentIndex >= count - 3) backend.loadMore()

        delegate: ReelItem {
            width: list.width
            height: list.height
            isCurrent: ListView.isCurrentItem && feed.active && !backend.locked && !commentsPanel.opened
            muted: feed.muted
            onLikeRequested: backend.toggleLike(index)
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
        visible: list.count > 0 && list.currentIndex === list.count - 1 && !backend.hasMore && !backend.loading
        width: hint.implicitWidth + 28; height: 32; radius: 16
        color: "#CC1a1a1a"
        Text { id: hint; anchors.centerIn: parent; text: "You're all caught up"; color: Theme.text; font.pixelSize: 13 }
    }


    Rectangle {
        anchors { top: parent.top; right: parent.right; margins: 14 }
        visible: backend.gateText !== "" && !backend.locked
        width: pillText.implicitWidth + 28; height: 32; radius: 16
        color: "#CC1a1a1a"
        border.color: Theme.border
        Text { id: pillText; anchors.centerIn: parent; text: backend.gateText; color: Theme.text; font.pixelSize: 13 }
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
        color: "#EE000000"
        Column {
            anchors.centerIn: parent
            width: Math.min(420, feed.width - 48)     // CHANGED: gives the text below a width to wrap in
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