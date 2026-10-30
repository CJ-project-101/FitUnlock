import QtQuick
import QtQuick.Layouts

Rectangle {
    id: bar
    property bool wide: true
    property string current: "reels"
    signal navigate(string page)

    width: wide ? 240 : 76
    color: Theme.bg
    Behavior on width { NumberAnimation { duration: 150 } }

    readonly property var items: {
        var a = [
            { key: "explore",  label: "Explore",       icon: Icons.explore },
            { key: "reels",    label: "Reels",         icon: Icons.reels },
            { key: "search",   label: "Search",        icon: Icons.search },
            { key: "activity", label: "Notifications", icon: Icons.heart },
            { key: "messages", label: "Messages",      icon: Icons.send },
            { key: "upload",   label: "Create",        icon: Icons.plus },
            { key: "profile",  label: "Profile",       icon: Icons.user }
        ]
        if (backend.isAdmin) a.push({ key: "moderation", label: "ReelGuard", icon: Icons.shield })
        return a
    }

    Rectangle { width: 1; height: parent.height; anchors.right: parent.right; color: Theme.border }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        anchors.rightMargin: 13
        spacing: 4

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 76
            Text {
                x: 14
                anchors.verticalCenter: parent.verticalCenter
                text: bar.wide ? "Reelz" : "R"
                color: Theme.text
                font.pixelSize: 28
                font.bold: true
            }
        }

        Repeater {
            model: bar.items
            delegate: NavButton {
                required property var modelData
                Layout.fillWidth: true
                label: modelData.label
                icon: modelData.icon
                showLabel: bar.wide
                selected: bar.current === modelData.key
                badge: modelData.key === "activity" ? backend.unreadNotifications
                     : modelData.key === "messages" ? backend.unreadMessages : 0
                onClicked: bar.navigate(modelData.key)
            }
        }

        Item { Layout.fillHeight: true }

        NavButton {
            Layout.fillWidth: true
            label: "Log out"
            icon: Icons.logout
            showLabel: bar.wide
            onClicked: backend.logout()
        }
    }
}