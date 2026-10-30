import QtQuick

Item {
    id: shell
    property string page: "reels"
    property bool viewerOpen: false
    property string viewerSource: "viewer"        // "viewer" = a user's reels, "feed" = the Explore list
    readonly property bool wide: width >= 1100

    function openViewer(source, index) {
        viewerSource = source
        viewerOpen = true
        viewer.jumpTo(index)
    }
    function openChat(name) {
        viewerOpen = false
        page = "messages"
        messagesPage.open(name)
    }

    // one place adds up everything that is playing and tells the backend (this is what spends minutes)
    readonly property bool watching: reelsPage.watching || viewer.watching
    onWatchingChanged: backend.setWatching(watching)
    Component.onDestruction: backend.setWatching(false)

    Connections {
        target: backend
        function onViewerReady(index) { shell.openViewer("viewer", index) }
    }

    Sidebar {
        id: side
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        wide: shell.wide
        current: shell.page
        onNavigate: (p) => { shell.viewerOpen = false; shell.page = p }
    }

    Item {
        anchors { left: side.right; right: parent.right; top: parent.top; bottom: parent.bottom }

        Backdrop { anchors.fill: parent }

        ExplorePage       { anchors.fill: parent; visible: shell.page === "explore"
                            onOpenReel: (index) => shell.openViewer("feed", index) }
        FeedPage          { id: reelsPage; anchors.fill: parent; visible: shell.page === "reels"
                            active: shell.page === "reels" && !shell.viewerOpen }
        SearchPage        { anchors.fill: parent; visible: shell.page === "search"
                            onMessageRequested: (name) => shell.openChat(name) }
        NotificationsPage { anchors.fill: parent; visible: shell.page === "activity" }
        MessagesPage      { id: messagesPage; anchors.fill: parent; visible: shell.page === "messages" }
        UploadPage        { anchors.fill: parent; visible: shell.page === "upload"; onUploaded: shell.page = "reels" }
        ProfileView       { anchors.fill: parent; visible: shell.page === "profile"; who: backend.username
                            onMessageRequested: (name) => shell.openChat(name) }
        ModerationPage    { anchors.fill: parent; visible: shell.page === "moderation" }

        // full-screen viewer (opened from a profile or from Explore)
        Backdrop { anchors.fill: parent; z: 49; visible: shell.viewerOpen }
        FeedPage {
            id: viewer
            anchors.fill: parent
            z: 50
            visible: shell.viewerOpen
            active: shell.viewerOpen
            feedModel: shell.viewerSource === "feed" ? backend.reels : backend.viewer
            source: shell.viewerSource
            showClose: true
            onCloseRequested: shell.viewerOpen = false
        }
    }
}