import QtQuick
import QtMultimedia

Item {
    id: item

    // roles injected by the ListView model
    required property int index
    required property int reelId
    required property string author
    required property string caption
    required property string videoUrl
    required property string thumbUrl
    required property int likes
    required property int comments
    required property bool liked
    required property string avatarUrl

    property bool isCurrent: false
    property bool muted: false
    property bool userPaused: false
    property bool started: false

    signal likeRequested()
    signal commentsRequested()
    signal muteRequested()

    function togglePlay() { userPaused = !userPaused }
    function fmt(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1).replace(".0", "") + "M"
        if (n >= 1000) return (n / 1000).toFixed(1).replace(".0", "") + "K"
        return String(n)
    }

    // 9:16 video, as large as the window allows
    readonly property real vh: Math.max(240, Math.min(height - 24, (width - 140) * 16 / 9, 920))
    readonly property real vw: vh * 9 / 16

    readonly property bool hasError: player.error !== MediaPlayer.NoError
    readonly property bool shouldPlay: isCurrent && !userPaused
    readonly property bool playing: shouldPlay && !hasError
    readonly property bool loadingNow: isCurrent && !hasError &&
        (player.mediaStatus === MediaPlayer.LoadingMedia ||
         player.mediaStatus === MediaPlayer.StalledMedia ||
         player.mediaStatus === MediaPlayer.BufferingMedia)

    function applyPlayback() { if (shouldPlay) player.play(); else player.pause() }
    onShouldPlayChanged: applyPlayback()
    onIsCurrentChanged: if (!isCurrent) userPaused = false
    Component.onCompleted: applyPlayback()
    Component.onDestruction: { player.stop(); player.source = "" }   // release decoder

    MediaPlayer {
        id: player
        source: item.videoUrl
        videoOutput: vo
        audioOutput: AudioOutput { muted: item.muted }
        loops: MediaPlayer.Infinite
        onMediaStatusChanged: if (mediaStatus === MediaPlayer.LoadedMedia) item.applyPlayback()
        onPositionChanged: if (!item.started && position > 80) item.started = true
    }

    Row {
        anchors.centerIn: parent
        spacing: 16

        Rectangle {
            id: frame
            width: item.vw; height: item.vh
            radius: 16
            color: "#0a0a0a"
            clip: true
            border.width: 1
            border.color: Theme.border

            // poster shown until the first frame plays
            Image {
                anchors.fill: parent
                source: item.thumbUrl
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                visible: !item.started
            }
            VideoOutput {
                id: vo
                anchors.fill: parent
                fillMode: VideoOutput.PreserveAspectFit
            }

            // tap = play/pause, double tap = like
            Item {
                anchors.fill: parent
                TapHandler {
                    onSingleTapped: item.togglePlay()
                    onDoubleTapped: {
                        if (!item.liked) item.likeRequested()
                        burst.restart()
                    }
                }
            }

            // legibility gradient + author + caption
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 200
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#00000000" }
                    GradientStop { position: 1.0; color: "#CC000000" }
                }
            }
            Column {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom
                          leftMargin: 16; rightMargin: 16; bottomMargin: 18 }
                spacing: 8
                Row {
                    spacing: 10
                    Avatar { name: item.author; source: item.avatarUrl; size: 32 }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: item.author
                        color: "white"; font.pixelSize: 15; font.bold: true
                    }
                }
                Text {
                    visible: item.caption.length > 0
                    width: parent.width
                    text: item.caption
                    color: "white"; font.pixelSize: 14
                    wrapMode: Text.Wrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
            }

            // thin progress bar
            Rectangle {
                anchors { left: parent.left; bottom: parent.bottom }
                height: 3; width: parent.width
                color: "#44ffffff"
                Rectangle {
                    height: parent.height; color: "white"
                    width: player.duration > 0 ? parent.width * player.position / player.duration : 0
                }
            }

            // mute button
            Rectangle {
                anchors { top: parent.top; right: parent.right; margins: 12 }
                width: 36; height: 36; radius: 18
                color: "#66000000"
                Icon {
                    anchors.centerIn: parent
                    size: 20
                    color: "white"
                    path: item.muted ? Icons.volumeOff : Icons.volume
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: item.muteRequested()
                }
            }

            // paused indicator
            Rectangle {
                anchors.centerIn: parent
                width: 76; height: 76; radius: 38
                color: "#80000000"
                opacity: item.userPaused ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: 150 } }
                Icon { anchors.centerIn: parent; size: 34; path: Icons.play; filled: true; color: "white" }
            }

            // double-tap heart
            Icon {
                id: burstIcon
                anchors.centerIn: parent
                size: 110
                path: Icons.heart
                filled: true
                color: Theme.like
                opacity: 0
                scale: 0.5
                SequentialAnimation {
                    id: burst
                    ParallelAnimation {
                        NumberAnimation { target: burstIcon; property: "opacity"; from: 0; to: 1; duration: 120 }
                        NumberAnimation { target: burstIcon; property: "scale"; from: 0.5; to: 1.2; duration: 220; easing.type: Easing.OutBack }
                    }
                    PauseAnimation { duration: 250 }
                    NumberAnimation { target: burstIcon; property: "opacity"; to: 0; duration: 220 }
                }
            }

            // loading spinner
            Icon {
                id: spinner
                anchors.centerIn: parent
                size: 44
                path: Icons.spinner
                color: "white"
                visible: item.loadingNow
                RotationAnimator on rotation {
                    from: 0; to: 360; duration: 900
                    loops: Animation.Infinite
                    running: spinner.visible
                }
            }

            // friendly error state
            Rectangle {
                anchors.fill: parent
                visible: item.hasError
                color: "#F0101010"
                Column {
                    anchors.centerIn: parent
                    width: parent.width - 48
                    spacing: 12
                    Text {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "This reel couldn't be played"
                        color: Theme.text; font.pixelSize: 16; font.bold: true
                        wrapMode: Text.Wrap
                    }
                    Text {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: player.errorString
                        color: Theme.muted; font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 100; height: 38; radius: 10; color: Theme.accent
                        Text { anchors.centerIn: parent; text: "Retry"; color: "white"; font.bold: true }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { player.source = ""; player.source = item.videoUrl; item.applyPlayback() }
                        }
                    }
                }
            }
        }

        // action rail
        Item {
            width: 64; height: item.vh
            Column {
                anchors.bottom: parent.bottom
                spacing: 14
                ActionButton {
                    icon: Icons.heart
                    filled: item.liked
                    iconColor: item.liked ? Theme.like : Theme.text
                    label: item.fmt(item.likes)
                    onClicked: item.likeRequested()
                }
                ActionButton {
                    icon: Icons.comment
                    label: item.fmt(item.comments)
                    onClicked: item.commentsRequested()
                }
            }
        }
    }
}