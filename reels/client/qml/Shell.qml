import QtQuick

Item {
    id: shell
    property string page: "reels"
    readonly property bool wide: width >= 1100

    Sidebar {
        id: side
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        wide: shell.wide
        current: shell.page
        onNavigate: (p) => shell.page = p
    }

    Item {
        anchors { left: side.right; right: parent.right; top: parent.top; bottom: parent.bottom }

        FeedPage    { anchors.fill: parent; visible: shell.page === "reels";  active: shell.page === "reels" }
        SearchPage  { anchors.fill: parent; visible: shell.page === "search" }
        UploadPage  { anchors.fill: parent; visible: shell.page === "upload"; onUploaded: shell.page = "reels" }
        ProfileView { anchors.fill: parent; visible: shell.page === "profile"; who: backend.username }
    }
}