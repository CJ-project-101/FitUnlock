import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia

Item {
    id: page
    property string fileUrl: ""
    property var info: ({})
    property string message: ""
    property bool isError: false
    signal uploaded()

    function choose(url) {
        var i = backend.inspectFile(url)
        if (i.error) {
            fileUrl = ""; info = ({}); message = i.error; isError = true
            return
        }
        info = i; fileUrl = url; message = ""
    }
    function reset() { fileUrl = ""; info = ({}); caption.text = ""; message = "" }

    FileDialog {
        id: dlg
        title: "Choose a video"
        nameFilters: ["Videos (*.mp4 *.mov *.webm *.mkv)"]
        onAccepted: page.choose(selectedFile.toString())
    }

    Connections {
        target: backend
        function onUploadSucceeded() { page.reset(); page.uploaded() }
        function onUploadFailed(msg) { page.message = msg; page.isError = true }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: col.implicitHeight + 48
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: col
            y: 24
            x: (page.width - width) / 2
            width: Math.min(560, page.width - 48)
            spacing: 16

            Text { text: "New reel"; color: Theme.text; font.pixelSize: 26; font.bold: true }

            DropArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 380
                onDropped: (drop) => { if (drop.hasUrls) page.choose(drop.urls[0].toString()) }

                Rectangle {
                    id: zone
                    anchors.fill: parent
                    radius: 16
                    color: Theme.panel
                    border.width: 2
                    border.color: parent.containsDrag ? Theme.accent : Theme.border

                    // empty state
                    Column {
                        anchors.centerIn: parent
                        spacing: 14
                        visible: page.fileUrl === ""
                        Icon { anchors.horizontalCenter: parent.horizontalCenter; size: 56; path: Icons.upload; color: Theme.muted }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Drag a video here"
                            color: Theme.text; font.pixelSize: 18; font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "MP4, MOV, WEBM or MKV, up to 100 MB"
                            color: Theme.muted; font.pixelSize: 13
                        }
                        PillButton {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Select from computer"
                            onClicked: dlg.open()
                        }
                    }

                    // preview state
                    Row {
                        anchors.centerIn: parent
                        spacing: 24
                        visible: page.fileUrl !== ""

                        Rectangle {
                            width: 180; height: 320; radius: 12; color: "black"; clip: true
                            VideoOutput { id: pvo; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
                            MediaPlayer {
                                id: prev
                                source: page.visible ? page.fileUrl : ""
                                videoOutput: pvo
                                audioOutput: AudioOutput { muted: true }
                                loops: MediaPlayer.Infinite
                                onMediaStatusChanged: if (mediaStatus === MediaPlayer.LoadedMedia) play()
                            }
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8
                            width: 220
                            Text { width: parent.width; text: page.info.name || ""; color: Theme.text; font.bold: true; elide: Text.ElideMiddle }
                            Text { text: (page.info.sizeMb || 0) + " MB"; color: Theme.muted }
                            PillButton {
                                text: "Change video"
                                fill: Theme.card
                                textColor: Theme.text
                                onClicked: dlg.open()
                            }
                        }
                    }
                }
            }

            AppTextField {
                id: caption
                Layout.fillWidth: true
                placeholderText: "Write a caption…"
                maximumLength: 300
            }
            Text {
                Layout.alignment: Qt.AlignRight
                text: caption.text.length + " / 300"
                color: Theme.muted; font.pixelSize: 12
            }

            // progress is indeterminate: requests cannot report upload progress
            ProgressBar {
                Layout.fillWidth: true
                visible: backend.uploading
                indeterminate: true
            }

            PillButton {
                Layout.fillWidth: true
                text: backend.uploading ? "Uploading…" : "Share reel"
                enabled: page.fileUrl !== "" && !backend.uploading
                onClicked: backend.uploadReel(page.fileUrl, caption.text)
            }

            Text {
                Layout.fillWidth: true
                visible: page.message !== ""
                text: page.message
                wrapMode: Text.Wrap
                color: page.isError ? Theme.like : "#4cd964"
                font.pixelSize: 14
            }
        }
    }
}