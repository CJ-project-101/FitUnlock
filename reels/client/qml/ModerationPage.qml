import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: mod
    property string filter: ""
    property var sum: ({ classified: { safe: 0, abusive: 0, threatening: 0 }, total: 0, after_review: 0, blocked: 0, flagged: 0 })

    function labelColor(l) { return l === "threatening" ? Theme.like : l === "abusive" ? "#f5a524" : "#2ecc71" }
    function outcomeText(o) {
        if (o === "published") return "Posted"
        if (o === "published_after_review") return "Posted after review"
        if (o === "flagged") return "Flagged: user was asked to review"
        if (o === "blocked") return "Blocked"
        return "Held: no review step"
    }
    function ago(iso) {
        var s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
        if (s < 60) return "now"
        if (s < 3600) return Math.floor(s / 60) + "m ago"
        if (s < 86400) return Math.floor(s / 3600) + "h ago"
        return Math.floor(s / 86400) + "d ago"
    }
    function refresh() { backend.loadModeration(filter) }
    onVisibleChanged: if (visible) refresh()
    onFilterChanged: refresh()

    ListModel { id: lm }
    Connections {
        target: backend
        function onModSummaryLoaded(s) { mod.sum = s }
        function onModLogLoaded(rows) {
            lm.clear()
            for (var i = 0; i < rows.length; i++) lm.append(rows[i])
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Icon { size: 28; path: Icons.shield; color: Theme.accent }
            Text { text: "ReelGuard"; color: Theme.text; font.pixelSize: 26; font.bold: true }
            Text { text: "comment moderation"; color: Theme.muted; font.pixelSize: 14; Layout.alignment: Qt.AlignBottom; Layout.bottomMargin: 4 }
            Text { text: "Engine: " + (mod.sum.engine || "…"); color: Theme.muted; font.pixelSize: 12 }
            Item { Layout.fillWidth: true }
            PillButton { text: "Refresh"; fill: Theme.card; textColor: Theme.text; onClicked: mod.refresh() }
        }

        // summary cards
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: [
                    { label: "Checked",        value: mod.sum.total,                 color: Theme.text },
                    { label: "Safe",           value: mod.sum.classified.safe,       color: "#2ecc71" },
                    { label: "Abusive",        value: mod.sum.classified.abusive,    color: "#f5a524" },
                    { label: "Threatening",    value: mod.sum.classified.threatening, color: Theme.like },
                    { label: "Posted anyway",  value: mod.sum.after_review,          color: Theme.muted },
                    { label: "Blocked",        value: mod.sum.blocked,               color: Theme.like }
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 78
                    radius: 12
                    color: Theme.card
                    border.color: Theme.border
                    Column {
                        anchors.centerIn: parent
                        spacing: 2
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: modelData.color; font.pixelSize: 26; font.bold: true }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: Theme.muted; font.pixelSize: 12 }
                    }
                }
            }
        }

        // share of each class
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 10
            radius: 5
            color: Theme.card
            clip: true
            Row {
                anchors.fill: parent
                Rectangle { height: parent.height; color: "#2ecc71"; width: mod.sum.total > 0 ? parent.width * mod.sum.classified.safe / mod.sum.total : 0 }
                Rectangle { height: parent.height; color: "#f5a524"; width: mod.sum.total > 0 ? parent.width * mod.sum.classified.abusive / mod.sum.total : 0 }
                Rectangle { height: parent.height; color: Theme.like; width: mod.sum.total > 0 ? parent.width * mod.sum.classified.threatening / mod.sum.total : 0 }
            }
        }

        // filters
        Row {
            spacing: 8
            Repeater {
                model: [ { t: "All", v: "" }, { t: "Abusive", v: "abusive" }, { t: "Threatening", v: "threatening" }, { t: "Safe", v: "safe" } ]
                delegate: PillButton {
                    required property var modelData
                    text: modelData.t
                    implicitHeight: 34
                    fill: mod.filter === modelData.v ? Theme.accent : Theme.card
                    textColor: mod.filter === modelData.v ? "white" : Theme.text
                    onClicked: mod.filter = modelData.v
                }
            }
        }

        // classification log
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: lm
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: item
                required property string user
                required property string text
                required property string label
                required property real score
                required property string reasons
                required property string outcome
                required property string time
                required property int comment_id
                required property bool removed
                width: ListView.view.width
                height: col.implicitHeight + 24
                radius: 12
                color: Theme.card
                border.color: Theme.border

                RowLayout {
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                    spacing: 12
                    Column {
                        id: col
                        Layout.fillWidth: true
                        spacing: 6
                        Row {
                            spacing: 8
                            Rectangle {
                                width: tag.implicitWidth + 16; height: 22; radius: 11
                                color: Qt.rgba(0, 0, 0, 0.3); border.color: mod.labelColor(item.label)
                                Text { id: tag; anchors.centerIn: parent; text: item.label; color: mod.labelColor(item.label); font.pixelSize: 12; font.bold: true }
                            }
                            Text { anchors.verticalCenter: parent.verticalCenter; text: Math.round(item.score * 100) + "%"; color: Theme.muted; font.pixelSize: 12 }
                            Text { anchors.verticalCenter: parent.verticalCenter; text: item.user + "  ·  " + mod.outcomeText(item.outcome) + "  ·  " + mod.ago(item.time); color: Theme.muted; font.pixelSize: 12 }
                        }
                        Text { width: parent.width; text: "\u201C" + item.text + "\u201D"; color: Theme.text; font.pixelSize: 14; wrapMode: Text.Wrap }
                        Text { visible: item.reasons !== ""; width: parent.width; text: item.reasons; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.Wrap }
                        Rectangle {
                            width: parent.width; height: 4; radius: 2; color: Theme.hover
                            Rectangle { width: parent.width * item.score; height: parent.height; radius: 2; color: mod.labelColor(item.label) }
                        }
                    }
                    PillButton {
                        visible: item.comment_id > 0 && !item.removed
                        text: "Remove"
                        fill: Theme.like
                        implicitHeight: 34
                        onClicked: backend.removeComment(item.comment_id, mod.filter)
                    }
                    Text { visible: item.removed; text: "Removed"; color: Theme.muted; font.pixelSize: 12 }
                }
            }
        }
        Text {
            visible: lm.count === 0
            Layout.alignment: Qt.AlignHCenter
            text: "No classified comments yet"
            color: Theme.muted
        }
    }
}