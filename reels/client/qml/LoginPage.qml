import QtQuick
import QtQuick.Layouts

Item {
    id: page
    property bool signup: false
    function submit() { backend.authenticate(user.text, pass.text, signup ? "signup" : "login") }

    Backdrop { anchors.fill: parent }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(360, parent.width - 48)
        height: col.implicitHeight + 56
        radius: 16
        color: Theme.panel
        border.color: Theme.border

        ColumnLayout {
            id: col
            anchors.fill: parent
            anchors.margins: 28
            spacing: 12

            Text { text: "Reelz"; color: Theme.text; font.pixelSize: 38; font.bold: true; Layout.alignment: Qt.AlignHCenter }
            Text {
                text: page.signup ? "Create your account" : "Log in to continue"
                color: Theme.muted; Layout.alignment: Qt.AlignHCenter; Layout.bottomMargin: 8
            }
            AppTextField {
                id: user
                Layout.fillWidth: true
                placeholderText: "Username"
                onAccepted: pass.forceActiveFocus()
            }
            AppTextField {
                id: pass
                Layout.fillWidth: true
                placeholderText: "Password"
                echoMode: TextInput.Password
                onAccepted: page.submit()
            }
            Text {
                Layout.fillWidth: true
                visible: backend.authError !== ""
                text: backend.authError
                color: Theme.like
                wrapMode: Text.Wrap
                font.pixelSize: 13
            }
            PillButton {
                Layout.fillWidth: true
                text: backend.busy ? "Please wait…" : (page.signup ? "Sign up" : "Log in")
                enabled: !backend.busy && user.text.length > 0 && pass.text.length > 0
                onClicked: page.submit()
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: page.signup ? "Already have an account? Log in" : "New here? Create an account"
                color: Theme.accent
                font.pixelSize: 13
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.signup = !page.signup }
            }
        }
    }
}