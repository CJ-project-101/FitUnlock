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
            model: [
                { key: "reels",    label: "Reels",         icon: Icons.reels,  ok: true },
                { key: "search",   label: "Search",        icon: Icons.search, ok: true },
                { key: "explore",  label: "Explore",       icon: Icons.explore, ok: true },
                { key: "activity", label: "Notifications", icon: Icons.heart,  ok: false },
                { key: "messages", label: "Messages",      icon: Icons.send,   ok: false },
                { key: "upload",   label: "Create",        icon: Icons.plus,   ok: true },
                { key: "profile",  label: "Profile",       icon: Icons.user,   ok: true }
            ]
            delegate: NavButton {
                required property var modelData
                Layout.fillWidth: true
                label: modelData.label
                icon: modelData.icon
                available: modelData.ok
                showLabel: bar.wide
                selected: bar.current === modelData.key
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